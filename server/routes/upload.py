"""File upload routes."""
import uuid
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from infra.neo4j_client import neo4j_client
from infra.storage import Storage
from services.parser import ParserFactory
from services.extractor import TripletExtractor
from services.linker import EntityLinker
from services.graph_service import GraphService
from services.graphrag_pipeline_service import graphrag_pipeline_service
from models.document import AIExtractionRequest
from infra.queue import get_queue
from infra.config import settings
from config import get_instance, InstanceNames

router = APIRouter(prefix="/uploads", tags=["uploads"])

logger = logging.getLogger("routes.upload")

storage = Storage()
extractor = TripletExtractor()
linker = EntityLinker()
graph_service = GraphService()

# Initialize Redis queue
queue = get_queue()

def get_ai_segmenter():
    """Get AI segmenter instance with lazy initialization."""
    return get_instance(InstanceNames.AI_SEGMENTER)

# Fallback job storage (used when Redis is not available)
processing_jobs = {}

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".md": "md",
    ".markdown": "md",
    ".txt": "txt",
    ".doc": "word",
    ".docx": "word",
    ".json": "json",
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
}

ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf",
    "application/x-pdf",
    # Markdown
    "text/markdown",
    "text/x-markdown",
    "text/x-markdown-markdown",
    # Plain text
    "text/plain",
    "text/plain; charset=utf-8",
    # Word
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # fallback used by some browsers
    # JSON
    "application/json",
    "application/x-json",
    "text/json",
    # CSV
    "text/csv",
    "application/csv",
    "text/plain; charset=utf-8",
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.ms-excel",  # XLS
    "application/x-excel",
    "application/x-msexcel",
}

SUPPORTED_TYPES_LABEL = "PDF, Markdown, TXT, Word (DOC/DOCX), JSON, CSV, Excel (XLS/XLSX)"


def get_document_kind(filename: str) -> str:
    """Determine document kind from filename."""
    if not filename:
        return "unknown"
    ext = Path(filename).suffix.lower()
    return ALLOWED_EXTENSIONS.get(ext, "unknown")


def validate_content_type(content_type: Optional[str]) -> None:
    """Validate uploaded file MIME type."""
    if not content_type:
        return
    # 放宽 MIME 类型验证，只做警告而不阻止上传
    # 因为不同浏览器可能发送不同的 MIME 类型
    if content_type not in ALLOWED_MIME_TYPES:
        print(f"⚠️ [上传] 非标准 MIME 类型: {content_type}，但文件扩展名已验证通过，继续处理")


