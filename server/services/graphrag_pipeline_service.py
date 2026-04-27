"""
GraphRAG Pipeline Service

封装 GraphRAG Pipeline，提供文档处理服务
支持软件工程领域知识图谱构建
"""

import logging
import asyncio
import time
from typing import Callable, Dict, Any, Optional, List
from pathlib import Path

from services.parser import ParserFactory
from graphrag.stages.pipeline import (
    GraphRAGPipeline,
    PipelineConfig,
    PipelineResult,
    create_pipeline
)
from config import settings
from infra.neo4j_client import neo4j_client

logger = logging.getLogger("services.graphrag_pipeline_service")


class GraphRAGPipelineService:
    """
    GraphRAG Pipeline 服务
    
    封装九阶段知识图谱构建流水线，提供统一的文档处理接口
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if GraphRAGPipelineService._initialized:
            return
        
        self._pipeline: Optional[GraphRAGPipeline] = None
        self._available = False
        
        try:
            self._init_pipeline()
            GraphRAGPipelineService._initialized = True
        except Exception as e:
            logger.warning(f"GraphRAGPipelineService 初始化失败: {e}")
    
    def _init_pipeline(self):
        """初始化 Pipeline"""
        config = PipelineConfig(
            enable_stage0=False,
            enable_stage8=False,
            enable_stage7=True,
            concurrency_limit=5,
            batch_size=10,
            min_confidence=0.6,
            enable_nli_verification=True,
            enable_domain_filter=True,
            stages_to_run=[1, 2, 3, 4, 5, 6, 7]
        )
        
        self._pipeline = GraphRAGPipeline(config)
        self._available = True
        logger.info("GraphRAGPipelineService 初始化成功")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available and self._pipeline is not None
    
    async def process_document(
        self,
        file_path: str,
        doc_id: str,
        root_topic: Optional[str] = None,
        user_prompt: Optional[str] = None,
        timeout: int = 300,
        progress_callback: Optional[Callable[[int, str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        处理文档，构建知识图谱
        
        Args:
            file_path: 文档文件路径
            doc_id: 文档ID
            root_topic: 根主题（可选）
            user_prompt: 用户自定义提示词（可选）
            timeout: 超时时间（秒）
            progress_callback: 进度回调函数 (stage_index, stage_name, progress_percent)
        
        Returns:
            处理结果统计
        """
        if not self.is_available():
            raise RuntimeError("GraphRAGPipelineService 不可用")
        
        logger.info(f"[GraphRAGPipelineService] 开始处理文档: doc_id={doc_id}, file={file_path}")
        
        start_time = time.time()
        
        try:
            kind = self._get_document_kind(file_path)
            
            parser = ParserFactory.create_parser(kind, chunk_size=2000)
            full_text, parser_chunks = parser.parse(file_path)
            
            logger.info(f"[GraphRAGPipelineService] 解析完成: {len(parser_chunks)} 个Chunk")
            
            document_meta = {
                "title": Path(file_path).stem,
                "source_type": kind,
                "user_prompt": user_prompt,
                "root_topic": root_topic
            }
            
            result = await asyncio.wait_for(
                self._pipeline.process(
                    doc_id=doc_id,
                    parser_chunks=parser_chunks,
                    document_meta=document_meta,
                    raw_text=full_text,
                    progress_callback=progress_callback
                ),
                timeout=timeout
            )
            
            stats = self._convert_result_to_stats(result)
            
            self._update_document_stats(doc_id, result)
            
            execution_time = time.time() - start_time
            logger.info(
                f"[GraphRAGPipelineService] 处理完成: doc_id={doc_id}, "
                f"chunks={result.chunks_count}, entities={result.entities_count}, "
                f"claims={result.claims_count}, time={execution_time:.2f}s"
            )
            
            return stats
            
        except asyncio.TimeoutError:
            logger.error(f"[GraphRAGPipelineService] 处理超时: doc_id={doc_id}")
            raise
        except Exception as e:
            logger.error(f"[GraphRAGPipelineService] 处理失败: {e}", exc_info=True)
            raise
    
    async def process_document_with_chunks(
        self,
        doc_id: str,
        parser_chunks: List[Any],
        document_meta: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
        progress_callback: Optional[Callable[[int, str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        使用预解析的Chunk处理文档
        
        Args:
            doc_id: 文档ID
            parser_chunks: Parser预处理的Chunk列表
            document_meta: 文档元数据
            timeout: 超时时间（秒）
            progress_callback: 进度回调函数 (stage_index, stage_name, progress_percent)
        
        Returns:
            处理结果统计
        """
        if not self.is_available():
            raise RuntimeError("GraphRAGPipelineService 不可用")
        
        logger.info(f"[GraphRAGPipelineService] 开始处理Chunk: doc_id={doc_id}, chunks={len(parser_chunks)}")
        
        try:
            result = await asyncio.wait_for(
                self._pipeline.process(
                    doc_id=doc_id,
                    parser_chunks=parser_chunks,
                    document_meta=document_meta,
                    progress_callback=progress_callback
                ),
                timeout=timeout
            )
            
            stats = self._convert_result_to_stats(result)
            
            self._update_document_stats(doc_id, result)
            
            return stats
            
        except asyncio.TimeoutError:
            logger.error(f"[GraphRAGPipelineService] 处理超时: doc_id={doc_id}")
            raise
        except Exception as e:
            logger.error(f"[GraphRAGPipelineService] 处理失败: {e}", exc_info=True)
            raise
    
    def process_document_sync(
        self,
        file_path: str,
        doc_id: str,
        root_topic: Optional[str] = None,
        user_prompt: Optional[str] = None,
        timeout: int = 300,
        progress_callback: Optional[Callable[[int, str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        同步处理文档（在后台线程中使用）
        
        Args:
            file_path: 文档文件路径
            doc_id: 文档ID
            root_topic: 根主题（可选）
            user_prompt: 用户自定义提示词（可选）
            timeout: 超时时间（秒）
            progress_callback: 进度回调函数 (stage_index, stage_name, progress_percent)
        
        Returns:
            处理结果统计
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.process_document(
                    file_path=file_path,
                    doc_id=doc_id,
                    root_topic=root_topic,
                    user_prompt=user_prompt,
                    timeout=timeout,
                    progress_callback=progress_callback
                )
            )
        except Exception as e:
            logger.error(f"[GraphRAGPipelineService] 同步处理失败: {e}")
            raise
        finally:
            loop.close()
    
    def _get_document_kind(self, file_path: str) -> str:
        """获取文档类型"""
        ext = Path(file_path).suffix.lower()
        kind_map = {
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
        return kind_map.get(ext, "txt")
    
    def _convert_result_to_stats(self, result: PipelineResult) -> Dict[str, Any]:
        """将PipelineResult转换为统计字典"""
        return {
            "chunks": result.chunks_count,
            "entities": result.entities_count,
            "claims": result.claims_count,
            "themes": result.themes_count,
            "relationships": result.relationships_count,
            "execution_time": result.execution_time,
            "success": result.success,
            "errors": result.errors,
            "stage_metrics": result.stage_metrics,
            "quality_metrics": result.quality_metrics,
            "mode": "graphrag_pipeline"
        }
    
    def _update_document_stats(self, doc_id: str, result: PipelineResult):
        """更新文档统计信息到Neo4j"""
        try:
            import json
            
            neo4j_client.execute_query("""
                MATCH (d:Document {id: $doc_id})
                SET d.stats = $stats,
                    d.chunk_count = $chunk_count,
                    d.claim_count = $claim_count,
                    d.concept_count = $concept_count,
                    d.relation_count = $relation_count,
                    d.theme_count = $theme_count,
                    d.processing_status = $status,
                    d.processed_at = datetime(),
                    d.updated_at = datetime(),
                    d.processing_mode = "graphrag_pipeline"
                RETURN d
            """, {
                "doc_id": doc_id,
                "stats": json.dumps({
                    "chunks": result.chunks_count,
                    "entities": result.entities_count,
                    "claims": result.claims_count,
                    "themes": result.themes_count,
                    "execution_time": result.execution_time,
                    "mode": "graphrag_pipeline"
                }),
                "chunk_count": result.chunks_count,
                "claim_count": result.claims_count,
                "concept_count": result.entities_count,
                "relation_count": result.relationships_count,
                "theme_count": result.themes_count,
                "status": "completed" if result.success else "failed"
            })
            
            logger.info(f"[GraphRAGPipelineService] 文档统计已更新: doc_id={doc_id}")
            
        except Exception as e:
            logger.warning(f"[GraphRAGPipelineService] 更新文档统计失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Pipeline统计信息"""
        if self._pipeline:
            return self._pipeline.get_stats()
        return {}
    
    def refresh_feedback(self):
        """刷新反馈数据"""
        if self._pipeline:
            self._pipeline.refresh_entity_linker_feedback()


graphrag_pipeline_service = GraphRAGPipelineService()

__all__ = ["GraphRAGPipelineService", "graphrag_pipeline_service"]
