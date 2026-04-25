"""
GraphRAG Pipeline - 软件工程领域知识图谱构建流水线

高质量、高效率的八阶段知识图谱构建系统
支持接受parser预处理后的文本块，构建软件工程领域知识图谱

阶段流程:
Stage 0: 语义分块 (SemanticChunker) - 可选，parser已预处理
Stage 1: 指代消解 (CoreferenceResolver)
Stage 2: 实体链接 (EntityLinker)
Stage 3: 论断抽取 (ClaimExtractor)
Stage 4: 主题构建 (ThemeBuilder)
Stage 5: 谓词治理 (PredicateGovernor)
Stage 6: 图谱存储 (GraphService)
Stage 7: 查询服务 (QueryService) - 可选
Stage 8: 度量服务 (MetricsService)
"""

import asyncio
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from models.document import Chunk as ParserChunk
from graphrag.models.chunk import ChunkMetadata
from graphrag.models.claim import Claim, ClaimRelation
from graphrag.config import get_config, GovernanceStatus
from graphrag.stages.stage0_chunker import SemanticChunker
from graphrag.stages.stage1_coref import CoreferenceResolver, CorefResult
from graphrag.stages.stage2_entity_linker import EntityLinker, LinkingResult
from graphrag.stages.stage3_claim_extractor import ClaimExtractor
from graphrag.stages.stage4_theme_builder import ThemeBuilder
from graphrag.stages.stage5_predicate_governor import PredicateGovernor
from graphrag.stages.stage6_graph_service import GraphService
from graphrag.stages.stage7_query_service import QueryService
from graphrag.stages.stage8_metrics_service import MetricsService
from graphrag.utils.embedding import get_embedding
from config import settings

logger = logging.getLogger("graphrag.pipeline")


class PipelineStage(Enum):
    """流水线阶段枚举"""
    CHUNKER = 0
    COREF = 1
    ENTITY_LINKER = 2
    CLAIM_EXTRACTOR = 3
    THEME_BUILDER = 4
    PREDICATE_GOVERNOR = 5
    GRAPH_SERVICE = 6
    QUERY_SERVICE = 7
    METRICS_SERVICE = 8


@dataclass
class PipelineConfig:
    """流水线配置"""
    enable_stage0: bool = False
    enable_stage7: bool = False
    enable_stage8: bool = True
    
    concurrency_limit: int = 5
    batch_size: int = 10
    
    min_confidence: float = 0.6
    enable_nli_verification: bool = True
    enable_domain_filter: bool = True
    
    save_intermediate: bool = False
    intermediate_dir: str = "./debug_output"
    
    stages_to_run: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 8])


@dataclass
class PipelineResult:
    """流水线执行结果"""
    doc_id: str
    build_version: str
    
    chunks_count: int = 0
    entities_count: int = 0
    claims_count: int = 0
    themes_count: int = 0
    relationships_count: int = 0
    
    stage_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    execution_time: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)


class ChunkConverter:
    """
    Chunk转换器
    
    将Parser预处理后的Chunk转换为GraphRAG所需的ChunkMetadata
    """
    
    def __init__(self):
        self.config = get_config()
        self.window_size = self.config.thresholds.get("chunking", "window_size", 4)
        self.step_size = self.config.thresholds.get("chunking", "step_size", 2)
    
    def convert(
        self, 
        parser_chunks: List[ParserChunk], 
        build_version: str
    ) -> List[ChunkMetadata]:
        """
        转换Parser Chunk列表为ChunkMetadata列表
        
        Args:
            parser_chunks: Parser预处理后的Chunk列表
            build_version: 构建版本标签
        
        Returns:
            ChunkMetadata列表
        """
        chunks = []
        
        for idx, pc in enumerate(parser_chunks):
            if len(pc.text.strip()) < 50:
                logger.debug(f"跳过过短的Chunk: {pc.chunk_id}")
                continue
            
            chunk_id = f"{pc.doc_id}:{idx}"
            
            meta = pc.meta or {}
            
            chunk = ChunkMetadata(
                id=chunk_id,
                doc_id=pc.doc_id,
                text=pc.text,
                chunk_index=idx,
                section_path=meta.get("section"),
                page_num=meta.get("page"),
                sentence_ids=[],
                sentence_count=0,
                window_start=0,
                window_end=0,
                build_version=build_version
            )
            
            chunks.append(chunk)
        
        logger.info(f"[ChunkConverter] 转换完成: {len(parser_chunks)} -> {len(chunks)} 个ChunkMetadata")
        return chunks
    
    def convert_single(
        self, 
        parser_chunk: ParserChunk, 
        chunk_index: int,
        build_version: str
    ) -> Optional[ChunkMetadata]:
        """
        转换单个Parser Chunk为ChunkMetadata
        
        Args:
            parser_chunk: Parser预处理后的Chunk
            chunk_index: Chunk索引
            build_version: 构建版本标签
        
        Returns:
            ChunkMetadata或None（如果文本太短）
        """
        if len(parser_chunk.text.strip()) < 50:
            return None
        
        chunk_id = f"{parser_chunk.doc_id}:{chunk_index}"
        meta = parser_chunk.meta or {}
        
        return ChunkMetadata(
            id=chunk_id,
            doc_id=parser_chunk.doc_id,
            text=parser_chunk.text,
            chunk_index=chunk_index,
            section_path=meta.get("section"),
            page_num=meta.get("page"),
            sentence_ids=[],
            sentence_count=0,
            window_start=0,
            window_end=0,
            build_version=build_version
        )