@router.post("", response_model=dict)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file and create a document record.
    
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "checksum": "...",
            "status": "uploaded"
        }
    """
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Determine document kind
    kind = get_document_kind(file.filename)
    if kind == "unknown":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type: {Path(file.filename).suffix or 'unknown'}. "
                f"Allowed types: {SUPPORTED_TYPES_LABEL}"
            ),
        )

    validate_content_type(file.content_type)
    
    # Save file and get checksum
    file_path, checksum = await storage.save_file(content, file.filename)
    
    # Check if document already exists (by checksum)
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": file.filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "Document already exists"
        }
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=file.filename,
        checksum=checksum,
        kind=kind,
        size=len(content),
        mime=file.content_type,
        meta={"path": file_path}
    )
    
    return {
        "documentId": doc_id,
        "filename": file.filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }

@router.get("")
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",  # "created_at", "filename", or "size"
    status: str = "",  # Filter by processing_status: "completed", "uploaded", "processing", "pending"
    kind: str = "",  # Filter by document kind: "pdf", "md", "txt", etc.
    keyword: str = ""  # Search by filename
):
    """
    获取所有已上传的文档列表
    
    Args:
        skip: 跳过的文档数
        limit: 返回的最大文档数
        sort_by: 排序字段 (created_at, filename, or size)
        status: 筛选处理状态
        kind: 筛选文档类型
        keyword: 搜索关键词（文件名匹配）
    
    Returns:
        {
            "total": 总数,
            "documents": [
                {
                    "id": "...",
                    "filename": "...",
                    "kind": "...",
                    "size": ...,
                    "created_at": "...",
                    "updated_at": "...",
                    "chunk_count": ...,
                    "concept_count": ...,
                    "claim_count": ...,
                    "processing_status": "..."
                }
            ],
            "stats": {
                "total": 总文档数,
                "completed": 已完成数,
                "pending": 待处理数
            }
        }
    """
    # 合法化参数
    skip = max(0, skip)
    limit = min(limit, 100)  # 最多返回 100 条
    
    # 构建基础查询和参数
    match_clause = "MATCH (d:Document)"
    where_conditions = []
    params = {}
    
    # 状态筛选
    if status:
        if status == "pending":
            where_conditions.append("d.processing_status IN ['uploaded', 'pending']")
        else:
            where_conditions.append("d.processing_status = $status")
            params["status"] = status
    
    # 类型筛选
    if kind:
        where_conditions.append("d.kind = $kind")
        params["kind"] = kind
    
    # 关键词搜索
    if keyword:
        where_conditions.append("toLower(d.filename) CONTAINS toLower($keyword)")
        params["keyword"] = keyword
    
    # 构建 WHERE 子句
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # 获取总数
    count_query = f"{match_clause}{where_clause} RETURN count(d) as total"
    total_result = neo4j_client.execute_query(count_query, params)
    total = total_result[0]["total"] if total_result else 0
    
    # 获取统计数据（不应用筛选条件）
    # 使用与文档列表一致的逻辑：如果 processing_status 为空，则根据 chunk_count/claim_count 推断
    # 同时将 processing, failed, cancelled 状态归类到待处理中
    stats_query = """
    MATCH (d:Document)
    RETURN 
        count(d) as total,
        count(CASE 
            WHEN d.processing_status = 'completed' THEN d 
            WHEN d.processing_status IS NULL AND (coalesce(d.chunk_count, 0) > 0 OR coalesce(d.claim_count, 0) > 0) THEN d 
            END) as completed,
        count(CASE 
            WHEN d.processing_status IN ['uploaded', 'pending', 'processing', 'failed', 'cancelled'] THEN d 
            WHEN d.processing_status IS NULL AND coalesce(d.chunk_count, 0) = 0 AND coalesce(d.claim_count, 0) = 0 THEN d 
            END) as pending
    """
    stats_result = neo4j_client.execute_query(stats_query)
    stats = stats_result[0] if stats_result else {"total": 0, "completed": 0, "pending": 0}
    
    # 构建排序子句
    order_clause = "d.created_at DESC"
    if sort_by == "filename":
        order_clause = "d.filename ASC"
    elif sort_by == "size":
        order_clause = "d.size DESC"
    
    # 获取文档列表
    query = f"""
    {match_clause}{where_clause}
    RETURN
        d.id AS id,
        d.filename AS filename,
        d.kind AS kind,
        d.size AS size,
        d.created_at AS created_at,
        d.updated_at AS updated_at,
        d.checksum AS checksum,
        coalesce(d.chunk_count, 0) AS chunk_count,
        coalesce(d.concept_count, 0) AS concept_count,
        coalesce(d.claim_count, 0) AS claim_count,
        coalesce(d.processing_status, "") AS processing_status
    ORDER BY {order_clause}
    SKIP {skip}
    LIMIT {limit}
    """
    
    results = neo4j_client.execute_query(query, params)
    
    documents = []
    for row in results:
        # 检查文档的处理状态（通过是否有统计数据）
        chunk_count = row.get("chunk_count", 0) or 0
        claim_count = row.get("claim_count", 0) or 0
        persisted_status = row.get("processing_status") or ""
        processing_status = persisted_status or ("completed" if chunk_count > 0 or claim_count > 0 else "uploaded")
        
        doc_id = row.get("id")
        # 过滤掉没有ID的无效文档数据
        if not doc_id:
            continue
        
        documents.append({
            "id": doc_id,
            "filename": row.get("filename") or "未命名文档",
            "kind": row.get("kind") or "unknown",
            "size": row.get("size") or 0,
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "checksum": row.get("checksum") or "",
            "chunk_count": chunk_count,
            "concept_count": row.get("concept_count", 0) or 0,
            "claim_count": row.get("claim_count", 0) or 0,
            "processing_status": processing_status
        })
    
    return {
        "total": total,
        "documents": documents,
        "stats": {
            "total": stats["total"],
            "completed": stats["completed"],
            "pending": stats["pending"]
        }
    }


@router.get("/{document_id}")
async def get_document(document_id: str):
    """
    获取文档详细信息
    
    Returns:
        {
            "id": "...",
            "filename": "...",
            "kind": "...",
            "size": ...,
            "created_at": "...",
            "updated_at": "...",
            "checksum": "...",
            "mime": "...",
            "meta": {...},
            "statistics": {
                "chunk_count": ...,
                "concept_count": ...,
                "claim_count": ...,
                "relation_count": ...
            },
            "themes": [
                {
                    "id": "...",
                    "label": "...",
                    "level": ...,
                    "member_count": ...
                }
            ],
            "processing_status": "..."
        }
    """
    # 获取基本文档信息
    doc_result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d",
        {"doc_id": document_id}
    )
    
    if not doc_result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = doc_result[0]["d"]
    
    # 获取统计信息（优先使用文档节点属性，与列表页保持一致）
    statistics = {
        "chunk_count": doc_data.get("chunk_count", 0) or 0,
        "concept_count": doc_data.get("concept_count", 0) or 0,
        "claim_count": doc_data.get("claim_count", 0) or 0,
        "relation_count": doc_data.get("relation_count", 0) or 0
    }
    
    # 获取关联的主题
    themes_query = """
    MATCH (d:Document {id: $doc_id})<-[:BELONGS_TO]-(c:Concept)-[:BELONGS_TO_THEME]->(t:Theme)
    RETURN DISTINCT
        t.id AS id,
        t.label AS label,
        t.level AS level,
        t.member_count AS member_count,
        t.summary AS summary
    LIMIT 20
    """
    
    themes_result = neo4j_client.execute_query(themes_query, {"doc_id": document_id})
    themes = [
        {
            "id": t.get("id"),
            "label": t.get("label"),
            "level": t.get("level"),
            "member_count": t.get("member_count"),
            "summary": t.get("summary")
        }
        for t in themes_result
    ]
    
    # 组合响应
    return {
        "id": doc_data.get("id"),
        "filename": doc_data.get("filename"),
        "kind": doc_data.get("kind"),
        "size": doc_data.get("size"),
        "created_at": doc_data.get("created_at"),
        "updated_at": doc_data.get("updated_at"),
        "checksum": doc_data.get("checksum"),
        "mime": doc_data.get("mime"),
        "meta": doc_data.get("meta", {}),
        "statistics": statistics,
        "themes": themes,
        "processing_status": "completed" if statistics["chunk_count"] > 0 else "uploaded"
    }


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str):
    """
    删除文档及其关联的所有数据。

    Args:
        document_id: 文档ID

    Returns:
        204 No Content
    """
    try:
        # 检查文档是否存在
        doc_result = neo4j_client.execute_query(
            "MATCH (d:Document {id: $doc_id}) RETURN d",
            {"doc_id": document_id}
        )

        if not doc_result:
            raise HTTPException(status_code=404, detail="Document not found")

        # 获取文件路径
        doc_data = doc_result[0]["d"]
        meta = doc_data.get("meta", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {}

        file_path = meta.get("path")

        # 从 Neo4j 删除文档及其所有关联节点
        delete_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[r]-()
        WITH d, r
        DETACH DELETE d
        RETURN count(d) as deleted
        """

        neo4j_client.execute_query(delete_query, {"doc_id": document_id})

        # 删除物理文件
        if file_path and Path(file_path).exists():
            try:
                Path(file_path).unlink()
            except Exception as e:
                print(f"Warning: Failed to delete file {file_path}: {e}")

        # 删除存储中的文件
        checksum = doc_data.get("checksum")
        if checksum:
            storage.delete_file(checksum)

        return None  # 返回 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.get("/{document_id}/file")
