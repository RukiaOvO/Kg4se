"""
反馈 API

处理人工反馈与修正请求
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import uuid

from graphrag.models.feedback import (
    MergeRequest,
    CorrectionRequest,
    UnlinkRequest
)
from infra.neo4j_client import neo4j_client

logger = logging.getLogger("graphrag.api.feedback")

router = APIRouter(prefix="/graphrag/feedback", tags=["Feedback"])


def _generate_request_id(prefix: str) -> str:
    """Generate unique request ID"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _concept_exists(concept_id: str) -> bool:
    """Check if concept exists"""
    result = neo4j_client.execute_query(
        "MATCH (c:Concept {name: $id}) RETURN c LIMIT 1",
        {"id": concept_id}
    )
    return len(result) > 0


# 端点
@router.post("/merge", response_model=MergeRequest)
async def submit_merge_request(request: MergeRequest):
    """
    提交实体合并请求
    
    当用户发现两个概念其实是同一个实体时调用
    """
    try:
        logger.info("收到合并请求: %s -> %s", request.source_concept_id, request.target_concept_id)
        
        # 验证概念是否存在
        if not _concept_exists(request.source_concept_id):
            raise HTTPException(status_code=404, detail=f"源概念 '{request.source_concept_id}' 不存在")
        if not _concept_exists(request.target_concept_id):
            raise HTTPException(status_code=404, detail=f"目标概念 '{request.target_concept_id}' 不存在")
        
        # 生成请求 ID
        request_id = _generate_request_id("merge")
        
        # 存储到 Neo4j
        neo4j_client.execute_query(
            """
            CREATE (mr:MergeRequest {
                id: $id,
                source_concept_id: $source,
                target_concept_id: $target,
                reason: $reason,
                submitted_by: $submitted_by,
                status: 'pending',
                created_at: $created_at
            })
            """,
            {
                "id": request_id,
                "source": request.source_concept_id,
                "target": request.target_concept_id,
                "reason": request.reason,
                "submitted_by": request.submitted_by or "anonymous",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # 返回更新后的请求对象
        request.id = request_id
        return request
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("合并请求失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}") from e


@router.post("/correction", response_model=CorrectionRequest)
async def submit_correction_request(request: CorrectionRequest):
    """
    提交数据修正请求
    
    当用户发现概念描述、关系类型等错误时调用
    """
    try:
        logger.info("收到修正请求: %s.%s.%s", request.object_type, request.object_id, request.field)
        
        # 验证对象是否存在
        if request.object_type == "concept":
            if not _concept_exists(request.object_id):
                raise HTTPException(status_code=404, detail=f"概念 '{request.object_id}' 不存在")
        elif request.object_type == "relation":
            result = neo4j_client.execute_query(
                "MATCH ()-[r {id: $id}]->() RETURN r LIMIT 1",
                {"id": request.object_id}
            )
            if not result:
                raise HTTPException(status_code=404, detail=f"关系 '{request.object_id}' 不存在")
        elif request.object_type == "claim":
            result = neo4j_client.execute_query(
                "MATCH (c:Claim {id: $id}) RETURN c LIMIT 1",
                {"id": request.object_id}
            )
            if not result:
                raise HTTPException(status_code=404, detail=f"断言 '{request.object_id}' 不存在")
        
        # 生成请求 ID
        request_id = _generate_request_id("correction")
        
        # 存储到 Neo4j
        neo4j_client.execute_query(
            """
            CREATE (cr:CorrectionRequest {
                id: $id,
                object_type: $object_type,
                object_id: $object_id,
                field: $field,
                old_value: $old_value,
                new_value: $new_value,
                reason: $reason,
                submitted_by: $submitted_by,
                status: 'pending',
                created_at: $created_at
            })
            """,
            {
                "id": request_id,
                "object_type": request.object_type,
                "object_id": request.object_id,
                "field": request.field,
                "old_value": request.old_value,
                "new_value": request.new_value,
                "reason": request.reason,
                "submitted_by": request.submitted_by or "anonymous",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        request.id = request_id
        return request
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("修正请求失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}") from e


@router.post("/unlink", response_model=UnlinkRequest)
async def submit_unlink_request(request: UnlinkRequest):
    """
    提交实体解链请求
    
    当用户发现提及被错误链接到概念时调用
    """
    try:
        logger.info("收到解链请求: %s -> %s", request.mention_text, request.linked_concept_id)
        
        # 验证链接是否存在
        result = neo4j_client.execute_query(
            """
            MATCH (chunk:Chunk {id: $chunk_id})-[link:LINKS_TO]-(concept:Concept {name: $concept_id})
            RETURN link LIMIT 1
            """,
            {"chunk_id": request.chunk_id, "concept_id": request.linked_concept_id}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="链接不存在或已被删除")
        
        # 生成请求 ID
        request_id = _generate_request_id("unlink")
        
        # 存储到 Neo4j
        neo4j_client.execute_query(
            """
            CREATE (ur:UnlinkRequest {
                id: $id,
                mention_text: $mention_text,
                chunk_id: $chunk_id,
                linked_concept_id: $linked_concept_id,
                correct_concept_id: $correct_concept_id,
                reason: $reason,
                submitted_by: $submitted_by,
                status: 'pending',
                created_at: $created_at
            })
            """,
            {
                "id": request_id,
                "mention_text": request.mention_text,
                "chunk_id": request.chunk_id,
                "linked_concept_id": request.linked_concept_id,
                "correct_concept_id": request.correct_concept_id,
                "reason": request.reason,
                "submitted_by": request.submitted_by or "anonymous",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        request.id = request_id
        return request
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("解链请求失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}") from e


@router.get("/pending")
async def list_pending_requests(
    feedback_type: Optional[str] = None,
    limit: int = 20
):
    """
    列出待审核的反馈请求
    
    Args:
        feedback_type: 可选，过滤类型（merge/correction/unlink）
        limit: 返回数量
    """
    try:
        requests = []
        
        if not feedback_type or feedback_type == "merge":
            # 查询待审核的合并请求
            result = neo4j_client.execute_query(
                """
                MATCH (mr:MergeRequest {status: 'pending'})
                RETURN mr
                ORDER BY mr.created_at DESC
                LIMIT $limit
                """,
                {"limit": limit}
            )
            for record in result:
                mr = record.get("mr", {})
                requests.append({
                    "type": "merge",
                    "id": mr.get("id"),
                    "source_concept_id": mr.get("source_concept_id"),
                    "target_concept_id": mr.get("target_concept_id"),
                    "reason": mr.get("reason"),
                    "submitted_by": mr.get("submitted_by"),
                    "created_at": mr.get("created_at")
                })
        
        if not feedback_type or feedback_type == "correction":
            # 查询待审核的修正请求
            result = neo4j_client.execute_query(
                """
                MATCH (cr:CorrectionRequest {status: 'pending'})
                RETURN cr
                ORDER BY cr.created_at DESC
                LIMIT $limit
                """,
                {"limit": limit}
            )
            for record in result:
                cr = record.get("cr", {})
                requests.append({
                    "type": "correction",
                    "id": cr.get("id"),
                    "object_type": cr.get("object_type"),
                    "object_id": cr.get("object_id"),
                    "field": cr.get("field"),
                    "old_value": cr.get("old_value"),
                    "new_value": cr.get("new_value"),
                    "reason": cr.get("reason"),
                    "submitted_by": cr.get("submitted_by"),
                    "created_at": cr.get("created_at")
                })
        
        if not feedback_type or feedback_type == "unlink":
            # 查询待审核的解链请求
            result = neo4j_client.execute_query(
                """
                MATCH (ur:UnlinkRequest {status: 'pending'})
                RETURN ur
                ORDER BY ur.created_at DESC
                LIMIT $limit
                """,
                {"limit": limit}
            )
            for record in result:
                ur = record.get("ur", {})
                requests.append({
                    "type": "unlink",
                    "id": ur.get("id"),
                    "mention_text": ur.get("mention_text"),
                    "chunk_id": ur.get("chunk_id"),
                    "linked_concept_id": ur.get("linked_concept_id"),
                    "correct_concept_id": ur.get("correct_concept_id"),
                    "reason": ur.get("reason"),
                    "submitted_by": ur.get("submitted_by"),
                    "created_at": ur.get("created_at")
                })
        
        # 按创建时间排序
        requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {"requests": requests[:limit]}
    
    except Exception as e:
        logger.error("查询失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}") from e


@router.post("/review/{request_id}")
async def review_feedback(
    request_id: str,
    action: str,
    comment: Optional[str] = None
):
    """
    审核反馈请求
    
    Args:
        request_id: 请求 ID
        action: 审核动作（approve/reject）
        comment: 审核意见
    """
    try:
        logger.info("审核反馈: request_id=%s, action=%s", request_id, action)
        
        if action not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="action 必须是 approve 或 reject")
        
        new_status = "approved" if action == "approve" else "rejected"
        review_time = datetime.utcnow().isoformat()
        
        # 1. 查询请求并确定类型
        merge_result = neo4j_client.execute_query(
            "MATCH (mr:MergeRequest {id: $id}) RETURN mr",
            {"id": request_id}
        )
        
        correction_result = neo4j_client.execute_query(
            "MATCH (cr:CorrectionRequest {id: $id}) RETURN cr",
            {"id": request_id}
        )
        
        unlink_result = neo4j_client.execute_query(
            "MATCH (ur:UnlinkRequest {id: $id}) RETURN ur",
            {"id": request_id}
        )
        
        if not merge_result and not correction_result and not unlink_result:
            raise HTTPException(status_code=404, detail="请求不存在")
        
        # 2. 更新请求状态
        if merge_result:
            mr = merge_result[0].get("mr", {})
            neo4j_client.execute_query(
                """
                MATCH (mr:MergeRequest {id: $id})
                SET mr.status = $status, mr.reviewed_at = $reviewed_at, mr.review_comment = $comment
                """,
                {
                    "id": request_id,
                    "status": new_status,
                    "reviewed_at": review_time,
                    "comment": comment or ""
                }
            )
            
            # 3. 如果批准，执行对应操作
            if action == "approve":
                # 合并概念：将源概念的所有关系转移到目标概念
                neo4j_client.execute_query(
                    """
                    MATCH (source:Concept {name: $source_id})-[r]->(target)
                    MATCH (target_concept:Concept {name: $target_id})
                    MERGE (target_concept)-[new_r:same_as(type(r))]->(target)
                    SET new_r = properties(r)
                    WITH source, target_concept
                    OPTIONAL MATCH (source)-[r2]->()
                    DELETE r2
                    DELETE source
                    """,
                    {
                        "source_id": mr.get("source_concept_id"),
                        "target_id": mr.get("target_concept_id")
                    }
                )
                logger.info("已执行合并: %s -> %s", mr.get("source_concept_id"), mr.get("target_concept_id"))
        
        elif correction_result:
            cr = correction_result[0].get("cr", {})
            neo4j_client.execute_query(
                """
                MATCH (cr:CorrectionRequest {id: $id})
                SET cr.status = $status, cr.reviewed_at = $reviewed_at, cr.review_comment = $comment
                """,
                {
                    "id": request_id,
                    "status": new_status,
                    "reviewed_at": review_time,
                    "comment": comment or ""
                }
            )
            
            # 3. 如果批准，执行修正
            if action == "approve":
                object_type = cr.get("object_type")
                if object_type == "concept":
                    neo4j_client.execute_query(
                        f"""
                        MATCH (c:Concept {{name: $object_id}})
                        SET c.{cr.get('field')} = $new_value
                        """,
                        {
                            "object_id": cr.get("object_id"),
                            "new_value": cr.get("new_value")
                        }
                    )
                logger.info("已执行修正: %s.%s", cr.get("object_id"), cr.get("field"))
        
        elif unlink_result:
            ur = unlink_result[0].get("ur", {})
            neo4j_client.execute_query(
                """
                MATCH (ur:UnlinkRequest {id: $id})
                SET ur.status = $status, ur.reviewed_at = $reviewed_at, ur.review_comment = $comment
                """,
                {
                    "id": request_id,
                    "status": new_status,
                    "reviewed_at": review_time,
                    "comment": comment or ""
                }
            )
            
            # 3. 如果批准，执行解链
            if action == "approve":
                neo4j_client.execute_query(
                    """
                    MATCH (chunk:Chunk {id: $chunk_id})-[link:LINKS_TO]-(concept:Concept {name: $concept_id})
                    DELETE link
                    """,
                    {
                        "chunk_id": ur.get("chunk_id"),
                        "concept_id": ur.get("linked_concept_id")
                    }
                )
                
                # 如果提供了正确的概念，创建新链接
                if ur.get("correct_concept_id"):
                    neo4j_client.execute_query(
                        """
                        MATCH (chunk:Chunk {id: $chunk_id})
                        MATCH (concept:Concept {name: $concept_id})
                        MERGE (chunk)-[:LINKS_TO]->(concept)
                        """,
                        {
                            "chunk_id": ur.get("chunk_id"),
                            "concept_id": ur.get("correct_concept_id")
                        }
                    )
                
                logger.info("已执行解链: %s", ur.get("mention_text"))
        
        return {"status": "success", "request_id": request_id, "action": action}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("审核失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}") from e


__all__ = ["router"]