class GraphRAGPipeline:
    """
    GraphRAG知识图谱构建流水线
    
    高质量、高效率的八阶段知识图谱构建系统
    专门针对软件工程领域优化
    
    使用示例:
    ```python
    from graphrag.stages.pipeline import GraphRAGPipeline
    from services.parser import PDFParser
    
    # 1. 解析文档
    parser = PDFParser()
    full_text, parser_chunks = parser.parse("software_engineering.pdf")
    
    # 2. 构建知识图谱
    pipeline = GraphRAGPipeline()
    result = await pipeline.process(
        doc_id="se_textbook_001",
        parser_chunks=parser_chunks,
        document_meta={
            "title": "软件工程导论",
            "source_type": "textbook"
        }
    )
    
    print(f"构建完成: {result.claims_count} 个论断, {result.entities_count} 个实体")
    ```
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        初始化流水线
        
        Args:
            config: 流水线配置，如果为None则使用默认配置
        """
        self.config = config or PipelineConfig()
        self.graphrag_config = get_config()
        
        self._init_components()
        
        self._stats = {
            "documents_processed": 0,
            "total_chunks": 0,
            "total_entities": 0,
            "total_claims": 0,
            "total_errors": 0
        }
        
        logger.info(f"[GraphRAGPipeline] 初始化完成, stages_to_run={self.config.stages_to_run}")
    
    def _init_components(self):
        """初始化各阶段组件"""
        stages = self.config.stages_to_run
        
        self.chunker = SemanticChunker() if 0 in stages else None
        self.coref_resolver = CoreferenceResolver() if 1 in stages else None
        self.entity_linker = EntityLinker(fast_mode=True) if 2 in stages else None
        self.claim_extractor = ClaimExtractor(enable_nli=False) if 3 in stages else None
        self.theme_builder = ThemeBuilder() if 4 in stages else None
        self.predicate_governor = PredicateGovernor() if 5 in stages else None
        self.graph_service = GraphService() if 6 in stages else None
        self.query_service = QueryService() if 7 in stages else None
        self.metrics_service = MetricsService() if 8 in stages else None
        
        self.chunk_converter = ChunkConverter()
        
        logger.info("[GraphRAGPipeline] 组件初始化: EntityLinker(fast_mode=True), ClaimExtractor(enable_nli=False)")
    
    async def process(
        self,
        doc_id: str,
        parser_chunks: List[ParserChunk],
        document_meta: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None
    ) -> PipelineResult:
        """
        处理文档，构建知识图谱
        
        Args:
            doc_id: 文档ID
            parser_chunks: Parser预处理后的Chunk列表
            document_meta: 文档元数据（title, source_type, author等）
            raw_text: 原始文本（可选，用于Stage 0重新分块）
        
        Returns:
            PipelineResult: 构建结果
        """
        start_time = time.time()
        build_version = f"{doc_id}_{int(time.time())}"
        
        logger.info(f"{'='*60}")
        logger.info(f"[GraphRAGPipeline] 开始处理文档: doc_id={doc_id}")
        logger.info(f"[GraphRAGPipeline] 输入Chunk数: {len(parser_chunks)}")
        logger.info(f"[GraphRAGPipeline] 构建版本: {build_version}")
        logger.info(f"{'='*60}")
        
        result = PipelineResult(
            doc_id=doc_id,
            build_version=build_version
        )
        
        try:
            chunks = await self._run_stage0(
                doc_id, parser_chunks, raw_text, build_version, result
            )
            
            if not chunks:
                result.errors.append("Stage 0: 没有生成有效的Chunk")
                result.success = False
                return result
            
            await self._store_document(doc_id, document_meta, build_version)
            
            chunks = await self._run_stage1(chunks, result)
            
            entities = await self._run_stage2(chunks, result)
            
            claims, relations = await self._run_stage3(chunks, result)
            
            themes = await self._run_stage4(doc_id, build_version, result)
            
            governed_claims = await self._run_stage5(claims, result)
            
            await self._run_stage6(
                doc_id, chunks, entities, governed_claims, relations, result
            )
            
            if self.config.enable_stage8 and 8 in self.config.stages_to_run:
                await self._run_stage8(doc_id, result)
            
            result.chunks_count = len(chunks)
            result.entities_count = len(entities)
            result.claims_count = len(governed_claims)
            result.themes_count = len(themes) if themes else 0
            result.relationships_count = len(relations)
            
            self._stats["documents_processed"] += 1
            self._stats["total_chunks"] += len(chunks)
            self._stats["total_entities"] += len(entities)
            self._stats["total_claims"] += len(governed_claims)
            
        except Exception as e:
            logger.error(f"[GraphRAGPipeline] 处理失败: {e}", exc_info=True)
            result.errors.append(str(e))
            result.success = False
            self._stats["total_errors"] += 1
        
        result.execution_time = time.time() - start_time
        
        logger.info(f"{'='*60}")
        logger.info(f"[GraphRAGPipeline] 处理完成: doc_id={doc_id}")
        logger.info(f"[GraphRAGPipeline] 结果: chunks={result.chunks_count}, "
                   f"entities={result.entities_count}, claims={result.claims_count}")
        logger.info(f"[GraphRAGPipeline] 耗时: {result.execution_time:.2f}s")
        logger.info(f"{'='*60}")
        
        return result
    
    async def _run_stage0(
        self,
        doc_id: str,
        parser_chunks: List[ParserChunk],
        raw_text: Optional[str],
        build_version: str,
        result: PipelineResult
    ) -> List[ChunkMetadata]:
        """
        Stage 0: 语义分块
        
        如果parser_chunks已提供，直接转换；否则使用SemanticChunker重新分块
        """
        stage_start = time.time()
        logger.info(f"[Stage 0] 开始语义分块...")
        
        chunks = []
        
        if parser_chunks:
            chunks = self.chunk_converter.convert(parser_chunks, build_version)
            logger.info(f"[Stage 0] 使用Parser预处理的Chunk: {len(chunks)} 个")
        elif raw_text and self.chunker:
            chunks = self.chunker.split(doc_id, raw_text, build_version)
            logger.info(f"[Stage 0] 使用SemanticChunker分块: {len(chunks)} 个")
        else:
            logger.warning("[Stage 0] 没有有效的输入，跳过分块")
        
        chunks = await self._generate_embeddings_batch(chunks)
        
        result.stage_metrics["stage0"] = {
            "chunks_count": len(chunks),
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 0] 完成: {len(chunks)} 个Chunk")
        return chunks
    
    async def _run_stage1(
        self,
        chunks: List[ChunkMetadata],
        result: PipelineResult
    ) -> List[ChunkMetadata]:
        """
        Stage 1: 指代消解
        """
        if not self.coref_resolver or 1 not in self.config.stages_to_run:
            logger.info("[Stage 1] 跳过指代消解")
            return chunks
        
        stage_start = time.time()
        logger.info(f"[Stage 1] 开始指代消解: {len(chunks)} 个Chunk")
        
        total_coverage = 0.0
        total_aliases = 0
        
        for chunk in chunks:
            try:
                coref_result = self.coref_resolver.resolve(chunk)
                
                if coref_result.resolved_text:
                    chunk.resolved_text = coref_result.resolved_text
                
                if coref_result.alias_map:
                    chunk.coreference_aliases = coref_result.alias_map
                    total_aliases += len(coref_result.alias_map)
                
                chunk.coref_mode = coref_result.mode
                total_coverage += coref_result.coverage
                
            except Exception as e:
                logger.warning(f"[Stage 1] Chunk {chunk.id} 指代消解失败: {e}")
        
        avg_coverage = total_coverage / len(chunks) if chunks else 0
        
        result.stage_metrics["stage1"] = {
            "total_aliases": total_aliases,
            "avg_coverage": avg_coverage,
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 1] 完成: 平均覆盖率={avg_coverage:.2%}, 别名数={total_aliases}")
        return chunks
    
    async def _run_stage2(
        self,
        chunks: List[ChunkMetadata],
        result: PipelineResult
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: 实体链接
        """
        if not self.entity_linker or 2 not in self.config.stages_to_run:
            logger.info("[Stage 2] 跳过实体链接")
            return []
        
        stage_start = time.time()
        logger.info(f"[Stage 2] 开始实体链接: {len(chunks)} 个Chunk")
        
        all_entities = []
        
        for chunk in chunks:
            try:
                entities = self.entity_linker.link_and_extract(chunk)
                all_entities.extend(entities)
            except Exception as e:
                logger.warning(f"[Stage 2] Chunk {chunk.id} 实体链接失败: {e}")
        
        unique_entities = {}
        for entity in all_entities:
            key = entity.get("concept_id") or entity.get("concept_name")
            if key and key not in unique_entities:
                unique_entities[key] = entity
        
        entities = list(unique_entities.values())
        
        result.stage_metrics["stage2"] = {
            "total_entities": len(all_entities),
            "unique_entities": len(entities),
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 2] 完成: {len(entities)} 个唯一实体")
        return entities
    
    async def _run_stage3(
        self,
        chunks: List[ChunkMetadata],
        result: PipelineResult
    ) -> Tuple[List[Claim], List[ClaimRelation]]:
        """
        Stage 3: 论断抽取
        """
        if not self.claim_extractor or 3 not in self.config.stages_to_run:
            logger.info("[Stage 3] 跳过论断抽取")
            return [], []
        
        stage_start = time.time()
        logger.info(f"[Stage 3] 开始论断抽取: {len(chunks)} 个Chunk")
        
        all_claims = []
        all_relations = []
        
        for i, chunk in enumerate(chunks):
            try:
                adjacent_chunks = None
                if i > 0 or i < len(chunks) - 1:
                    adjacent_chunks = chunks[max(0, i-1):min(len(chunks), i+2)]
                
                claims, relations = self.claim_extractor.extract(chunk, adjacent_chunks)
                all_claims.extend(claims)
                all_relations.extend(relations)
                
            except Exception as e:
                logger.warning(f"[Stage 3] Chunk {chunk.id} 论断抽取失败: {e}")
        
        unique_claims = {}
        for claim in all_claims:
            if claim.normalized_text_hash:
                if claim.normalized_text_hash not in unique_claims:
                    unique_claims[claim.normalized_text_hash] = claim
            else:
                unique_claims[claim.id] = claim
        
        claims = list(unique_claims.values())
        
        result.stage_metrics["stage3"] = {
            "total_claims": len(all_claims),
            "unique_claims": len(claims),
            "total_relations": len(all_relations),
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 3] 完成: {len(claims)} 个唯一论断, {len(all_relations)} 个关系")
        return claims, all_relations
    
    async def _run_stage4(
        self,
        doc_id: str,
        build_version: str,
        result: PipelineResult
    ) -> Optional[List[Any]]:
        """
        Stage 4: 主题构建
        """
        if not self.theme_builder or 4 not in self.config.stages_to_run:
            logger.info("[Stage 4] 跳过主题构建")
            return None
        
        stage_start = time.time()
        logger.info(f"[Stage 4] 开始主题构建: doc_id={doc_id}")
        
        try:
            themes = self.theme_builder.build(doc_id, build_version)
            
            result.stage_metrics["stage4"] = {
                "themes_count": len(themes) if themes else 0,
                "execution_time": time.time() - stage_start
            }
            
            logger.info(f"[Stage 4] 完成: {len(themes) if themes else 0} 个主题")
            return themes
            
        except Exception as e:
            logger.warning(f"[Stage 4] 主题构建失败: {e}")
            result.stage_metrics["stage4"] = {
                "themes_count": 0,
                "error": str(e),
                "execution_time": time.time() - stage_start
            }
            return None
    
    async def _run_stage5(
        self,
        claims: List[Claim],
        result: PipelineResult
    ) -> List[Claim]:
        """
        Stage 5: 谓词治理
        
        注意：Claim对象本身不需要谓词治理，因为Claim是论断文本而非关系。
        谓词治理主要用于ClaimRelation（论断间关系）。
        此阶段目前直接返回所有Claim。
        """
        if not self.predicate_governor or 5 not in self.config.stages_to_run:
            logger.info("[Stage 5] 跳过谓词治理")
            return claims
        
        stage_start = time.time()
        logger.info(f"[Stage 5] 谓词治理: 直接接受 {len(claims)} 个论断")
        
        result.stage_metrics["stage5"] = {
            "accepted": len(claims),
            "rejected": 0,
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 5] 完成: 接受={len(claims)}")
        return claims
    
    async def _run_stage6(
        self,
        doc_id: str,
        chunks: List[ChunkMetadata],
        entities: List[Dict[str, Any]],
        claims: List[Claim],
        relations: List[ClaimRelation],
        result: PipelineResult
    ) -> None:
        """
        Stage 6: 图谱存储
        """
        if not self.graph_service or 6 not in self.config.stages_to_run:
            logger.info("[Stage 6] 跳过图谱存储")
            return
        
        stage_start = time.time()
        logger.info(f"[Stage 6] 开始图谱存储: doc_id={doc_id}, chunks={len(chunks)}, entities={len(entities)}, claims={len(claims)}, relations={len(relations)}")
        
        # 打印第一个 chunk 的详细信息用于调试
        if chunks:
            first_chunk = chunks[0]
            logger.info(f"[Stage 6] 第一个Chunk详情: id={first_chunk.id}, doc_id={first_chunk.doc_id}, text_len={len(first_chunk.text)}")
        
        chunks_stored = 0
        entities_stored = 0
        claims_stored = 0
        relations_stored = 0
        mentions_relations_stored = 0
        contains_claim_relations_stored = 0
        contains_relations_stored = 0
        evidence_from_relations_stored = 0
        belongs_to_theme_relations_stored = 0
        
        # 1. 存储 Chunk 节点
        logger.info(f"[Stage 6] 开始存储 {len(chunks)} 个 Chunk 节点")
        for chunk in chunks:
            try:
                self.graph_service.store_chunk(chunk.model_dump())
                chunks_stored += 1
                
                # 创建 Document → Chunk 的 CONTAINS 关系
                try:
                    self.graph_service.store_relationship(
                        rel_type="CONTAINS",
                        source_id=doc_id,
                        target_id=chunk.id,
                        rel_data={"chunk_index": chunk.chunk_index}
                    )
                    contains_relations_stored += 1
                except Exception as e:
                    logger.warning(f"[Stage 6] 存储 CONTAINS 关系失败: {e}")
                    
            except Exception as e:
                logger.warning(f"[Stage 6] 存储Chunk {chunk.id} 失败: {e}")
        
        logger.info(f"[Stage 6] Chunk 存储完成: {chunks_stored}/{len(chunks)}, CONTAINS关系: {contains_relations_stored}")
        
        # 2. 存储实体节点（Concept）- 先生成向量再存储
        logger.info(f"[Stage 6] 开始存储 {len(entities)} 个实体节点并创建 MENTIONS 关系")
        
        # 为Concept生成向量嵌入
        entities = self._generate_entity_embeddings_batch(entities)
        
        for entity in entities:
            try:
                concept_id = entity.get("concept_id") or hashlib.sha256(
                    entity.get("concept_name", "").encode()
                ).hexdigest()[:16]
                
                concept_data = {
                    "id": concept_id,
                    "name": entity.get("concept_name"),
                    "description": entity.get("description"),
                    "domain": "software_engineering",
                    "embedding": entity.get("embedding")
                }
                
                if self.graph_service.store_entity("Concept", concept_data):
                    entities_stored += 1
                    
                    # 创建 Chunk → Concept 的 MENTIONS 关系
                    chunk_id = entity.get("chunk_id")
                    if chunk_id:
                        try:
                            self.graph_service.store_relationship(
                                rel_type="MENTIONS",
                                source_id=chunk_id,
                                target_id=concept_id,
                                rel_data={"confidence": entity.get("confidence", 0.8)}
                            )
                            mentions_relations_stored += 1
                        except Exception as e:
                            logger.warning(f"[Stage 6] 存储 MENTIONS 关系失败: {e}")
                        
                        # 创建 Concept → Chunk 的 EVIDENCE_FROM 关系
                        try:
                            self.graph_service.store_relationship(
                                rel_type="EVIDENCE_FROM",
                                source_id=concept_id,
                                target_id=chunk_id,
                                rel_data={}
                            )
                            evidence_from_relations_stored += 1
                        except Exception as e:
                            logger.warning(f"[Stage 6] 存储 EVIDENCE_FROM 关系失败: {e}")
                            
            except Exception as e:
                logger.warning(f"[Stage 6] 存储实体失败: {e}")
        
        # 3. 存储 Claim 节点 - 先生成向量再存储
        logger.info(f"[Stage 6] 开始存储 {len(claims)} 个 Claim 节点并创建 CONTAINS_CLAIM 关系")
        
        # 为Claim生成向量嵌入
        claims = self._generate_claim_embeddings_batch(claims)
        
        for claim in claims:
            try:
                # 使用 model_dump 并包含 embedding
                claim_data = claim.model_dump()
                self.graph_service.store_claim(claim_data)
                claims_stored += 1
                
                # 创建 Chunk → Claim 的 CONTAINS_CLAIM 关系
                if claim.chunk_id:
                    try:
                        self.graph_service.store_relationship(
                            rel_type="CONTAINS_CLAIM",
                            source_id=claim.chunk_id,
                            target_id=claim.id,
                            rel_data={"confidence": claim.confidence}
                        )
                        contains_claim_relations_stored += 1
                    except Exception as e:
                        logger.warning(f"[Stage 6] 存储 CONTAINS_CLAIM 关系失败: {e}")
                    
                    # 创建 Claim → Chunk 的 EVIDENCE_FROM 关系
                    try:
                        self.graph_service.store_relationship(
                            rel_type="EVIDENCE_FROM",
                            source_id=claim.id,
                            target_id=claim.chunk_id,
                            rel_data={"evidence_span": claim.evidence_span}
                        )
                        evidence_from_relations_stored += 1
                    except Exception as e:
                        logger.warning(f"[Stage 6] 存储 EVIDENCE_FROM 关系失败: {e}")
                
                # 存储带证据的 Claim
                if claim.chunk_id:
                    self.graph_service.store_with_provenance(
                        node={"id": claim.id, "type": "Claim", "text": claim.text},
                        evidence_chunk_id=claim.chunk_id,
                        doc_id=claim.doc_id
                    )
                    
            except Exception as e:
                logger.warning(f"[Stage 6] 存储论断 {claim.id} 失败: {e}")
        
        # 4. 存储 Claim 之间的关系
        logger.info(f"[Stage 6] 开始存储 {len(relations)} 个 Claim 之间的关系")
        for relation in relations:
            try:
                self.graph_service.store_relation({
                    "source_id": relation.source_claim_id,
                    "target_id": relation.target_claim_id,
                    "type": relation.relation_type,
                    "confidence": relation.confidence,
                    "properties": {
                        "strength": relation.strength,
                        "evidence": relation.evidence
                    }
                })
                relations_stored += 1
                
            except Exception as e:
                logger.warning(f"[Stage 6] 存储关系失败: {e}")
        
        result.stage_metrics["stage6"] = {
            "chunks_stored": chunks_stored,
            "entities_stored": entities_stored,
            "claims_stored": claims_stored,
            "relations_stored": relations_stored,
            "mentions_relations_stored": mentions_relations_stored,
            "contains_claim_relations_stored": contains_claim_relations_stored,
            "contains_relations_stored": contains_relations_stored,
            "evidence_from_relations_stored": evidence_from_relations_stored,
            "belongs_to_theme_relations_stored": belongs_to_theme_relations_stored,
            "execution_time": time.time() - stage_start
        }
        
        logger.info(f"[Stage 6] 完成: chunks={chunks_stored}, entities={entities_stored}, "
                   f"claims={claims_stored}, relations={relations_stored}, "
                   f"mentions={mentions_relations_stored}, contains_claim={contains_claim_relations_stored}, "
                   f"contains={contains_relations_stored}, evidence_from={evidence_from_relations_stored}")
    
    async def _run_stage8(
        self,
        doc_id: str,
        result: PipelineResult
    ) -> None:
        """
        Stage 8: 度量服务
        """
        if not self.metrics_service or 8 not in self.config.stages_to_run:
            logger.info("[Stage 8] 跳过度量服务")
            return
        
        stage_start = time.time()
        logger.info(f"[Stage 8] 开始度量计算: doc_id={doc_id}")
        
        try:
            metrics = self.metrics_service.compute_metrics(doc_id)
            alerts = self.metrics_service.check_alerts(metrics)
            
            result.quality_metrics = metrics
            result.stage_metrics["stage8"] = {
                "metrics": metrics,
                "alerts": alerts,
                "execution_time": time.time() - stage_start
            }
            
            logger.info(f"[Stage 8] 完成: 孤立节点比例={metrics.get('isolated_node_ratio', 0):.2%}, "
                       f"平均度数={metrics.get('avg_degree', 0):.2f}")
            
            if alerts:
                logger.warning(f"[Stage 8] 质量告警: {alerts}")
                
        except Exception as e:
            logger.warning(f"[Stage 8] 度量计算失败: {e}")
            result.stage_metrics["stage8"] = {
                "error": str(e),
                "execution_time": time.time() - stage_start
            }
    
    async def _store_document(
        self,
        doc_id: str,
        document_meta: Optional[Dict[str, Any]],
        build_version: str
    ) -> None:
        """存储文档节点"""
        if not self.graph_service:
            return
        
        doc_data = {
            "id": doc_id,
            "doc_id": doc_id,  # 添加 doc_id 属性，确保与其他节点保持一致
            "title": document_meta.get("title", doc_id) if document_meta else doc_id,
            "source_type": document_meta.get("source_type", "unknown") if document_meta else "unknown",
            "url": document_meta.get("url") if document_meta else None,
            "author": document_meta.get("author") if document_meta else None
        }
        
        self.graph_service.store_entity("Document", doc_data)
        logger.debug(f"[Pipeline] 存储文档节点: {doc_id}")
    
    async def _generate_embeddings_batch(
        self,
        chunks: List[ChunkMetadata]
    ) -> List[ChunkMetadata]:
        """批量生成Chunk向量嵌入"""
        if not settings.enable_vector_search:
            return chunks
        
        logger.info(f"[Pipeline] 开始生成向量嵌入: {len(chunks)} 个Chunk")
        
        for chunk in chunks:
            try:
                if not chunk.embedding:
                    chunk.embedding = get_embedding(chunk.text, model=settings.embedding_model)
            except Exception as e:
                logger.warning(f"[Pipeline] 生成embedding失败: chunk={chunk.id}, error={e}")
        
        return chunks
    
    def _generate_entity_embeddings_batch(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量生成实体（Concept）向量嵌入
        
        Args:
            entities: 实体列表，每个实体包含 concept_name, description 等字段
        
        Returns:
            添加了embedding字段的实体列表
        """
        if not settings.enable_vector_search:
            return entities
        
        logger.info(f"[Pipeline] 开始生成实体向量嵌入: {len(entities)} 个实体")
        embedded_count = 0
        
        for entity in entities:
            try:
                if entity.get("embedding"):
                    continue  # 已有向量，跳过
                
                # 使用 name + description 构建向量输入文本
                name = entity.get("concept_name", "")
                description = entity.get("description", "")
                
                if name:
                    # 优先使用 name + description（如果有）
                    embedding_text = f"{name}. {description}" if description else name
                    entity["embedding"] = get_embedding(embedding_text, model=settings.embedding_model)
                    embedded_count += 1
                else:
                    logger.warning(f"[Pipeline] 实体缺少名称，跳过向量生成: {entity}")
                    
            except Exception as e:
                logger.warning(f"[Pipeline] 生成实体embedding失败: entity={entity.get('concept_name')}, error={e}")
        
        logger.info(f"[Pipeline] 实体向量嵌入生成完成: {embedded_count}/{len(entities)}")
        return entities
    
    def _generate_claim_embeddings_batch(
        self,
        claims: List[Any]
    ) -> List[Any]:
        """
        批量生成论断（Claim）向量嵌入
        
        Args:
            claims: Claim对象列表
        
        Returns:
            添加了embedding字段的Claim列表
        """
        if not settings.enable_vector_search:
            return claims
        
        logger.info(f"[Pipeline] 开始生成论断向量嵌入: {len(claims)} 个论断")
        embedded_count = 0
        
        for claim in claims:
            try:
                if hasattr(claim, 'embedding') and claim.embedding:
                    continue  # 已有向量，跳过
                
                # 使用 claim.text 构建向量输入
                text = getattr(claim, 'text', '')
                if text:
                    claim.embedding = get_embedding(text, model=settings.embedding_model)
                    embedded_count += 1
                    
            except Exception as e:
                logger.warning(f"[Pipeline] 生成论断embedding失败: claim_id={getattr(claim, 'id', 'unknown')}, error={e}")
        
        logger.info(f"[Pipeline] 论断向量嵌入生成完成: {embedded_count}/{len(claims)}")
        return claims
    
    async def process_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[PipelineResult]:
        """
        批量处理多个文档
        
        Args:
            documents: 文档列表，每个文档包含:
                - doc_id: 文档ID
                - parser_chunks: Parser预处理后的Chunk列表
                - document_meta: 文档元数据（可选）
                - raw_text: 原始文本（可选）
        
        Returns:
            PipelineResult列表
        """
        logger.info(f"[GraphRAGPipeline] 开始批量处理: {len(documents)} 个文档")
        
        semaphore = asyncio.Semaphore(self.config.concurrency_limit)
        
        async def process_with_semaphore(doc: Dict[str, Any]) -> PipelineResult:
            async with semaphore:
                return await self.process(
                    doc_id=doc["doc_id"],
                    parser_chunks=doc.get("parser_chunks", []),
                    document_meta=doc.get("document_meta"),
                    raw_text=doc.get("raw_text")
                )
        
        tasks = [process_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[GraphRAGPipeline] 文档 {documents[i]['doc_id']} 处理异常: {result}")
                final_results.append(PipelineResult(
                    doc_id=documents[i]["doc_id"],
                    build_version="",
                    success=False,
                    errors=[str(result)]
                ))
            else:
                final_results.append(result)
        
        logger.info(f"[GraphRAGPipeline] 批量处理完成: {len(final_results)} 个结果")
        return final_results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取流水线统计信息"""
        return self._stats.copy()
    
    def refresh_entity_linker_feedback(self):
        """刷新实体链接器的反馈数据"""
        if self.entity_linker:
            self.entity_linker.refresh_feedback_data()
            logger.info("[GraphRAGPipeline] 实体链接器反馈数据已刷新")


def create_pipeline(
    stages: Optional[List[int]] = None,
    enable_stage0: bool = False,
    enable_stage7: bool = False,
    enable_stage8: bool = True,
    concurrency_limit: int = 5,
    min_confidence: float = 0.6
) -> GraphRAGPipeline:
    """
    创建GraphRAG流水线的便捷函数
    
    Args:
        stages: 要运行的阶段列表，默认 [1,2,3,4,5,6,8]
        enable_stage0: 是否启用Stage 0（语义分块）
        enable_stage7: 是否启用Stage 7（查询服务）
        enable_stage8: 是否启用Stage 8（度量服务）
        concurrency_limit: 并发限制
        min_confidence: 最低置信度阈值
    
    Returns:
        GraphRAGPipeline实例
    """
    config = PipelineConfig(
        enable_stage0=enable_stage0,
        enable_stage7=enable_stage7,
        enable_stage8=enable_stage8,
        stages_to_run=stages or [1, 2, 3, 4, 5, 6, 8],
        concurrency_limit=concurrency_limit,
        min_confidence=min_confidence
    )
    
    return GraphRAGPipeline(config)


__all__ = [
    "GraphRAGPipeline",
    "PipelineConfig",
    "PipelineResult",
    "PipelineStage",
    "ChunkConverter",
    "create_pipeline"
]