async def download_document_file(document_id: str):
    """下载或预览文档原文件，供前端内嵌查看 (PDF/TXT/MD 等)。"""
    result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d",
        {"doc_id": document_id}
    )

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_node = result[0]["d"]

    # 解析 meta，兼容字符串/JSON/字典
    raw_meta = doc_node.get("meta")
    meta = {}
    if isinstance(raw_meta, dict):
        meta = raw_meta
    elif isinstance(raw_meta, str):
        try:
            meta = json.loads(raw_meta)
            if isinstance(meta, str):  # 双重编码的情况
                meta = json.loads(meta)
        except Exception:
            meta = {}

    file_path = meta.get("path") if isinstance(meta, dict) else None

    # 如果 meta 没有路径，尝试根据 checksum 找文件
    if not file_path:
        checksum = doc_node.get("checksum")
        if checksum:
            existing = storage.file_exists(checksum)
            if existing:
                file_path = existing

    # 仍然没有路径则直接报错

    if not file_path:
        raise HTTPException(status_code=404, detail="File path not found")

    abs_path = Path(file_path)
    if not abs_path.is_absolute():
        # 如果是相对路径，优先相对于上传目录，其次当前工作目录
        abs_path = Path(settings.upload_dir) / file_path if not file_path.startswith(str(Path(settings.upload_dir))) else Path(file_path)
        if not abs_path.exists():
            abs_path = Path.cwd() / file_path

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    media_type = doc_node.get("mime") or "application/octet-stream"
    filename = doc_node.get("filename") or abs_path.name
    
    # URL encode the filename to handle non-ASCII characters (Chinese, etc.)
    encoded_filename = quote(filename)

    headers = {"Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}'}

    return FileResponse(
        abs_path,
        media_type=media_type,
        filename=filename,
        headers=headers
    )


def _update_upload_status(job_id: str, status: str, progress: int, message: str, **kwargs):
    """Update job status (supports both Redis and fallback storage)."""
    # Try to update via RQ if we're in a worker context
    if queue.is_connected():
        try:
            from rq import get_current_job
            current_job = get_current_job()
            if current_job:
                # We're in a worker, update current job
                meta = current_job.meta or {}
                meta.update({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    **kwargs
                })
                current_job.meta = meta
                current_job.save()
                return
        except Exception:
            pass
        
        # Not in worker context, try to fetch job by ID
        try:
            job = queue.get_job(job_id)
            if job:
                meta = job.meta or {}
                meta.update({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    **kwargs
                })
                job.meta = meta
                job.save()
                return
        except Exception:
            pass
    
    # Fallback to in-memory storage
    if job_id not in processing_jobs:
        processing_jobs[job_id] = {}
    processing_jobs[job_id].update({
        "status": status,
        "progress": progress,
        "message": message,
        **kwargs
    })


def process_document_background(
    doc_id: str, 
    file_path: str, 
    kind: str, 
    job_id: str, 
    chunk_size: int = 2000,
    enable_ai_segmentation: bool = False,
    user_prompt: Optional[str] = None,
    optimize_prompt: bool = True,
    root_topic: Optional[str] = None
):
    """
    Background task for processing document into knowledge graph.
    
    Args:
        doc_id: Document ID
        file_path: Path to document file
        kind: Document type
        job_id: Job ID for tracking
        chunk_size: Maximum characters per chunk (default: 2000)
        enable_ai_segmentation: Enable AI-powered intelligent segmentation
        user_prompt: User-defined analysis prompt
        optimize_prompt: Whether to optimize user prompt with AI
    """
    _update_upload_status(job_id, "processing", 0, "开始处理文档...", documentId=doc_id)
    
    try:
        print(f"\n{'#'*80}")
        print(f"🚀 [文档处理] 开始处理文档")
        print(f"   - 文档ID: {doc_id}")
        print(f"   - 文件路径: {file_path}")
        print(f"   - 文件类型: {kind}")
        print(f"   - 任务ID: {job_id}")
        print(f"   - AI智能分词: 启用")
        if user_prompt:
            print(f"   - 用户Prompt: {user_prompt[:100]}...")
        print(f"{'#'*80}\n")
        
        if _is_job_cancelled(job_id):
            print(f"❌ [任务取消] 任务已被用户取消")
            _update_upload_status(job_id, "cancelled", 0, "任务已被用户取消", documentId=doc_id)
            return
        
        if graphrag_pipeline_service.is_available():
            print(f"\n🧠 [GraphRAG Pipeline模式] 使用八阶段知识图谱构建流水线")
            
            _update_upload_status(job_id, "processing", 10, "正在解析文档...", documentId=doc_id)
            
            try:
                stats = graphrag_pipeline_service.process_document_sync(
                    file_path=file_path,
                    doc_id=doc_id,
                    root_topic=root_topic,
                    user_prompt=user_prompt,
                    timeout=600
                )
                
                print(f"\n🎉 [GraphRAG Pipeline处理完成]")
                print(f"   - 文本块数: {stats.get('chunks', 0)}")
                print(f"   - 实体数: {stats.get('entities', 0)}")
                print(f"   - 论断数: {stats.get('claims', 0)}")
                print(f"   - 主题数: {stats.get('themes', 0)}")
                print(f"   - 关系数: {stats.get('relationships', 0)}")
                print(f"   - 处理耗时: {stats.get('execution_time', 0):.2f}s")
                
                quality = stats.get('quality_metrics', {})
                if quality:
                    print(f"   - 质量指标:")
                    print(f"     * 孤立节点比例: {quality.get('isolated_node_ratio', 0):.2%}")
                    print(f"     * 平均度数: {quality.get('avg_degree', 0):.2f}")
                
                result_data = {"stats": stats}
                if stats.get('quality_metrics'):
                    result_data["quality_metrics"] = stats['quality_metrics']
                
                _update_upload_status(job_id, "completed", 100, "GraphRAG Pipeline处理完成！", documentId=doc_id, **result_data)
                logger.info(f"GraphRAG Pipeline completed successfully for doc_id: {doc_id}")
                return
            
            except Exception as e:
                error_msg = f"GraphRAG Pipeline执行失败，回退到传统模式: {str(e)}"
                print(f"⚠️  {error_msg}")
                logger.warning(error_msg)
        
        print(f"\n🤖 [传统模式] 使用传统处理流程")
        
        _update_upload_status(job_id, "processing", 10, "正在解析文档...", documentId=doc_id)
        
        print(f"📖 [步骤1] 解析文档 (chunk_size={chunk_size})...")
        parser = ParserFactory.create_parser(kind, chunk_size=chunk_size)
        full_text, chunks = parser.parse(file_path)
        print(f"✅ [步骤1] 解析完成: {len(chunks)} 个文本块，总长度 {len(full_text)} 字符")
        if chunks:
            avg_chunk_size = sum(len(c.text) for c in chunks) / len(chunks)
            print(f"   - 平均每个文本块: {avg_chunk_size:.0f} 字符")
        
        ai_segmenter = get_ai_segmenter()
        enable_ai_segmentation = True
        
        if ai_segmenter:
            print(f"\n🧠 [AI模式] 启用智能知识抽取")
            
            final_prompt = None
            if user_prompt:
                _update_upload_status(job_id, "processing", 15, "正在优化分析提示词...", documentId=doc_id)
                
                if optimize_prompt:
                    print(f"🔧 [Prompt优化] 优化用户提示词...")
                    final_prompt = ai_segmenter.optimize_user_prompt(user_prompt)
                else:
                    final_prompt = user_prompt
                    print(f"📝 [Prompt] 使用原始用户提示词")
            
            _update_upload_status(job_id, "processing", 20, "正在分析文档结构...", documentId=doc_id)
            
            print(f"\n🔍 [文档分析] 分析文档整体结构...")
            doc_context = ai_segmenter.analyze_document_structure(chunks, final_prompt)
            print(f"✅ [文档分析] 完成:")
            print(f"   - 主题: {', '.join(doc_context.get('themes', []))}")
            print(f"   - 领域: {', '.join(doc_context.get('domains', []))}")
            print(f"   - 关键概念: {', '.join(doc_context.get('key_concepts', [])[:5])}...")
            
            _update_upload_status(job_id, "processing", 30, "正在进行深度知识抽取...", documentId=doc_id)
            
            print(f"\n💎 [深度抽取] 开始智能知识抽取 (共 {len(chunks)} 个文本块)...")
            all_triplets = []
            all_concepts = []
            all_insights = []
            
            for i, chunk in enumerate(chunks, 1):
                if _is_job_cancelled(job_id):
                    print(f"❌ [任务取消] 任务已被用户取消")
                    _update_upload_status(job_id, "cancelled", progress, "任务已被用户取消", documentId=doc_id)
                    return
                
                print(f"\n📦 [文本块 {i}/{len(chunks)}] AI深度分析中...")
                knowledge = ai_segmenter.extract_rich_knowledge(chunk, doc_context, final_prompt)
                
                triplets = knowledge.get("triplets", [])
                all_triplets.extend(triplets)
                
                concepts = knowledge.get("concepts", [])
                all_concepts.extend(concepts)
                
                insights = knowledge.get("insights", [])
                all_insights.extend(insights)
                
                print(f"   ✓ 提取: {len(triplets)} 个关系, {len(concepts)} 个概念, {len(insights)} 个洞察")
                
                progress = 30 + int((i / len(chunks)) * 40)
                _update_upload_status(job_id, "processing", progress, f"AI深度分析中... ({i}/{len(chunks)})", documentId=doc_id)
            
            print(f"\n📊 [深度抽取] 完成:")
            print(f"   - 总关系数: {len(all_triplets)}")
            print(f"   - 总概念数: {len(all_concepts)}")
            print(f"   - 总洞察数: {len(all_insights)}")
            
            _update_upload_status(job_id, "processing", 75, "正在构建丰富概念...", documentId=doc_id)
            
            print(f"\n💎 [概念构建] 写入丰富概念信息...")
            graph_service.ingest_rich_concepts(doc_id, all_concepts, root_topic=root_topic)
            
            _update_upload_status(job_id, "processing", 80, "正在链接实体...", documentId=doc_id)
            
            print(f"\n🔗 [实体链接] 开始实体链接和合并...")
            linked_triplets = linker.link_and_merge(all_triplets)
            print(f"✅ [实体链接] 完成: {len(linked_triplets)} 个三元组")
            
            _update_upload_status(job_id, "processing", 90, "正在构建知识图谱...", documentId=doc_id)
            
            print(f"\n💾 [图谱构建] 开始构建知识图谱...")
            graph_service.ingest_triplets(doc_id, linked_triplets, root_topic=root_topic)
            print(f"✅ [图谱构建] 完成")
            
            concept_names = set(c["name"] for c in all_concepts)
            
            print(f"\n{'#'*80}")
            print(f"🎉 [AI智能处理] 处理完成!")
            print(f"   - 文本块数: {len(chunks)}")
            print(f"   - 丰富概念数: {len(all_concepts)}")
            print(f"   - 知识关系数: {len(linked_triplets)}")
            print(f"   - 深度洞察数: {len(all_insights)}")
            print(f"   - 文本总长度: {len(full_text)} 字符")
            if all_insights:
                print(f"\n💡 [关键洞察]:")
                for insight in all_insights[:3]:
                    print(f"   • {insight}")
            print(f"{'#'*80}\n")
            
            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "insights": len(all_insights),
                "textLength": len(full_text),
                "mode": "ai_segmentation"
            }
            result_data = {"stats": stats}
            if all_insights:
                result_data["insights"] = all_insights[:10]
            
            try:
                neo4j_client.execute_query("""
                    MATCH (d:Document {id: $doc_id})
                    SET d.stats = $stats,
                        d.chunk_count = $chunk_count,
                        d.claim_count = $claim_count,
                        d.concept_count = $concept_count,
                        d.relation_count = $relation_count,
                        d.text_length = $text_length,
                        d.processing_status = "completed",
                        d.processed_at = datetime(),
                        d.updated_at = datetime()
                    RETURN d
                """, {
                    "doc_id": doc_id,
                    "stats": json.dumps(stats),
                    "chunk_count": len(chunks),
                    "claim_count": len(linked_triplets),
                    "concept_count": len(concept_names),
                    "relation_count": len(linked_triplets),
                    "text_length": len(full_text)
                })
                print(f"✅ [Neo4j统计更新] 文档统计信息已保存到数据库")
            except Exception as e:
                print(f"⚠️  Neo4j统计更新失败: {e}")
            
            _update_upload_status(job_id, "completed", 100, "AI智能分析完成！", documentId=doc_id, **result_data)
        
        else:
            _update_upload_status(job_id, "processing", 30, f"已提取 {len(chunks)} 个文本块，正在进行知识抽取...", documentId=doc_id)
            
            print(f"\n🤖 [步骤2] 开始知识抽取 (共 {len(chunks)} 个文本块)...")
            all_triplets = []
            chunk_triplet_counts = []
            
            for i, chunk in enumerate(chunks, 1):
                if _is_job_cancelled(job_id):
                    print(f"❌ [任务取消] 任务已被用户取消")
                    _update_upload_status(job_id, "cancelled", progress, "任务已被用户取消", documentId=doc_id)
                    return
                
                print(f"\n📦 [文本块 {i}/{len(chunks)}] 处理中...")
                triplets = extractor.extract(chunk)
                all_triplets.extend(triplets)
                chunk_triplet_counts.append(len(triplets))
                progress = 30 + int((i / len(chunks)) * 40)
                _update_upload_status(job_id, "processing", progress, f"正在抽取知识... ({i}/{len(chunks)})", documentId=doc_id)
            
            print(f"\n📊 [步骤2] 知识抽取完成:")
            print(f"   - 总三元组数: {len(all_triplets)}")
            print(f"   - 各文本块三元组数: {chunk_triplet_counts}")
            print(f"   - 平均每个文本块: {len(all_triplets) / len(chunks) if chunks else 0:.2f} 个三元组")
            
            _update_upload_status(job_id, "processing", 70, f"已抽取 {len(all_triplets)} 个知识三元组，正在链接实体...", documentId=doc_id)
            
            print(f"\n🔗 [步骤3] 开始实体链接和合并...")
            linked_triplets = linker.link_and_merge(all_triplets)
            print(f"✅ [步骤3] 实体链接完成: {len(linked_triplets)} 个三元组")
            
            _update_upload_status(job_id, "processing", 85, "正在构建知识图谱...", documentId=doc_id)
            
            print(f"\n💾 [步骤4] 开始构建知识图谱...")
            graph_service.ingest_triplets(doc_id, linked_triplets, root_topic=root_topic)
            print(f"✅ [步骤4] 知识图谱构建完成")
            
            concept_names = set(t.subject for t in linked_triplets) | set(t.object for t in linked_triplets)
            
            print(f"\n{'#'*80}")
            print(f"🎉 [文档处理] 处理完成!")
            print(f"   - 文本块数: {len(chunks)}")
            print(f"   - 知识三元组数: {len(linked_triplets)}")
            print(f"   - 概念数量: {len(concept_names)}")
            print(f"   - 文本总长度: {len(full_text)} 字符")
            print(f"{'#'*80}\n")

            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "textLength": len(full_text),
                "mode": "traditional"
            }

            try:
                neo4j_client.execute_query("""
                    MATCH (d:Document {id: $doc_id})
                    SET d.stats = $stats,
                        d.chunk_count = $chunk_count,
                        d.claim_count = $claim_count,
                        d.concept_count = $concept_count,
                        d.relation_count = $relation_count,
                        d.text_length = $text_length,
                        d.processing_status = "completed",
                        d.processed_at = datetime(),
                        d.updated_at = datetime()
                    RETURN d
                """, {
                    "doc_id": doc_id,
                    "stats": json.dumps(stats),
                    "chunk_count": len(chunks),
                    "claim_count": len(linked_triplets),
                    "concept_count": len(concept_names),
                    "relation_count": len(linked_triplets),
                    "text_length": len(full_text)
                })
                print(f"✅ [Neo4j统计更新] 文档统计信息已保存到数据库")
            except Exception as e:
                print(f"⚠️  Neo4j统计更新失败: {e}")

            _update_upload_status(job_id, "completed", 100, "知识图谱构建完成！", documentId=doc_id, stats=stats)
        
    except Exception as e:
        print(f"\n{'#'*80}")
        print(f"❌ [文档处理] 处理失败!")
        print(f"   - 错误信息: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(f"   - 错误详情:\n{error_trace}")
        print(f"{'#'*80}\n")
        
        _update_upload_status(job_id, "failed", 0, f"处理失败: {str(e)}", documentId=doc_id, error=error_trace)


@router.post("/process", response_model=dict)
async def upload_and_process(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    chunk_size: int = 2000,
    enable_ai_segmentation: str = "false",
    user_prompt: Optional[str] = None,
    optimize_prompt: str = "true",
    root_topic: Optional[str] = None
):
    """
    一体化接口：上传文件并自动进行知识抽取和图谱构建。
    
    Args:
        file: 上传的文件
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000，建议范围：1000-8000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        root_topic: 主题根节点名称（可选），如果提供，文件内容将链接到此主题而不是文档
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
    # 直接从请求体获取原始表单数据（绕过 FastAPI 的自动类型转换）
    form_data = await request.form()
    enable_ai_segmentation_raw = form_data.get("enable_ai_segmentation", "false")
    optimize_prompt_raw = form_data.get("optimize_prompt", "true")
    
    # Debug: Print raw values before conversion
    print(f"\n[DEBUG upload_and_process] 原始表单值:")
    print(f"  - enable_ai_segmentation_raw: '{enable_ai_segmentation_raw}' (类型: {type(enable_ai_segmentation_raw)})")
    print(f"  - optimize_prompt_raw: '{optimize_prompt_raw}' (类型: {type(optimize_prompt_raw)})")
    
    # 转换为布尔值
    enable_ai_segmentation = enable_ai_segmentation_raw.lower() == "true"
    optimize_prompt = optimize_prompt_raw.lower() == "true"
    
    # Debug: Print received parameters (after conversion)
    print(f"\n[DEBUG upload_and_process] 接收到参数:")
    print(f"  - auto_process: {auto_process} (类型: {type(auto_process)})")
    print(f"  - chunk_size: {chunk_size} (类型: {type(chunk_size)})")
    print(f"  - enable_ai_segmentation: {enable_ai_segmentation} (类型: {type(enable_ai_segmentation)})")
    print(f"  - user_prompt: {user_prompt}")
    print(f"  - optimize_prompt: {optimize_prompt}")
    print(f"  - root_topic: {root_topic}")
    print(f"  - 文件名: {file.filename}")
    
    # Validate chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if enable_ai_segmentation and not get_ai_segmenter():
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Determine document kind
    kind = get_document_kind(file.filename)
    if kind == "unknown":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type: {Path(file.filename).suffix or 'unknown'}. "
                f"Allowed types: {SUPPORTED_TYPES_LABEL}"
            ),
        )

    validate_content_type(file.content_type)
    
    # Save file and get checksum
    file_path, checksum = await storage.save_file(content, file.filename)
    
    # Check if document already exists (by checksum)
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": file.filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "文档已存在"
        }
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=file.filename,
        checksum=checksum,
        kind=kind,
        size=len(content),
        mime=file.content_type,
        meta={"path": file_path}
    )
    
    response = {
        "documentId": doc_id,
        "filename": file.filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }
    
    # If auto_process is enabled, start background processing
    if auto_process and background_tasks:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Try to use RQ queue if available
        import os
        # Windows 系统不支持 os.fork()，RQ Worker 无法工作，直接使用 BackgroundTasks
        if queue.is_connected() and os.name != 'nt':
            try:
                job = queue.enqueue(
                    process_document_background,
                    doc_id,
                    file_path,
                    kind,
                    job_id,
                    chunk_size,
                    enable_ai_segmentation,
                    user_prompt,
                    optimize_prompt,
                    root_topic,
                    timeout='1h'
                )
                
                if job:
                    job.meta = {
                        "status": "queued",
                        "documentId": doc_id,
                        "progress": 0,
                        "message": "等待处理..."
                    }
                    job.save()
                    response["status"] = "processing"
                    response["jobId"] = job.id
                    response["message"] = "文档已上传，正在后台处理..."
                    return response
            except Exception as e:
                print(f"⚠️  RQ 队列失败，回退到 BackgroundTasks: {e}")
        
        # Fallback to BackgroundTasks (Windows 系统或 Redis 不可用)
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            kind,
            job_id,
            chunk_size,
            enable_ai_segmentation,
            user_prompt,
            optimize_prompt,
            root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "文档已上传，正在后台处理..."
    
    return response


@router.get("/status/{job_id}")
async def get_processing_status(job_id: str):
    """
    获取文档处理状态。
    
    Returns:
        {
            "status": "queued" | "processing" | "completed" | "failed",
            "documentId": "...",
            "progress": 0-100,
            "message": "...",
            "stats": {...} (if completed)
        }
    """
    # Try to get status from Redis first
    if queue.is_connected():
        status = queue.get_job_status(job_id)
        if status.get("status") != "not_found":
            return status
    
    # Fallback to in-memory storage
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]


# Pydantic models for text and URL uploads
class TextUploadRequest(BaseModel):
    """Request model for text content upload."""
    content: str
    title: Optional[str] = None
    auto_process: bool = True
    chunk_size: int = 2000
    enable_ai_segmentation: bool = False
    user_prompt: Optional[str] = None
    optimize_prompt: bool = True
    root_topic: Optional[str] = None


class URLUploadRequest(BaseModel):
    """Request model for URL content upload."""
    url: str
    title: Optional[str] = None
    auto_process: bool = True
    chunk_size: int = 2000
    enable_ai_segmentation: bool = False
    user_prompt: Optional[str] = None
    optimize_prompt: bool = True
    root_topic: Optional[str] = None


@router.post("/text", response_model=dict)
async def upload_text(
    request: TextUploadRequest,
    background_tasks: BackgroundTasks
):
    """
    从文本内容创建文档并可选地自动处理。
    
    Args:
        content: 文本内容
        title: 文档标题（可选，默认使用前30个字符）
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
    print(f"\n[DEBUG upload_text] 接收到参数:")
    print(f"   - enable_ai_segmentation: {request.enable_ai_segmentation} (类型: {type(request.enable_ai_segmentation)})")
    print(f"   - user_prompt: {request.user_prompt}")
    print(f"   - optimize_prompt: {request.optimize_prompt}")
    print(f"   - root_topic: {request.root_topic}")
    # Validate chunk_size
    chunk_size = request.chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if request.enable_ai_segmentation and not get_ai_segmenter():
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
    
    content = request.content.strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    
    # Generate title from content if not provided
    title = request.title or content[:30].replace('\n', ' ') + "..."
    filename = f"{title}.txt"
    
    # Calculate checksum
    content_bytes = content.encode('utf-8')
    checksum = hashlib.sha256(content_bytes).hexdigest()
    
    # Check if document already exists
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "相同内容的文档已存在"
        }
    
    # Save text as file
    file_path, _ = await storage.save_file(content_bytes, filename)
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=filename,
        checksum=checksum,
        kind="txt",
        size=len(content_bytes),
        mime="text/plain",
        meta={"path": file_path, "source": "text_input"}
    )
    
    response = {
        "documentId": doc_id,
        "filename": filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }
    
    # Auto-process if enabled
    if request.auto_process:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Try to use RQ queue if available
        import os
        if queue.is_connected() and os.name != 'nt':
            try:
                job = queue.enqueue(
                    process_document_background,
                    doc_id,
                    file_path,
                    "txt",
                    job_id,
                    chunk_size,
                    request.enable_ai_segmentation,
                    request.user_prompt,
                    request.optimize_prompt,
                    request.root_topic,
                    timeout='1h'
                )
                
                if job:
                    job.meta = {
                        "status": "queued",
                        "documentId": doc_id,
                        "progress": 0,
                        "message": "等待处理..."
                    }
                    job.save()
                    response["status"] = "processing"
                    response["jobId"] = job.id
                    response["message"] = "文本已保存，正在后台处理..."
                    return response
            except Exception as e:
                print(f"⚠️  RQ 队列失败，回退到 BackgroundTasks: {e}")
        
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id,
            chunk_size,
            request.enable_ai_segmentation,
            request.user_prompt,
            request.optimize_prompt,
            request.root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "文本已保存，正在后台处理..."
    
    return response


