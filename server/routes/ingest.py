"""Document ingestion routes."""
import json
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Optional
from pathlib import Path
from infra.neo4j_client import neo4j_client
from infra.queue import get_queue, update_job_progress
from services.graphrag_pipeline_service import graphrag_pipeline_service
from config import get_instance, InstanceNames

router = APIRouter(prefix="/ingest", tags=["ingest"])

storage = get_instance(InstanceNames.STORAGE)

queue = get_queue()

jobs: Dict[str, Dict] = {}


def _is_job_cancelled(job_id: str) -> bool:
    """Check if job has been cancelled."""
    if queue.is_connected():
        try:
            from rq import get_current_job
            current_job = get_current_job()
            if current_job:
                meta = current_job.meta or {}
                return meta.get('_cancelled', False)
        except Exception:
            pass
        
        try:
            job = queue.get_job(job_id)
            if job:
                meta = job.meta or {}
                return meta.get('_cancelled', False)
        except Exception:
            pass
    
    if job_id in jobs:
        return jobs[job_id].get("status") == "cancelled"
    
    return False


def _update_status(job_id: str, status: str, progress: int, message: str, **kwargs):
    """Update job status (supports both Redis and fallback storage)."""
    if queue.is_connected():
        try:
            from rq import get_current_job
            current_job = get_current_job()
            if current_job:
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
    
    if job_id not in jobs:
        jobs[job_id] = {}
    jobs[job_id].update({
        "status": status,
        "progress": progress,
        "message": message,
        **kwargs
    })


def process_document(
    doc_id: str, 
    file_path: str, 
    kind: str, 
    job_id: str, 
    chunk_size: int = 2000,
    user_prompt: Optional[str] = None,
    root_topic: Optional[str] = None
):
    """
    Process document using GraphRAG Pipeline.
    
    Args:
        doc_id: Document ID
        file_path: Path to document file
        kind: Document type
        job_id: Job ID for tracking
        chunk_size: Maximum characters per chunk (default: 2000)
        user_prompt: User-defined analysis prompt
        root_topic: Root topic name
    """
    _update_status(job_id, "processing", 0, "开始处理文档...", documentId=doc_id)
    
    try:
        if _is_job_cancelled(job_id):
            return
        
        if not graphrag_pipeline_service.is_available():
            raise RuntimeError("GraphRAG Pipeline 服务不可用，请检查配置")
        
        _update_status(job_id, "processing", 10, "正在解析文档...", documentId=doc_id)
        
        stats = graphrag_pipeline_service.process_document_sync(
            file_path=file_path,
            doc_id=doc_id,
            root_topic=root_topic,
            user_prompt=user_prompt,
            timeout=600
        )
        
        result_data = {"stats": stats}
        if stats.get('quality_metrics'):
            result_data["quality_metrics"] = stats['quality_metrics']
        
        _update_status(job_id, "completed", 100, "GraphRAG Pipeline处理完成！", documentId=doc_id, **result_data)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        _update_status(job_id, "failed", 0, f"Error: {str(e)}", documentId=doc_id, error=error_trace)


