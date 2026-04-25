"""
阶段 7: GraphRAG 检索 (Query Service) - P1 实现

实现多路候选生成、图先验协同、限域生成
支持三种问答模式：llm_only, rag, graphrag
"""

import logging
from typing import Dict, Any, List, Literal, Optional, Set, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

from infra.neo4j_client import neo4j_client
from config import settings
from graphrag.utils.embedding import get_embedding, cosine_similarity
from graphrag.models.claim import Claim
from graphrag.models.theme import Theme

logger = logging.getLogger("graphrag.stage7")


@dataclass
class CandidateEvidence:
    """候选证据"""
    claim_id: str
    claim_text: str
    chunk_id: str
    doc_id: str
    section_path: Optional[str]
    evidence_span: Optional[Tuple[int, int]]
    score: float  # 综合分数
    source: str  # 来源：theme/vector/keyword/graph
    confidence: float
    claim_type: str
    modality: Optional[str] = None
    polarity: Optional[str] = None
    certainty: Optional[float] = None


@dataclass
class ConceptCandidate:
    """概念候选"""
    concept_id: str
    concept_name: str
    domain: Optional[str]
    score: float
    source: str  # 来源：theme/vector/keyword/graph


class QueryService:
    """
    GraphRAG 查询服务（P1 实现）
    
    实现多路候选生成 + 图先验协同 + 限域生成
    支持三种问答模式：
    - llm_only: 直接调用 LLM 回答
    - rag: 仅使用向量检索（Neo4j）
    - graphrag: 图遍历 + 向量检索 + LLM 生成
    """
    
    def __init__(self):
        logger.info("QueryService initialized (P1)")
        # 配置参数（从 settings 读取）
        self.max_hop = settings.graphrag_max_hop
        self.theme_weight = settings.graphrag_theme_weight
        self.vector_weight = settings.graphrag_vector_weight
        self.keyword_weight = settings.graphrag_keyword_weight
        self.graph_weight = settings.graphrag_graph_weight
        self.similarity_threshold = settings.vector_search_threshold
        
        logger.info("Using Neo4j vector index for similarity search")
        
    def answer(
        self,
        question: str,
        mode: Literal["llm_only", "rag", "graphrag", "local", "global", "hybrid"] = "graphrag",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        回答问题（P1 实现）
        
        Args:
            question: 用户问题
            mode: 查询模式: llm_only | rag | graphrag | local | global | hybrid
                  llm_only: 直接调用 LLM 回答
                  rag: 仅使用向量检索
                  graphrag/local/global/hybrid: GraphRAG 模式
            top_k: Top-K 结果数
        
        Returns:
            结构化答案 {conclusion, reasoning_chain, evidence, confidence}
        """
        logger.info(f"开始回答问题: question={question}, mode={mode}")
        
        # LLM Only 模式：直接返回通用回答
        if mode == "llm_only":
            answer = self._generate_llm_only_answer(question)
            result = {
                "answer": answer,
                "cited_evidence_ids": [],
                "relevant_themes": [],
                "mode": "llm_only"
            }
            logger.info(f"LLM Only 回答完成: confidence={answer['confidence']:.3f}")
            return result
        
        # RAG 模式：仅使用向量检索
        if mode == "rag":
            claim_candidates, _ = self._retrieve_by_vector(question, top_k * 3)
            final_candidates = claim_candidates[:top_k]
            answer = self._generate_answer(question, final_candidates)
            relevant_themes = []
            
            result = {
                "answer": answer,
                "cited_evidence_ids": [c.claim_id for c in final_candidates],
                "relevant_themes": relevant_themes,
                "mode": "rag"
            }
            logger.info(f"RAG 回答完成: confidence={answer['confidence']:.3f}, "
                       f"evidence_count={len(final_candidates)}")
            return result
        
        # GraphRAG 模式（兼容旧模式名）
        graph_mode = mode if mode in ["local", "global", "hybrid"] else "hybrid"
        
        # 1. 多路候选生成
        claim_candidates, concept_candidates = self._multi_path_candidate_generation(
            question, graph_mode, top_k * 3  # 召回更多候选以便后续融合
        )
        
        # 2. 图先验协同（扩展证据链）
        if graph_mode in ["local", "hybrid"]:
            claim_candidates = self._graph_prior_collaboration(
                claim_candidates, concept_candidates, max_hop=self.max_hop
            )
        
        # 3. 候选融合与重排序
        final_candidates = self._merge_and_rerank(claim_candidates, top_k)
        
        # 4. 限域生成（基于召回证据生成答案）
        answer = self._generate_answer(question, final_candidates)
        
        # 5. 提取相关主题
        relevant_themes = self._extract_relevant_themes(final_candidates)
        
        result = {
            "answer": answer,
            "cited_evidence_ids": [c.claim_id for c in final_candidates],
            "relevant_themes": relevant_themes,
            "mode": "graphrag"
        }
        
        logger.info(f"GraphRAG 回答完成: confidence={answer['confidence']:.3f}, "
                   f"evidence_count={len(final_candidates)}")
        return result
    
    def _generate_llm_only_answer(self, question: str) -> Dict[str, Any]:
        """
        LLM Only 模式：直接生成回答（模拟）
        
        在实际实现中，这里会调用真实的 LLM API
        """
        logger.info("Generating LLM-only answer")
        
        # 模拟 LLM 回答（实际实现中应调用真实 LLM）
        mock_answers = {
            "什么是软件测试？": "软件测试是一种评估软件系统或应用程序的过程，目的是发现其中的缺陷或错误，确保软件满足预期的功能和性能要求。",
            "什么是敏捷开发？": "敏捷开发是一种以人为核心、迭代、循序渐进的开发方法，强调快速响应变化和持续交付有价值的软件。",
            "什么是单元测试？": "单元测试是对软件中的最小可测试单元进行验证的过程，通常是对单个函数或方法的测试。"
        }
        
        conclusion = mock_answers.get(question, 
            f"这是一个关于「{question}」的问题。在实际系统中，此模式会直接调用 LLM 生成回答，不依赖知识库。")
        
        return {
            "conclusion": conclusion,
            "reasoning_chain": [],
            "confidence": 0.6,  # LLM 直接回答的置信度相对较低
            "caveats": "此回答基于 LLM 预训练知识，可能存在幻觉风险"
        }
    
    def _multi_path_candidate_generation(
        self,
        question: str,
        mode: Literal["local", "global", "hybrid"],
        recall_limit: int
    ) -> Tuple[List[CandidateEvidence], List[ConceptCandidate]]:
        """
        多路候选生成（P1 核心功能）
        
        1. 主题匹配召回（Theme-based）
        2. 向量检索（Vector Search）
        3. 关键词匹配（Keyword/BM25）
        4. 图遍历（Graph Traversal，仅 local/hybrid）
        
        Args:
            question: 用户问题
            mode: 查询模式
            recall_limit: 每路召回数量限制
        
        Returns:
            (claim_candidates, concept_candidates)
        """
        logger.info(f"[Stage7] 多路候选生成: mode={mode}, recall_limit={recall_limit}")
        
        claim_candidates: List[CandidateEvidence] = []
        concept_candidates: List[ConceptCandidate] = []
        seen_claim_ids: Set[str] = set()
        seen_concept_ids: Set[str] = set()
        
        # 1. 主题匹配召回（Global/Hybrid 模式）
        if mode in ["global", "hybrid"]:
            logger.debug(f"[Stage7] 开始主题匹配召回...")
            theme_claims, theme_concepts = self._retrieve_by_theme(question, recall_limit)
            logger.debug(f"[Stage7] 主题匹配返回: {len(theme_claims)} claims, {len(theme_concepts)} concepts")
            for claim in theme_claims:
                if claim.claim_id not in seen_claim_ids:
                    claim_candidates.append(claim)
                    seen_claim_ids.add(claim.claim_id)
            for concept in theme_concepts:
                if concept.concept_id not in seen_concept_ids:
                    concept_candidates.append(concept)
                    seen_concept_ids.add(concept.concept_id)
            logger.info(f"主题匹配召回: {len(theme_claims)} claims, {len(theme_concepts)} concepts")
        
        # 2. 向量检索
        logger.debug(f"[Stage7] 开始向量检索...")
        vector_claims, vector_concepts = self._retrieve_by_vector(question, recall_limit)
        logger.debug(f"[Stage7] 向量检索返回: {len(vector_claims)} claims, {len(vector_concepts)} concepts")
        for claim in vector_claims:
            if claim.claim_id not in seen_claim_ids:
                claim_candidates.append(claim)
                seen_claim_ids.add(claim.claim_id)
        for concept in vector_concepts:
            if concept.concept_id not in seen_concept_ids:
                concept_candidates.append(concept)
                seen_concept_ids.add(concept.concept_id)
        logger.info(f"向量检索召回: {len(vector_claims)} claims, {len(vector_concepts)} concepts")
        
        # 3. 关键词匹配（BM25 风格）
        logger.debug(f"[Stage7] 开始关键词匹配...")
        keyword_claims, keyword_concepts = self._retrieve_by_keyword(question, recall_limit)
        logger.debug(f"[Stage7] 关键词匹配返回: {len(keyword_claims)} claims, {len(keyword_concepts)} concepts")
        for claim in keyword_claims:
            if claim.claim_id not in seen_claim_ids:
                claim_candidates.append(claim)
                seen_claim_ids.add(claim.claim_id)
        for concept in keyword_concepts:
            if concept.concept_id not in seen_concept_ids:
                concept_candidates.append(concept)
                seen_concept_ids.add(concept.concept_id)
        logger.info(f"关键词匹配召回: {len(keyword_claims)} claims, {len(keyword_concepts)} concepts")
        
        # 4. 图遍历（Local/Hybrid 模式）
        if mode in ["local", "hybrid"]:
            logger.debug(f"[Stage7] 开始图遍历...")
            graph_claims, graph_concepts = self._retrieve_by_graph_traversal(
                question, concept_candidates, recall_limit
            )
            logger.debug(f"[Stage7] 图遍历返回: {len(graph_claims)} claims, {len(graph_concepts)} concepts")
            for claim in graph_claims:
                if claim.claim_id not in seen_claim_ids:
                    claim_candidates.append(claim)
                    seen_claim_ids.add(claim.claim_id)
            for concept in graph_concepts:
                if concept.concept_id not in seen_concept_ids:
                    concept_candidates.append(concept)
                    seen_concept_ids.add(concept.concept_id)
            logger.info(f"图遍历召回: {len(graph_claims)} claims, {len(graph_concepts)} concepts")
        
        logger.info(f"多路候选生成完成: 总计 {len(claim_candidates)} claims, "
                   f"{len(concept_candidates)} concepts")
        
        return claim_candidates, concept_candidates
    
    def _retrieve_by_theme(
        self, question: str, limit: int
    ) -> Tuple[List[CandidateEvidence], List[ConceptCandidate]]:
        """主题匹配召回"""
        claims = []
        concepts = []
        
        # 查询相关主题（基于关键词匹配）
        query = """
        MATCH (t:Theme)
        WHERE t.label CONTAINS $keyword 
           OR t.summary CONTAINS $keyword
           OR any(kw IN t.keywords WHERE kw CONTAINS $keyword)
        RETURN t
        ORDER BY t.member_count DESC
        LIMIT 5
        """
        
        # 提取问题关键词（简单实现：取前3个词）
        keywords = question.split()[:3]
        theme_results = []
        for keyword in keywords:
            results = neo4j_client.execute_query(query, {"keyword": keyword})
            theme_results.extend(results)
        
        # 去重
        seen_theme_ids = set()
        for record in theme_results:
            theme = record.get("t", {})
            theme_id = theme.get("id")
            if not theme_id or theme_id in seen_theme_ids:
                continue
            seen_theme_ids.add(theme_id)
            
            # 查询该主题下的 Claim（支持两种关系类型：BELONGS_TO_THEME 或 HAS_MEMBER）
            claim_query = """
            MATCH (t:Theme {id: $theme_id})
            OPTIONAL MATCH (cl:Claim)-[:BELONGS_TO_THEME]->(t)
            WITH t, collect(DISTINCT cl) AS claims1
            OPTIONAL MATCH (t)-[:HAS_MEMBER]->(cl2:Claim)
            WITH claims1 + collect(DISTINCT cl2) AS all_claims
            UNWIND all_claims AS cl
            WHERE cl IS NOT NULL
            RETURN DISTINCT cl
            LIMIT $limit
            """
            claim_results = neo4j_client.execute_query(claim_query, {
                "theme_id": theme_id,
                "limit": limit // len(seen_theme_ids) if seen_theme_ids else limit
            })
            
            for claim_record in claim_results:
                cl = claim_record.get("cl", {})
                if not cl:
                    continue
                claim = self._claim_to_candidate(cl, source="theme", base_score=0.8)
                claims.append(claim)
            
            # 查询该主题下的 Concept（支持两种关系类型：BELONGS_TO_THEME 或 HAS_MEMBER）
            concept_query = """
            MATCH (t:Theme {id: $theme_id})
            OPTIONAL MATCH (c:Concept)-[:BELONGS_TO_THEME]->(t)
            WITH t, collect(DISTINCT c) AS concepts1
            OPTIONAL MATCH (t)-[:HAS_MEMBER]->(c2:Concept)
            WITH concepts1 + collect(DISTINCT c2) AS all_concepts
            UNWIND all_concepts AS c
            WHERE c IS NOT NULL
            RETURN DISTINCT c
            LIMIT $limit
            """
            concept_results = neo4j_client.execute_query(concept_query, {
                "theme_id": theme_id,
                "limit": limit // len(seen_theme_ids) if seen_theme_ids else limit
            })
            
            for concept_record in concept_results:
                c = concept_record.get("c", {})
                concept_name = c.get("name", "")
                if not concept_name:
                    continue
                concept = ConceptCandidate(
                    concept_id=concept_name,  # Concept 使用 name 作为 ID
                    concept_name=concept_name,
                    domain=c.get("domain"),
                    score=0.8,
                    source="theme"
                )
                concepts.append(concept)
        
        return claims[:limit], concepts[:limit]
    
    def _retrieve_by_vector(
        self, question: str, limit: int
    ) -> Tuple[List[CandidateEvidence], List[ConceptCandidate]]:
        """向量检索（使用 Neo4j 向量索引）"""
        claims = []
        concepts = []
        
        # 获取问题向量
        question_embedding = get_embedding(question)
        if not question_embedding or len(question_embedding) != settings.embedding_dimension:
            logger.warning("无法获取问题向量，跳过向量检索")
            return claims, concepts
        
        # 1. Claim 向量检索
        claim_query = """
        CALL db.index.vector.queryNodes('claim_embeddings', $topK, $queryVector)
        YIELD node, score
        WHERE node.embedding IS NOT NULL AND score >= $threshold AND coalesce(node.confidence, 0.5) >= $confidenceThreshold
        RETURN node, score
        """
        
        top_k = limit * 2  # 召回更多以便后续过滤
        claim_results = neo4j_client.execute_query(claim_query, {
            "topK": top_k,
            "queryVector": question_embedding,
            "threshold": self.similarity_threshold,
            "confidenceThreshold": 0.5
        })
        
        for record in claim_results:
            node = record.get("node", {})
            score = record.get("score", 0.0)
            claim = self._claim_to_candidate(node, source="vector", base_score=float(score))
            claims.append(claim)
        
        # 2. Concept 向量检索
        concept_query = """
        CALL db.index.vector.queryNodes('concept_embeddings', $topK, $queryVector)
        YIELD node, score
        WHERE node.embedding IS NOT NULL AND score >= $threshold
        RETURN node, score
        """
        
        concept_results = neo4j_client.execute_query(concept_query, {
            "topK": top_k,
            "queryVector": question_embedding,
            "threshold": self.similarity_threshold
        })
        
        for record in concept_results:
            node = record.get("node", {})
            score = record.get("score", 0.0)
            concept_name = node.get("name", "")
            if not concept_name:
                continue
            concept = ConceptCandidate(
                concept_id=concept_name,  # Concept 使用 name 作为 ID
                concept_name=concept_name,
                domain=node.get("domain"),
                score=float(score),
                source="vector"
            )
            concepts.append(concept)
        
        logger.info(f"Neo4j向量检索完成: {len(claims)} claims, {len(concepts)} concepts")
        return claims[:limit], concepts[:limit]
    
    def _retrieve_by_keyword(
        self, question: str, limit: int
    ) -> Tuple[List[CandidateEvidence], List[ConceptCandidate]]:
        """关键词匹配（BM25 风格）"""
        claims = []
        concepts = []
        
        # 提取关键词（简单实现：去除停用词）
        keywords = [w for w in question.split() if len(w) > 2]
        if not keywords:
            return claims, concepts
        
        # 构建查询条件
        keyword_conditions = " OR ".join([f"cl.text CONTAINS '{kw}'" for kw in keywords])
        
        # 1. Claim 关键词匹配
        claim_query = f"""
        MATCH (cl:Claim)
        WHERE {keyword_conditions}
        RETURN cl
        ORDER BY cl.confidence DESC
        LIMIT $limit
        """
        
        claim_results = neo4j_client.execute_query(claim_query, {"limit": limit})
        
        for record in claim_results:
            cl = record.get("cl", {})
            # 计算关键词匹配分数（简单实现：匹配词数 / 总词数）
            text = cl.get("text", "")
            match_count = sum(1 for kw in keywords if kw.lower() in text.lower())
            keyword_score = match_count / len(keywords) if keywords else 0.0
            
            claim = self._claim_to_candidate(cl, source="keyword", base_score=keyword_score)
            claims.append(claim)
        
        # 2. Concept 关键词匹配
        concept_conditions = " OR ".join([f"c.name CONTAINS '{kw}'" for kw in keywords])
        concept_query = f"""
        MATCH (c:Concept)
        WHERE {concept_conditions}
        RETURN c
        LIMIT $limit
        """
        
        concept_results = neo4j_client.execute_query(concept_query, {"limit": limit})
        
        for record in concept_results:
            c = record.get("c", {})
            name = c.get("name", "")
            if not name:
                continue
            match_count = sum(1 for kw in keywords if kw.lower() in name.lower())
            keyword_score = match_count / len(keywords) if keywords else 0.0
            
            concept = ConceptCandidate(
                concept_id=name,  # Concept 使用 name 作为 ID
                concept_name=name,
                domain=c.get("domain"),
                score=keyword_score,
                source="keyword"
            )
            concepts.append(concept)
        
        return claims[:limit], concepts[:limit]
    
    def _retrieve_by_graph_traversal(
        self,
        question: str,
        seed_concepts: List[ConceptCandidate],
        limit: int
    ) -> Tuple[List[CandidateEvidence], List[ConceptCandidate]]:
        """图遍历（K-hop）"""
        claims = []
        concepts = []
        
        if not seed_concepts:
            return claims, concepts
        
        # 从种子概念开始，进行 K-hop 遍历
        seed_names = [c.concept_id for c in seed_concepts[:5]]  # 取前5个种子（Concept 使用 name 作为 ID）
        
        # K-hop 查询：找到与种子概念相关的 Claim
        graph_query = """
        MATCH (c:Concept)
        WHERE c.name IN $seed_names
        MATCH path = (c)-[*1..2]-(cl:Claim)
        WHERE all(r IN relationships(path) WHERE type(r) IN ['MENTIONS', 'SUPPORTS', 'CAUSES', 'CONTRADICTS'])
        RETURN DISTINCT cl, length(path) AS hop
        ORDER BY hop ASC, cl.confidence DESC
        LIMIT $limit
        """
        
        claim_results = neo4j_client.execute_query(graph_query, {
            "seed_names": seed_names,
            "limit": limit
        })
        
        for record in claim_results:
            cl = record.get("cl", {})
            hop = record.get("hop", 2)
            # 跳数越少，分数越高
            graph_score = 1.0 / hop if hop > 0 else 1.0
            
            claim = self._claim_to_candidate(cl, source="graph", base_score=graph_score)
            claims.append(claim)
        
        # K-hop 查询：找到与种子概念相关的其他 Concept
        concept_query = """
        MATCH (c1:Concept)
        WHERE c1.name IN $seed_names
        MATCH path = (c1)-[*1..2]-(c2:Concept)
        WHERE c2.name <> c1.name
        RETURN DISTINCT c2, length(path) AS hop
        ORDER BY hop ASC
        LIMIT $limit
        """
        
        concept_results = neo4j_client.execute_query(concept_query, {
            "seed_names": seed_names,
            "limit": limit
        })
        
        for record in concept_results:
            c = record.get("c2", {})
            hop = record.get("hop", 2)
            graph_score = 1.0 / hop if hop > 0 else 1.0
            concept_name = c.get("name", "")
            if not concept_name:
                continue
            
            concept = ConceptCandidate(
                concept_id=concept_name,  # Concept 使用 name 作为 ID
                concept_name=concept_name,
                domain=c.get("domain"),
                score=graph_score,
                source="graph"
            )
            concepts.append(concept)
        
        return claims[:limit], concepts[:limit]
    
    def _graph_prior_collaboration(
        self,
        claim_candidates: List[CandidateEvidence],
        concept_candidates: List[ConceptCandidate],
        max_hop: int = 2
    ) -> List[CandidateEvidence]:
        """
        图先验协同：基于知识图谱结构扩展证据链
        
        1. 沿着 SUPPORTS/CAUSES 关系扩展
        2. 基于社区聚合（如果可用）
        3. 证据链评分
        """
        logger.info(f"图先验协同: 输入 {len(claim_candidates)} claims, max_hop={max_hop}")
        
        expanded_claims = list(claim_candidates)  # 保留原始候选
        seen_claim_ids = {c.claim_id for c in claim_candidates}
        
        # 获取种子 Claim ID
        seed_claim_ids = [c.claim_id for c in claim_candidates[:10]]  # 取前10个作为种子
        
        # 沿着关系扩展
        expansion_query = """
        MATCH (cl1:Claim)
        WHERE cl1.id IN $seed_ids
        MATCH path = (cl1)-[r:SUPPORTS|CAUSES*1..2]-(cl2:Claim)
        WHERE cl2.id <> cl1.id
        RETURN DISTINCT cl2, length(path) AS hop,
               [r IN relationships(path) | type(r)] AS rel_types
        ORDER BY hop ASC, cl2.confidence DESC
        LIMIT 20
        """
        
        expansion_results = neo4j_client.execute_query(expansion_query, {
            "seed_ids": seed_claim_ids
        })
        
        for record in expansion_results:
            cl = record.get("cl2", {})
            claim_id = cl.get("id")
            if not claim_id or claim_id in seen_claim_ids:
                continue
            
            hop = record.get("hop", 2)
            rel_types = record.get("rel_types", [])
            
            # 计算扩展分数（跳数越少，关系越强，分数越高）
            expansion_score = 1.0 / hop if hop > 0 else 1.0
            # SUPPORTS 关系权重更高
            if "SUPPORTS" in rel_types:
                expansion_score *= 1.2
            
            claim = self._claim_to_candidate(
                cl,
                source="graph_expansion",
                base_score=expansion_score * 0.7  # 扩展证据分数略低
            )
            expanded_claims.append(claim)
            seen_claim_ids.add(claim_id)
        
        logger.info(f"图先验协同完成: 扩展后 {len(expanded_claims)} claims")
        return expanded_claims
    
    def _merge_and_rerank(
        self,
        claim_candidates: List[CandidateEvidence],
        top_k: int
    ) -> List[CandidateEvidence]:
        """
        候选融合与重排序
        
        根据来源加权融合分数，然后重排序
        """
        # 按来源分组
        by_source = defaultdict(list)
        for claim in claim_candidates:
            by_source[claim.source].append(claim)
        
        # 加权融合
        source_weights = {
            "theme": self.theme_weight,
            "vector": self.vector_weight,
            "keyword": self.keyword_weight,
            "graph": self.graph_weight,
            "graph_expansion": self.graph_weight * 0.8  # 扩展证据权重略低
        }
        
        # 计算综合分数
        for claim in claim_candidates:
            weight = source_weights.get(claim.source, 0.1)
            # 综合分数 = 来源分数 * 来源权重 + 置信度 * 0.3
            claim.score = claim.score * weight + claim.confidence * 0.3
        
        # 按综合分数排序
        claim_candidates.sort(key=lambda x: x.score, reverse=True)
        
        # 过滤掉综合分数过低的候选
        min_candidate_score = 0.3
        claim_candidates = [c for c in claim_candidates if c.score >= min_candidate_score]
        
        # 返回 Top-K
        return claim_candidates[:top_k]
    
    def _generate_answer(
        self,
        question: str,
        evidence_candidates: List[CandidateEvidence]
    ) -> Dict[str, Any]:
        """
        限域生成：基于召回证据生成答案
        
        简化实现：直接拼接证据文本，实际应该调用 LLM
        """
        if not evidence_candidates:
            return {
                "conclusion": "抱歉，未找到相关证据。",
                "reasoning_chain": [],
                "confidence": 0.0,
                "caveats": "未找到相关证据"
            }
        
        # 构建推理链
        reasoning_chain = []
        for i, evidence in enumerate(evidence_candidates[:5], 1):  # 最多5条证据
            reasoning_chain.append({
                "step": i,
                "statement": evidence.claim_text,
                "evidence_ids": [evidence.claim_id],
                "confidence": evidence.confidence,
                "source": evidence.source
            })
        
        # 生成结论（简化实现：取第一条证据的文本）
        conclusion = evidence_candidates[0].claim_text
        
        # 计算平均置信度
        avg_confidence = sum(c.confidence for c in evidence_candidates) / len(evidence_candidates)
        
        # 检查是否有低置信度证据
        caveats = None
        low_confidence_count = sum(1 for c in evidence_candidates if c.confidence < 0.7)
        if low_confidence_count > 0:
            caveats = f"部分证据置信度较低（{low_confidence_count} 条）"
        
        return {
            "conclusion": conclusion,
            "reasoning_chain": reasoning_chain,
            "confidence": avg_confidence,
            "caveats": caveats
        }
    
    def _extract_relevant_themes(
        self, evidence_candidates: List[CandidateEvidence]
    ) -> List[str]:
        """提取相关主题"""
        if not evidence_candidates:
            return []
        
        # 查询证据相关的主题
        claim_ids = [c.claim_id for c in evidence_candidates[:10]]
        
        # 提取相关主题（支持两种关系类型：BELONGS_TO_THEME 或 HAS_MEMBER）
        theme_query = """
        MATCH (cl:Claim)
        WHERE cl.id IN $claim_ids
        OPTIONAL MATCH (cl)-[:BELONGS_TO_THEME]->(t1:Theme)
        WITH cl, collect(DISTINCT t1) AS themes1
        OPTIONAL MATCH (t2:Theme)-[:HAS_MEMBER]->(cl)
        WITH themes1 + collect(DISTINCT t2) AS all_themes
        UNWIND all_themes AS t
        WHERE t IS NOT NULL
        RETURN DISTINCT t.label AS theme_label
        LIMIT 5
        """
        
        results = neo4j_client.execute_query(theme_query, {"claim_ids": claim_ids})
        return [r.get("theme_label", "") for r in results if r.get("theme_label")]
    
    def _claim_to_candidate(
        self,
        claim_node: Dict[str, Any],
        source: str,
        base_score: float
    ) -> CandidateEvidence:
        """将 Neo4j Claim 节点转换为 CandidateEvidence"""
        evidence_span = None
        if claim_node.get("evidence_span"):
            span = claim_node["evidence_span"]
            if isinstance(span, list) and len(span) == 2:
                evidence_span = tuple(span)
        
        return CandidateEvidence(
            claim_id=claim_node.get("id", ""),
            claim_text=claim_node.get("text", ""),
            chunk_id=claim_node.get("chunk_id", ""),
            doc_id=claim_node.get("doc_id", ""),
            section_path=claim_node.get("section_path"),
            evidence_span=evidence_span,
            score=base_score,
            source=source,
            confidence=claim_node.get("confidence", 0.5),
            claim_type=claim_node.get("claim_type", "fact"),
            modality=claim_node.get("modality"),
            polarity=claim_node.get("polarity"),
            certainty=claim_node.get("certainty")
        )


__all__ = ["QueryService"]