@router.post("/url", response_model=dict)
async def upload_url(
    request: URLUploadRequest,
    background_tasks: BackgroundTasks
):
    """
    从网页URL抓取内容并创建文档。
    
    Args:
        url: 网页链接
        title: 文档标题（可选，默认使用URL）
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
    # Validate chunk_size
    chunk_size = request.chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if request.enable_ai_segmentation and not get_ai_segmenter():
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
    import httpx
    from bs4 import BeautifulSoup
    
    url = request.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL 不能为空")
    
    # Fetch webpage content
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html_content = response.text
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法访问该网页: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"抓取网页时出错: {str(e)}"
        )
    
    # Parse HTML and extract text
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get page title
        page_title = soup.title.string if soup.title else None
        title = request.title or page_title or url
        
        # Extract text
        text_content = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"解析网页内容时出错: {str(e)}"
        )
    
    if not content or len(content) < 50:
        raise HTTPException(
            status_code=400,
            detail="网页内容过少或无法提取有效文本"
        )
    
    # Generate filename
    filename = f"{title[:50]}.txt"
    
    # Calculate checksum
    content_bytes = content.encode('utf-8')
    checksum = hashlib.sha256(content_bytes).hexdigest()
    
    # Check if document already exists
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "相同内容的文档已存在"
        }
    
    # Save content as file
    file_path, _ = await storage.save_file(content_bytes, filename)
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=filename,
        checksum=checksum,
        kind="txt",
        size=len(content_bytes),
        mime="text/plain",
        meta={"path": file_path, "source": "url", "original_url": url}
    )
    
    response = {
        "documentId": doc_id,
        "filename": filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path,
        "sourceUrl": url
    }
    
    # Auto-process if enabled
    if request.auto_process:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        import os
        if queue.is_connected() and os.name != 'nt':
            try:
                job = queue.enqueue(
                    process_document_background,
                    doc_id,
                    file_path,
                    "txt",
                    job_id,
                    chunk_size,
                    request.enable_ai_segmentation,
                    request.user_prompt,
                    request.optimize_prompt,
                    request.root_topic,
                    timeout='1h'
                )
                
                if job:
                    job.meta = {
                        "status": "queued",
                        "documentId": doc_id,
                        "progress": 0,
                        "message": "等待处理..."
                    }
                    job.save()
                    response["status"] = "processing"
                    response["jobId"] = job.id
                    response["message"] = "网页内容已抓取，正在后台处理..."
                    return response
            except Exception as e:
                print(f"⚠️  RQ 队列失败，回退到 BackgroundTasks: {e}")
        
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id,
            chunk_size,
            request.enable_ai_segmentation,
            request.user_prompt,
            request.optimize_prompt,
            request.root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "网页内容已抓取，正在后台处理..."
    
    return response


@router.delete("/cancel/{job_id}")
async def cancel_upload_job(job_id: str):
    """
    Cancel a running upload processing job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        Success message or error
    """
    # Try to cancel via RQ if available
    if queue.is_connected():
        success = queue.cancel_job(job_id)
        if success:
            # Update in-memory status if exists
            if job_id in processing_jobs:
                processing_jobs[job_id].update({
                    "status": "cancelled",
                    "message": "任务已被用户取消"
                })
            return {"message": "Job cancelled successfully", "jobId": job_id}
    
    # Fallback: mark job as cancelled in in-memory storage
    processing_jobs[job_id] = {
        "status": "cancelled",
        "message": "任务已被用户取消",
        "progress": 0
    }
    
    return {"message": "Job cancelled successfully", "jobId": job_id}


def _is_job_cancelled(job_id: str) -> bool:
    """Check if job has been cancelled."""
    # Check in-memory storage
    if job_id in processing_jobs:
        return processing_jobs[job_id].get("status") == "cancelled"
    
    # Check Redis queue metadata
    if queue.is_connected():
        status = queue.get_job_status(job_id)
        if status.get("status") == "cancelled":
            return True
    
    return False