@router.post("/{document_id}")
async def ingest_document(
    document_id: str, 
    background_tasks: BackgroundTasks,
    chunk_size: int = 2000,
    user_prompt: Optional[str] = None,
    root_topic: Optional[str] = None
):
    """
    Trigger ingestion for a document using GraphRAG Pipeline.
    
    Args:
        document_id: Document ID to ingest
        chunk_size: Maximum characters per chunk (default: 2000)
        user_prompt: User-defined analysis prompt
        root_topic: Root topic name
    
    Returns:
        {
            "jobId": "...",
            "documentId": "...",
            "status": "queued"
        }
    """
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d.filename as filename, d.kind as kind, d.meta as meta",
        {"doc_id": document_id}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = result[0]
    filename = doc_data["filename"]
    kind = doc_data["kind"]
    
    meta = {}
    if doc_data.get("meta"):
        try:
            meta = json.loads(doc_data["meta"]) if isinstance(doc_data["meta"], str) else doc_data["meta"]
        except (json.JSONDecodeError, TypeError):
            meta = {}
    
    file_path = meta.get("path") or storage.get_file_path(filename)
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    if queue.is_connected():
        job = queue.enqueue(
            process_document,
            document_id,
            str(file_path),
            kind,
            job_id,
            chunk_size,
            user_prompt,
            root_topic,
            timeout='1h'
        )
        
        if job:
            job.meta = {
                "status": "queued",
                "documentId": document_id,
                "progress": 0,
                "message": "Queued for processing"
            }
            job.save()
            return {
                "jobId": job.id,
                "documentId": document_id,
                "status": "queued"
            }
    
    _update_status(job_id, "queued", 0, "Queued for processing", documentId=document_id)
    
    background_tasks.add_task(
        process_document, 
        document_id, 
        str(file_path), 
        kind, 
        job_id, 
        chunk_size,
        user_prompt,
        root_topic
    )
    
    return {
        "jobId": job_id,
        "documentId": document_id,
        "status": "queued"
    }


@router.get("/status/{job_id}")
async def get_ingest_status(job_id: str):
    """Get ingestion job status."""
    if queue.is_connected():
        status = queue.get_job_status(job_id)
        if status.get("status") != "not_found":
            return status
    
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@router.delete("/cancel/{job_id}")
async def cancel_ingest_job(job_id: str):
    """
    Cancel a running ingestion job.
    """
    if queue.is_connected():
        success = queue.cancel_job(job_id)
        if success:
            if job_id in jobs:
                jobs[job_id].update({
                    "status": "cancelled",
                    "message": "任务已被用户取消"
                })
            return {"message": "Job cancelled successfully", "jobId": job_id}
        else:
            status = queue.get_job_status(job_id)
            if status.get("status") == "not_found":
                jobs[job_id] = {
                    "status": "cancelled",
                    "message": "任务已被用户取消",
                    "progress": 0
                }
                return {"message": "Job cancelled successfully", "jobId": job_id}
            else:
                raise HTTPException(status_code=400, detail="Job cannot be cancelled (already completed or failed)")
    
    if job_id not in jobs:
        jobs[job_id] = {
            "status": "cancelled",
            "message": "任务已被用户取消",
            "progress": 0
        }
        return {"message": "Job cancelled successfully", "jobId": job_id}
    
    current_status = jobs[job_id].get("status")
    if current_status in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled (status: {current_status})")
    
    jobs[job_id].update({
        "status": "cancelled",
        "message": "任务已被用户取消"
    })
    
    return {"message": "Job cancelled successfully", "jobId": job_id}


@router.get("/status")
async def get_all_jobs_status():
    """获取所有任务状态。"""
    try:
        all_tasks = []

        if queue.is_connected():
            rq_jobs = queue.get_all_jobs()
            for job in rq_jobs:
                meta = job.meta or {}
                all_tasks.append({
                    "task_id": job.id,
                    "document_id": meta.get("documentId"),
                    "status": meta.get("status", "unknown"),
                    "progress": meta.get("progress", 0),
                    "created_at": meta.get("created_at"),
                    "message": meta.get("message", "")
                })

        for job_id, job_data in jobs.items():
            all_tasks.append({
                "task_id": job_id,
                "document_id": job_data.get("documentId"),
                "status": job_data.get("status", "unknown"),
                "progress": job_data.get("progress", 0),
                "message": job_data.get("message", "")
            })

        summary = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }

        for task in all_tasks:
            status = task.get("status", "unknown")
            if status in summary:
                summary[status] += 1
            elif status == "queued":
                summary["queued"] += 1

        return {
            "tasks": all_tasks[:100],
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消正在进行的任务。"""
    try:
        return await cancel_ingest_job(task_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")
