"""
GraphRAG 查询 API

提供 GraphRAG 检索接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional
import logging

from graphrag.stages.stage7_query_service import QueryService

logger = logging.getLogger("graphrag.api.query")

router = APIRouter(prefix="/graphrag", tags=["GraphRAG"])


# 请求模型
class GraphRAGQueryRequest(BaseModel):
    """GraphRAG 查询请求"""
    
    question: str = Field(..., description="用户问题", min_length=5)
    mode: Literal["local", "global", "hybrid"] = Field(
        "hybrid",
        description="查询模式: local/global/hybrid"
    )
    top_k: int = Field(5, description="Top-K 结果数", ge=1, le=20)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "什么是 Transformer？",
                "mode": "hybrid",
                "top_k": 5
            }
        }


# 响应模型
class GraphRAGQueryResponse(BaseModel):
    """GraphRAG 查询响应"""
    
    answer: Dict[str, Any] = Field(..., description="结构化答案")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="引用的证据 ID")
    relevant_themes: List[str] = Field(default_factory=list, description="相关主题")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": {
                    "conclusion": "Transformer 是一种基于自注意力机制的神经网络架构...",
                    "reasoning_chain": [
                        {
                            "step": 1,
                            "statement": "Transformer 的核心创新是自注意力机制",
                            "evidence_ids": [1]
                        }
                    ],
                    "confidence": 0.95,
                    "caveats": None
                },
                "cited_evidence_ids": ["chunk_001", "chunk_002"],
                "relevant_themes": ["Transformer 架构与注意力机制"]
            }
        }


# 端点
@router.post("/query", response_model=GraphRAGQueryResponse)
async def graphrag_query(request: GraphRAGQueryRequest):
    """
    GraphRAG 查询接口
    
    支持三种查询模式：
    - local: 局部图遍历
    - global: 全局社区聚合
    - hybrid: 混合模式（推荐）
    """
    try:
        logger.info(f"收到 GraphRAG 查询: question={request.question}, mode={request.mode}")
        
        # 调用查询服务
        query_service = QueryService()
        result = query_service.answer(
            question=request.question,
            mode=request.mode,
            top_k=request.top_k
        )
        
        return GraphRAGQueryResponse(**result)
    
    except Exception as e:
        logger.error(f"GraphRAG 查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/themes")
async def list_themes(doc_id: Optional[str] = None):
    """
    列出所有主题
    
    Args:
        doc_id: 可选，过滤特定文档的主题
    """
    try:
        from infra.neo4j_client import Neo4jClient
        
        neo4j_client = Neo4jClient()
        neo4j_client.initialize()
        
        # 构建查询
        if doc_id:
            query = """
            MATCH (t:Theme)
            WHERE t.id CONTAINS $doc_id
            RETURN t.id AS id,
                   t.label AS label,
                   t.summary AS summary,
                   t.level AS level,
                   t.keywords AS keywords,
                   t.member_count AS member_count,
                   t.created_at AS created_at
            ORDER BY t.level, t.label
            """
            params = {"doc_id": doc_id}
        else:
            query = """
            MATCH (t:Theme)
            RETURN t.id AS id,
                   t.label AS label,
                   t.summary AS summary,
                   t.level AS level,
                   t.keywords AS keywords,
                   t.member_count AS member_count,
                   t.created_at AS created_at
            ORDER BY t.level, t.label
            """
            params = {}
        
        result = neo4j_client.execute_query(query, params)
        
        themes = []
        for record in result:
            # 格式化时间戳
            created_at = record.get("created_at")
            if created_at:
                created_at = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
            
            themes.append({
                "id": record["id"],
                "label": record["label"],
                "summary": record["summary"],
                "level": record["level"],
                "keywords": record.get("keywords", []),
                "member_count": record.get("member_count", 0),
                "created_at": created_at
            })
        
        return {
            "themes": themes,
            "total": len(themes)
        }
    
    except Exception as e:
        logger.error(f"查询主题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/theme/{theme_id}")
async def get_theme_detail(theme_id: str):
    """
    获取主题详情
    
    Args:
        theme_id: 主题 ID
    """
    try:
        from infra.neo4j_client import Neo4jClient
        import json
        
        neo4j_client = Neo4jClient()
        neo4j_client.initialize()
        
        # 查询主题节点
        query = """
        MATCH (t:Theme {id: $theme_id})
        RETURN t.id AS id,
               t.label AS label,
               t.summary AS summary,
               t.level AS level,
               t.keywords AS keywords,
               t.community_id AS community_id,
               t.member_count AS member_count,
               t.concept_ids AS concept_ids,
               t.claim_ids AS claim_ids,
               t.key_evidence AS key_evidence,
               t.build_version AS build_version,
               t.created_at AS created_at,
               t.updated_at AS updated_at
        """
        
        result = neo4j_client.execute_query(query, {"theme_id": theme_id})
        
        if not result:
            raise HTTPException(status_code=404, detail=f"主题不存在: {theme_id}")
        
        record = result[0]
        
        # 格式化时间戳
        created_at = record.get("created_at")
        updated_at = record.get("updated_at")
        
        if created_at:
            created_at = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        if updated_at:
            updated_at = updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)
        
        # 解析 key_evidence (如果是 JSON 字符串)
        key_evidence = record.get("key_evidence")
        if key_evidence and isinstance(key_evidence, str):
            try:
                key_evidence = json.loads(key_evidence)
            except:
                key_evidence = None
        
        # 查询相关的概念和论断
        concepts_query = """
        MATCH (t:Theme {id: $theme_id})<-[:BELONGS_TO_THEME]-(c:Concept)
        RETURN c.name AS name, c.definition AS definition
        LIMIT 10
        """
        
        claims_query = """
        MATCH (t:Theme {id: $theme_id})<-[:BELONGS_TO_THEME]-(cl:Claim)
        RETURN cl.id AS id, cl.text AS text
        LIMIT 10
        """
        
        concepts_result = neo4j_client.execute_query(concepts_query, {"theme_id": theme_id})
        claims_result = neo4j_client.execute_query(claims_query, {"theme_id": theme_id})
        
        concepts = [{
            "name": c["name"],
            "definition": c.get("definition")
        } for c in concepts_result]
        
        claims = [{
            "id": c["id"],
            "text": c["text"]
        } for c in claims_result]
        
        return {
            "id": record["id"],
            "label": record["label"],
            "summary": record["summary"],
            "level": record["level"],
            "keywords": record.get("keywords", []),
            "community_id": record.get("community_id"),
            "member_count": record.get("member_count", 0),
            "concept_ids": record.get("concept_ids", []),
            "claim_ids": record.get("claim_ids", []),
            "key_evidence": key_evidence,
            "build_version": record.get("build_version"),
            "created_at": created_at,
            "updated_at": updated_at,
            "concepts": concepts,
            "claims": claims
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询主题详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


__all__ = ["router"]

