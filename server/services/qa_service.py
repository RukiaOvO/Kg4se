"""Intelligent Q&A service using Neo4j knowledge graph and AI providers."""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator
from infra.ai_providers import AIProviderFactory
from infra.neo4j_client import neo4j_client
from services.config_service import config_service
from utils.logger import get_logger

logger = get_logger("services.qa_service")


class QAService:
    """Service for intelligent Q&A using Neo4j knowledge graph."""
    
    def __init__(self):
        self.ai_client = self._initialize_ai_client()
        self.judge_client = self._initialize_judge_client()
        self.context_limit = 4000  # 字符限制，增加到4000以嵌入更多信息
    
    def chat(self, prompt: str, temperature: float = None) -> str:
        """通用聊天接口，供 PointwiseEvaluator 等评估器调用（使用独立的 JUDGE_MODEL）"""
        t = temperature if temperature is not None else 0.3
        system_msg = "You are a helpful assistant. Please respond in JSON format."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
        logger.info(f"[QA服务 chat] 调用 judge_model，温度: {t}")
        return self.judge_client.chat_completion(messages=messages, temperature=t, json_mode=True)
    
    def _query_vector_store(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query vector store for similar documents using Neo4j vector index."""
        try:
            from config import settings
            from graphrag.utils.embedding import get_embedding
            
            query_embedding = get_embedding(question)
            similarity_threshold = settings.vector_search_threshold
            
            if not query_embedding or all(v == 0.0 for v in query_embedding):
                logger.debug("[QA服务] 向量化失败，使用关键词匹配")
                return self._keyword_fallback(question, top_k)
            
            all_results = []
            
            # 1. 查询 Claim 向量索引（优先，包含实际论断内容）
            try:
                claim_query = """
                    CALL db.index.vector.queryNodes('claim_embeddings', $topK, $queryVector)
                    YIELD node, score
                    WHERE node.embedding IS NOT NULL AND node.text IS NOT NULL AND score >= $threshold
                    RETURN 
                        node.text AS text, 
                        'Claim:' + node.id AS source, 
                        score AS similarity,
                        node.claim_type AS type
                    ORDER BY score DESC
                    LIMIT $topK
                """
                claim_params = {
                    "topK": top_k,
                    "queryVector": query_embedding,
                    "threshold": similarity_threshold
                }
                claim_results = neo4j_client.execute_query(claim_query, claim_params)
                for record in claim_results:
                    text = record.get("text", "")
                    if text and text.strip() and len(text.strip()) > 20:  # 过滤过短内容
                        all_results.append({
                            "text": text,
                            "source": record.get("source", ""),
                            "similarity": record.get("similarity", 0.0),
                            "type": record.get("type", "claim")
                        })
                logger.debug(f"[QA服务] Claim向量检索返回 {len(claim_results)} 条结果")
            except Exception as e:
                logger.debug(f"[QA服务] Claim向量索引查询失败: {e}")
            
            # 2. 查询 Chunk 向量索引（包含文档片段内容）
            try:
                chunk_query = """
                    CALL db.index.vector.queryNodes('chunk_embeddings', $topK, $queryVector)
                    YIELD node, score
                    WHERE node.embedding IS NOT NULL AND node.text IS NOT NULL AND score >= $threshold
                    RETURN 
                        node.text AS text, 
                        'Chunk:' + coalesce(node.section_path, node.id) AS source, 
                        score AS similarity,
                        'chunk' AS type
                    ORDER BY score DESC
                    LIMIT $topK
                """
                chunk_params = {
                    "topK": top_k,
                    "queryVector": query_embedding,
                    "threshold": similarity_threshold
                }
                chunk_results = neo4j_client.execute_query(chunk_query, chunk_params)
                for record in chunk_results:
                    text = record.get("text", "")
                    if text and text.strip() and len(text.strip()) > 50:  # 过滤过短内容
                        all_results.append({
                            "text": text,
                            "source": record.get("source", ""),
                            "similarity": record.get("similarity", 0.0),
                            "type": record.get("type", "chunk")
                        })
                logger.debug(f"[QA服务] Chunk向量检索返回 {len(chunk_results)} 条结果")
            except Exception as e:
                logger.debug(f"[QA服务] Chunk向量索引查询失败: {e}")
            
            # 3. 查询 Concept 向量索引（作为补充，只返回有description/concept_content的）
            try:
                concept_query = """
                    CALL db.index.vector.queryNodes('concept_embeddings', $topK, $queryVector)
                    YIELD node, score
                    WHERE node.embedding IS NOT NULL AND score >= $threshold
                    RETURN 
                        node.name AS name,
                        node.description AS description,
                        node.definition AS definition,
                        score AS similarity
                    ORDER BY score DESC
                    LIMIT $topK
                """
                concept_params = {
                    "topK": top_k,
                    "queryVector": query_embedding,
                    "threshold": similarity_threshold
                }
                concept_results = neo4j_client.execute_query(concept_query, concept_params)
                for record in concept_results:
                    name = record.get("name", "")
                    description = record.get("description", "")
                    definition = record.get("definition", "")
                    
                    # 优先使用description，其次definition，都不存在则跳过此Concept
                    if description and description.strip():
                        text = description.strip()
                    elif definition and definition.strip():
                        text = definition.strip()
                    else:
                        # Concept没有description/definition，查询其关联的Claim/Chunk作为补充
                        logger.debug(f"[QA服务] Concept '{name}' 无description，尝试查询关联内容")
                        text = self._get_concept_content(name)
                    
                    if text and text.strip() and len(text.strip()) > 20:  # 过滤过短内容
                        all_results.append({
                            "text": text,
                            "source": f"Concept:{name}",
                            "similarity": record.get("similarity", 0.0),
                            "type": "concept"
                        })
                logger.debug(f"[QA服务] Concept向量检索返回 {len(concept_results)} 条结果")
            except Exception as e:
                logger.debug(f"[QA服务] Concept向量索引查询失败: {e}")
            
            # 4. 去重并按相似度排序
            seen_texts = set()
            unique_results = []
            for result in all_results:
                # 使用前100字符作为去重key
                text_key = result["text"][:100].strip()
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_results.append(result)
            
            # 按相似度降序排序，返回 top_k
            unique_results.sort(key=lambda x: x["similarity"], reverse=True)
            final_results = unique_results[:top_k]
            
            logger.info(f"[QA服务] 向量检索: 原始{len(all_results)}条 → 阈值{similarity_threshold}过滤后{len(unique_results)}条 → 取top_{top_k}返回{len(final_results)}条")
            
            # 打印实际返回的内容用于调试
            for i, r in enumerate(final_results[:3]):
                logger.debug(f"[QA服务] 结果{i+1}: type={r['type']}, similarity={r['similarity']:.4f}, text_len={len(r['text'])}, text_preview={r['text'][:80]}...")
            
            if final_results:
                return final_results
            
            # 回退到关键词匹配
            return self._keyword_fallback(question, top_k)
            
        except Exception as e:
            logger.error(f"[QA服务] 向量数据库查询失败: {e}")
            return []
    
    def _get_concept_content(self, concept_name: str) -> str:
        """当Concept没有description时，查询其关联的Claim或Chunk作为内容"""
        try:
            # 查询Concept关联的Claim（优先）
            claim_query = """
                MATCH (c:Concept {name: $name})<-[:MENTIONS]-(:Chunk)-[:CONTAINS_CLAIM]->(cl:Claim)
                RETURN cl.text AS text, cl.confidence AS confidence
                ORDER BY cl.confidence DESC
                LIMIT 3
            """
            claim_results = neo4j_client.execute_query(claim_query, {"name": concept_name})
            
            if claim_results:
                claims = []
                for record in claim_results:
                    text = record.get("text", "")
                    if text and text.strip():
                        claims.append(text.strip())
                if claims:
                    content = "\n\n".join(claims)
                    logger.debug(f"[QA服务] 从Concept关联Claim获取内容: {len(content)} 字符")
                    return content
            
            # 查询Concept关联的Chunk
            chunk_query = """
                MATCH (c:Concept {name: $name})<-[:MENTIONS]-(ch:Chunk)
                RETURN ch.text AS text
                LIMIT 2
            """
            chunk_results = neo4j_client.execute_query(chunk_query, {"name": concept_name})
            
            if chunk_results:
                chunks = []
                for record in chunk_results:
                    text = record.get("text", "")
                    if text and text.strip() and len(text.strip()) > 50:
                        chunks.append(text.strip())
                if chunks:
                    content = "\n\n".join(chunks)
                    logger.debug(f"[QA服务] 从Concept关联Chunk获取内容: {len(content)} 字符")
                    return content
            
            # 如果都没有，返回name（但不推荐，因为信息太少）
            logger.debug(f"[QA服务] Concept '{concept_name}' 无关联内容")
            return ""
            
        except Exception as e:
            logger.debug(f"[QA服务] 查询Concept关联内容失败: {e}")
            return ""
    
    def _keyword_fallback(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """基于关键词的fallback检索方法"""
        keywords = self._extract_keywords(question)
        
        if not keywords:
            logger.debug("[QA服务] 无可用关键词，跳过fallback查询")
            return []
        
        # 基于关键词匹配 name, description, aliases
        fallback_query = """
            MATCH (n:Concept)
            WHERE n.description IS NOT NULL AND n.description <> ''
            AND (
                ANY(keyword IN $keywords WHERE toLower(n.name) CONTAINS toLower(keyword))
                OR ANY(keyword IN $keywords WHERE toLower(n.description) CONTAINS toLower(keyword))
                OR ANY(keyword IN $keywords WHERE 
                    ANY(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower(keyword))
                )
            )
            RETURN n.description AS text, n.name AS source, 0.5 AS similarity
            LIMIT $topK
        """
        fallback_params = {"topK": top_k, "keywords": keywords}
        
        fallback_results = neo4j_client.execute_query(fallback_query, fallback_params)
        
        contexts = []
        for record in fallback_results:
            text = record.get("text", "")
            if text and text.strip():
                contexts.append({
                    "text": text,
                    "source": record.get("source", ""),
                    "similarity": record.get("similarity", 0.0)
                })
        
        logger.debug(f"[QA服务] Neo4j关键词检索返回 {len(contexts)} 条结果")
        return contexts
    
    def _initialize_ai_client(self):
        """Initialize AI client with configured provider."""
        try:
            ai_config = config_service.get_ai_provider_config()
            client = AIProviderFactory.create_client(
                provider=ai_config["provider"],
                api_key=ai_config["api_key"],
                model=ai_config["model"],
                base_url=ai_config["base_url"]
            )
            logger.info(f"[QA服务] AI客户端初始化成功: {ai_config['provider']}")
            return client
        except Exception as e:
            logger.error(f"[QA服务] AI客户端初始化失败: {e}")
            return None
    
    def _initialize_judge_client(self):
        """Initialize judge/evaluation AI client with JUDGE_MODEL config."""
        try:
            judge_config = config_service.get_judge_provider_config()
            client = AIProviderFactory.create_client(
                provider=judge_config["provider"],
                api_key=judge_config["api_key"],
                model=judge_config["model"],
                base_url=judge_config["base_url"]
            )
            logger.info(f"[QA服务] Judge客户端初始化成功: {judge_config['provider']}/{judge_config['model']}")
            return client
        except Exception as e:
            logger.error(f"[QA服务] Judge客户端初始化失败，回退到AI客户端: {e}")
            return self.ai_client
    
    def query_knowledge_graph(self, question: str, limit: int = 8) -> Dict[str, Any]:
        """
        Query knowledge graph to find relevant entities and relationships.
        
        Args:
            question: User's question
            limit: Maximum number of relevant nodes to retrieve
            
        Returns:
            Dictionary containing relevant knowledge graph data
        """
        try:
            keywords = self._extract_keywords(question)
            
            logger.debug(f"[QA服务] 提取的关键词: {keywords}")
            
            if not keywords:
                logger.debug("[QA服务] 未提取到关键词，返回空结果")
                return {"entities": [], "relationships": []}
            
            cypher = """
            MATCH (n:Concept)
            WHERE ANY(keyword IN $keywords WHERE toLower(n.name) CONTAINS toLower(keyword) 
                   OR ANY(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower(keyword)))
            WITH n LIMIT $limit
            OPTIONAL MATCH (n)-[r]-(related)
            WITH n, collect(DISTINCT {
                type: type(r),
                target_name: coalesce(related.name, related.label, related.id, 'Unknown'),
                target_type: coalesce(related.type, labels(related)[0], 'Unknown')
            }) AS rels
            OPTIONAL MATCH (n)<-[mc:MENTIONS]-(c:Claim)
            WITH n, rels, collect(DISTINCT {
                claim_text: c.text,
                claim_type: c.claim_type,
                confidence: c.confidence,
                modality: c.modality,
                polarity: c.polarity
            }) AS all_claims
            WITH n, rels, all_claims
            UNWIND all_claims AS claim
            WITH n, rels, claim
            ORDER BY n.name, claim.confidence DESC
            WITH n, rels, collect(claim)[0..3] AS top_claims
            RETURN {
                entity: {
                    id: elementId(n),
                    name: n.name,
                    type: n.type,
                    definition: n.definition,
                    description: n.description,
                    domain: n.domain,
                    category: n.category,
                    importance: n.importance,
                    aliases: n.aliases
                },
                relationships: rels,
                claims: top_claims
            } AS result
            """
            
            results = neo4j_client.execute_query(
                cypher,
                parameters={
                    "keywords": keywords,
                    "limit": limit
                }
            )
            
            logger.debug(f"[QA服务] Neo4j查询结果数量: {len(results) if results else 0}")
            
            # 打印前2个结果的实际格式
            if results and len(results) > 0:
                import json
                logger.debug(f"[QA服务] 第一个查询结果格式: {type(results[0])}")
                logger.debug(f"[QA服务] 第一个查询结果内容: {json.dumps(results[0], ensure_ascii=False)[:500]}")
            
            entities = []
            for record in results:
                if record and isinstance(record, dict):
                    # 检查是否有 result 字段（Cypher 查询返回的格式）
                    if "result" in record:
                        result_data = record["result"]
                        if isinstance(result_data, dict) and "entity" in result_data:
                            entity = result_data["entity"]
                            entity["relationships"] = result_data.get("relationships", [])
                            entities.append(entity)
                        else:
                            logger.debug(f"[QA服务] result 字段格式不正确: {str(result_data)[:200]}")
                    # 直接包含 entity 字段的格式
                    elif "entity" in record:
                        entity = record["entity"]
                        entity["relationships"] = record.get("relationships", [])
                        entities.append(entity)
                    else:
                        logger.debug(f"[QA服务] 跳过不符合格式的记录: {list(record.keys())[:10]}")
                elif record:
                    logger.debug(f"[QA服务] 跳过非字典记录: {type(record)}")
            
            logger.debug(f"[QA服务] 解析出的实体数量: {len(entities)}")
            
            return {
                "entities": entities,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"[QA服务] 知识图谱查询失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            return {"entities": [], "keywords": []}
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract keywords from question."""
        stop_words = {
            "是什么", "有什么", "怎样", "如何", "什么", "那么", "这个", "这是",
            "的", "了", "和", "是", "在", "有", "一个", "中", "到", "会",
            "被", "以", "与", "为", "由", "通过", "从", "使用", "作为",
            "请问", "请", "能否", "可以", "能", "是否", "哪些", "哪个", "哪里",
            "为什么", "什么时候", "什么地方", "a", "an", "the", "is", "are",
            "what", "how", "why", "when", "where", "which", "can", "could",
            "would", "should", "might", "may", "do", "does", "did"
        }
        
        # 尝试使用 jieba 分词（如果可用）
        try:
            import jieba
            words = jieba.lcut(question)
        except ImportError:
            # 回退到基于规则的分词
            words = self._simple_chinese_segment(question)
        
        # 过滤停用词和短词
        keywords = []
        for word in words:
            word = word.strip()
            if word and len(word) > 1 and word not in stop_words:
                # 检查是否包含停用词（部分匹配）
                contains_stop = False
                for stop in stop_words:
                    if stop in word:
                        contains_stop = True
                        break
                if not contains_stop:
                    keywords.append(word)
        
        # 去重但保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:5]  # 最多5个关键词
    
    def _simple_chinese_segment(self, text: str) -> List[str]:
        """简单的中文分词方法（当 jieba 不可用时使用）"""
        words = []
        current = ""
        
        for char in text:
            if char in " \n\t，。！？、；：,.:!?;:":
                if current:
                    words.append(current)
                    current = ""
            else:
                current += char
        if current:
            words.append(current)
        
        # 尝试分割长词（基于常见中文词模式）
        result = []
        for word in words:
            if len(word) > 4:
                # 尝试按常见模式分割
                subwords = self._split_long_word(word)
                result.extend(subwords)
            else:
                result.append(word)
        
        return result
    
    def _split_long_word(self, word: str) -> List[str]:
        """分割长词的辅助方法"""
        subwords = []
        i = 0
        while i < len(word):
            # 尝试 3-4 个字符的词
            found = False
            for l in [4, 3, 2]:
                if i + l <= len(word):
                    candidate = word[i:i+l]
                    # 常见的中文技术词汇模式
                    if self._is_common_word(candidate):
                        subwords.append(candidate)
                        i += l
                        found = True
                        break
            if not found:
                subwords.append(word[i])
                i += 1
        return subwords
    
    def _is_common_word(self, word: str) -> bool:
        """检查是否是常见中文词汇"""
        common_words = {
            "软件", "工程", "开发", "设计", "系统", "技术", "数据", "算法",
            "网络", "安全", "架构", "测试", "维护", "管理", "项目", "产品",
            "代码", "编程", "语言", "框架", "平台", "工具", "服务", "应用",
            "人工智能", "机器学习", "深度学习", "神经网络", "自然语言",
            "计算机", "数据库", "服务器", "客户端", "接口", "协议", "标准",
            "重点", "核心", "基础", "原理", "方法", "技术", "理论", "实践"
        }
        return word in common_words
    
    def _format_context(self, kg_data: Dict[str, Any]) -> str:
        """Format knowledge graph data as context for AI."""
        context_parts = []
        
        for entity in kg_data.get("entities", []):
            entity_str = f"【{entity.get('name', 'Unknown')}】"
            
            if entity.get("type"):
                entity_str += f"\n类型: {entity['type']}"
            
            if entity.get("domain"):
                entity_str += f"\n领域: {entity['domain']}"
            
            if entity.get("category"):
                entity_str += f"\n分类: {entity['category']}"
            
            if entity.get("importance"):
                entity_str += f"\n重要性: {entity['importance']}"
            
            if entity.get("definition"):
                entity_str += f"\n定义: {entity['definition']}"
            
            if entity.get("description"):
                entity_str += f"\n描述: {entity['description']}"
            
            if entity.get("aliases") and isinstance(entity["aliases"], list) and entity["aliases"]:
                entity_str += f"\n别名: {', '.join(entity['aliases'])}"
            
            if entity.get("relationships"):
                rel_strs = []
                for rel in entity.get("relationships", [])[:8]:  # 最多8个关系（从5增加到8）
                    rel_str = f"{rel.get('type', 'RELATED')} {rel.get('target_name', 'Unknown')}"
                    rel_strs.append(rel_str)
                if rel_strs:
                    entity_str += f"\n关系: {', '.join(rel_strs)}"
            
            if entity.get("claims") and isinstance(entity["claims"], list) and entity["claims"]:
                claim_strs = []
                for claim in entity["claims"][:5]:  # 最多5个论断（从3增加到5）
                    claim_text = claim.get("claim_text", "")[:200]  # 增加到200字符（从150增加）
                    claim_type = claim.get("claim_type", "fact")
                    confidence = claim.get("confidence", 0.0)
                    if claim_text:
                        claim_str = f"{claim_type}({confidence:.2f}): {claim_text}"
                        claim_strs.append(claim_str)
                if claim_strs:
                    entity_str += f"\n论断:\n  - " + "\n  - ".join(claim_strs)
            
            context_parts.append(entity_str)
        
        return "\n\n".join(context_parts[:12])  # 最多12个实体（从10增加到12）
    
    def answer_with_graphrag(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer using GraphRAG (knowledge graph + AI).
        
        Uses Stage7 QueryService for advanced multi-path retrieval,
        then generates answer via LLM.
        
        Args:
            question: User's question
            conversation_history: Previous conversation messages
            session_id: Session ID for continuous conversation
        
        Returns:
            Dictionary with answer and metadata
        """
        if not self.ai_client:
            return {
                "success": False,
                "answer": "AI服务未配置",
                "used_context": False,
                "error": "AI客户端未初始化"
            }
        
        try:
            kg_context = ""
            used_kg = False
            entities = []
            
            try:
                from graphrag.stages.stage7_query_service import QueryService
                query_svc = QueryService()
                
                claim_candidates, concept_candidates = query_svc._multi_path_candidate_generation(
                    question, "hybrid", 15
                )
                
                claim_candidates = query_svc._graph_prior_collaboration(
                    claim_candidates, concept_candidates, max_hop=query_svc.max_hop
                )
                
                final_candidates = query_svc._merge_and_rerank(claim_candidates, 5)
                
                if final_candidates:
                    original_count = len(final_candidates)
                    high_conf_candidates = [c for c in final_candidates if c.confidence >= 0.5]
                    if high_conf_candidates:
                        final_candidates = high_conf_candidates
                        logger.info(f"[QA服务] 过滤低置信度证据: {len(final_candidates)} 条高质量证据 (原{original_count}条)")
                    kg_context = self._format_stage7_context(final_candidates, concept_candidates)
                    used_kg = True
                    entities = self._stage7_candidates_to_entities(final_candidates, concept_candidates)
                    logger.info(f"[QA服务] Stage7高级检索: {len(final_candidates)} 条证据, {len(concept_candidates)} 个概念")
                else:
                    logger.info("[QA服务] Stage7高级检索无结果，降级到关键词匹配")
                    kg_data = self.query_knowledge_graph(question)
                    if kg_data.get("entities"):
                        kg_context = self._format_context(kg_data)
                        used_kg = True
                        entities = kg_data.get("entities", [])
            except Exception as e:
                logger.warning(f"[QA服务] Stage7高级检索失败，降级到关键词匹配: {e}")
                kg_data = self.query_knowledge_graph(question)
                if kg_data.get("entities"):
                    kg_context = self._format_context(kg_data)
                    used_kg = True
                    entities = kg_data.get("entities", [])
            
            messages = []
            
            system_msg = """你是一个软件工程领域的高级专业问答助手，拥有知识图谱提供的权威结构化知识。

核心优势：你拥有经过严格抽取和验证的知识图谱信息，包括实体概念、关系网络和高质量论断，这是其他方法无法比拟的。

请严格按照以下原则回答：
1. 充分信任并直接使用知识图谱中的信息，这些信息经过严格验证，准确性极高
2. 充分利用知识图谱中的实体关系和论断，构建层次分明、逻辑严谨的专业答案
3. 利用知识图谱的结构化特性，从多个维度和层面全面阐述问题
4. 当知识图谱信息充足时，直接给出确定性结论，绝不使用"可能"、"或许"等不确定措辞
5. 当知识图谱信息部分覆盖时，以其为核心框架，补充必要的专业背景，确保答案完整
6. 答案必须详尽、专业、有深度，充分展现知识图谱在信息覆盖和结构化方面的优势
7. 使用markdown格式组织答案，包括多级标题、分层列表、加粗重点等，使结构清晰
8. 对每个关键概念给出定义或解释，对每个重要论断提供支撑依据"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            user_content = question
            if kg_context:
                user_content = f"""【知识图谱信息】
{kg_context}

【用户问题】
{question}"""
            
            messages.append({"role": "user", "content": user_content})
            
            logger.info(f"[QA服务] GraphRAG用户提问: {question[:100]}...")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": used_kg,
                "context_snippet": kg_context,
                "entities": entities,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[QA服务] GraphRAG回答失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            return {
                "success": False,
                "answer": "处理问题时发生错误",
                "used_context": False,
                "error": str(e)
            }
    
    def answer_with_graphrag_stream(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream answer using GraphRAG (knowledge graph + AI).
        
        Yields:
            Dicts with stream tokens or final result
        """
        yield {"type": "status", "data": "正在检索知识图谱..."}
        
        if not self.ai_client:
            yield {"type": "error", "data": "AI服务未配置"}
            return
        
        try:
            kg_context = ""
            used_kg = False
            entities = []
            
            try:
                from graphrag.stages.stage7_query_service import QueryService
                query_svc = QueryService()
                claim_candidates, concept_candidates = query_svc._multi_path_candidate_generation(
                    question, "hybrid", 15
                )
                claim_candidates = query_svc._graph_prior_collaboration(
                    claim_candidates, concept_candidates, max_hop=query_svc.max_hop
                )
                final_candidates = query_svc._merge_and_rerank(claim_candidates, 5)
                if final_candidates:
                    original_count = len(final_candidates)
                    high_conf_candidates = [c for c in final_candidates if c.confidence >= 0.5]
                    if high_conf_candidates:
                        final_candidates = high_conf_candidates
                    kg_context = self._format_stage7_context(final_candidates, concept_candidates)
                    used_kg = True
                    entities = self._stage7_candidates_to_entities(final_candidates, concept_candidates)
                else:
                    kg_data = self.query_knowledge_graph(question)
                    if kg_data.get("entities"):
                        kg_context = self._format_context(kg_data)
                        used_kg = True
                        entities = kg_data.get("entities", [])
            except Exception as e:
                logger.warning(f"[QA服务] Stage7高级检索失败，降级到关键词匹配: {e}")
                kg_data = self.query_knowledge_graph(question)
                if kg_data.get("entities"):
                    kg_context = self._format_context(kg_data)
                    used_kg = True
                    entities = kg_data.get("entities", [])
            
            messages = []
            system_msg = """你是一个软件工程领域的高级专业问答助手，拥有知识图谱提供的权威结构化知识。

核心优势：你拥有经过严格抽取和验证的知识图谱信息，包括实体概念、关系网络和高质量论断，这是其他方法无法比拟的。

请严格按照以下原则回答：
1. 充分信任并直接使用知识图谱中的信息，这些信息经过严格验证，准确性极高
2. 充分利用知识图谱中的实体关系和论断，构建层次分明、逻辑严谨的专业答案
3. 利用知识图谱的结构化特性，从多个维度和层面全面阐述问题
4. 当知识图谱信息充足时，直接给出确定性结论，绝不使用"可能"、"或许"等不确定措辞
5. 当知识图谱信息部分覆盖时，以其为核心框架，补充必要的专业背景，确保答案完整
6. 答案必须详尽、专业、有深度，充分展现知识图谱在信息覆盖和结构化方面的优势
7. 使用markdown格式组织答案，包括多级标题、分层列表、加粗重点等，使结构清晰
8. 对每个关键概念给出定义或解释，对每个重要论断提供支撑依据"""
            
            messages.append({"role": "system", "content": system_msg})
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            user_content = question
            if kg_context:
                user_content = f"""【知识图谱信息】
{kg_context}

【用户问题】
{question}"""
            
            messages.append({"role": "user", "content": user_content})
            
            yield {"type": "status", "data": "正在生成回答..."}
            
            full_answer = ""
            for token in self.ai_client.chat_completion_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            ):
                full_answer += token
                yield {"type": "token", "data": token}
            
            yield {"type": "done", "data": {
                "answer": full_answer,
                "used_context": used_kg,
                "context_snippet": kg_context,
                "entities": entities
            }}
        
        except Exception as e:
            logger.error(f"[QA服务] GraphRAG流式回答失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            yield {"type": "error", "data": str(e)}
    
    def answer_with_rag_stream(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"type": "status", "data": "正在检索向量数据库..."}

        if not self.ai_client:
            yield {"type": "error", "data": "AI服务未配置"}
            return

        try:
            vector_context = ""
            used_vector = False

            vector_results = self._query_vector_store(question)
            if vector_results:
                vector_context = "\n\n".join([
                    f"【文档片段{i+1}】\n类型: {r.get('type', 'unknown')}\n相似度: {r['similarity']:.4f}\n来源: {r.get('source', '')}\n内容: {r['text'][:800]}"
                    for i, r in enumerate(vector_results)
                ])
                used_vector = True

            messages = []
            system_msg = """你是一个软件工程领域的专业问答助手，基于提供的文档内容回答问题。

你拥有经过检索的专业文档片段作为参考，这为你提供了比纯LLM更可靠的信息来源。

请按照以下原则回答：
1. 文档中的信息是权威参考资料，请以其为依据构建准确答案
2. 基于文档中的事实和数据构建详细、准确的答案，充分阐述相关知识点
3. 当文档信息部分覆盖时，以文档内容为核心，适当补充必要的专业背景
4. 如果文档信息与自身知识存在冲突，以文档信息为准
5. 使用专业术语，提供有组织的答案
6. 使用markdown格式使答案更易阅读，包括标题、列表等
7. 答案应详尽但聚焦于文档所涵盖的内容范围"""

            messages.append({"role": "system", "content": system_msg})
            if conversation_history:
                messages.extend(conversation_history[-6:])

            user_content = question
            if vector_context:
                user_content = f"""【参考文档】
{vector_context}

【用户问题】
{question}"""

            messages.append({"role": "user", "content": user_content})

            yield {"type": "status", "data": "正在生成回答..."}

            full_answer = ""
            for token in self.ai_client.chat_completion_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            ):
                full_answer += token
                yield {"type": "token", "data": token}

            yield {"type": "done", "data": {
                "answer": full_answer,
                "used_context": used_vector,
                "context_snippet": vector_context
            }}

        except Exception as e:
            logger.error(f"[QA服务] RAG流式回答失败: {e}")
            yield {"type": "error", "data": str(e)}

    def answer_with_llm_stream(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"type": "status", "data": "准备回答..."}

        if not self.ai_client:
            yield {"type": "error", "data": "AI服务未配置"}
            return

        try:
            messages = []
            system_msg = """你是一个问答助手，请仅基于你自身的知识回答用户的问题。

严格限制：
1. 不要进行网络检索、知识库检索或任何外部信息查询
2. 你没有访问任何专业资料库的权限，只能依靠自身知识"""

            messages.append({"role": "system", "content": system_msg})
            if conversation_history:
                messages.extend(conversation_history[-6:])
            messages.append({"role": "user", "content": question})

            yield {"type": "status", "data": "正在生成回答..."}

            full_answer = ""
            for token in self.ai_client.chat_completion_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            ):
                full_answer += token
                yield {"type": "token", "data": token}

            yield {"type": "done", "data": {
                "answer": full_answer,
                "used_context": False,
                "context_snippet": None
            }}

        except Exception as e:
            logger.error(f"[QA服务] LLM流式回答失败: {e}")
            yield {"type": "error", "data": str(e)}

    def _format_stage7_context(
        self,
        claim_candidates: list,
        concept_candidates: list
    ) -> str:
        """将 Stage7 检索结果格式化为 LLM 可用的上下文"""
        context_parts = []
        
        concept_by_id = {}
        for c in concept_candidates[:8]:
            concept_by_id[c.concept_id] = c
        
        if concept_by_id:
            concept_section = "【相关概念】\n"
            for concept in concept_by_id.values():
                concept_section += f"- {concept.concept_name}"
                if concept.domain:
                    concept_section += f" (领域: {concept.domain})"
                concept_section += f" [来源: {concept.source}, 相关度: {(concept.score or 0.0):.2f}]\n"
            context_parts.append(concept_section)
        
        if claim_candidates:
            evidence_section = "【证据论断】\n"
            for i, claim in enumerate(claim_candidates[:5], 1):
                evidence_section += f"{i}. [{claim.claim_type}] (置信度: {claim.confidence:.2f}, 来源: {claim.source})\n"
                evidence_section += f"   {claim.claim_text[:300]}\n"
            context_parts.append(evidence_section)
        
        return "\n\n".join(context_parts)
    
    def _stage7_candidates_to_entities(
        self,
        claim_candidates: list,
        concept_candidates: list
    ) -> list:
        """将 Stage7 候选结果转换为实体列表（用于 trace 显示）"""
        entities = []
        for concept in concept_candidates[:5]:
            entity = {
                "name": concept.concept_name,
                "type": "Concept",
                "domain": concept.domain,
                "claims": []
            }
            for claim in claim_candidates:
                if claim.claim_text and concept.concept_name.lower() in claim.claim_text.lower():
                    entity["claims"].append({
                        "claim_text": claim.claim_text[:200],
                        "claim_type": claim.claim_type,
                        "confidence": claim.confidence
                    })
                    if len(entity["claims"]) >= 3:
                        break
            entities.append(entity)
        
        unassigned_claims = []
        assigned_texts = set()
        for entity in entities:
            for c in entity["claims"]:
                assigned_texts.add(c["claim_text"])
        for claim in claim_candidates[:5]:
            if claim.claim_text[:200] not in assigned_texts:
                unassigned_claims.append({
                    "claim_text": claim.claim_text[:200],
                    "claim_type": claim.claim_type,
                    "confidence": claim.confidence
                })
        if unassigned_claims and entities:
            entities[0]["claims"].extend(unassigned_claims[:2])
        
        return entities
    
    def answer_with_rag(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer using RAG (vector database retrieval + AI).
        
        Args:
            question: User's question
            conversation_history: Previous conversation messages
            session_id: Session ID for continuous conversation
        
        Returns:
            Dictionary with answer and metadata
        """
        if not self.ai_client:
            return {
                "success": False,
                "answer": "AI服务未配置",
                "used_context": False,
                "error": "AI客户端未初始化"
            }
        
        try:
            vector_context = ""
            used_vector = False
            
            vector_results = self._query_vector_store(question)
            if vector_results:
                # 显示所有检索结果，但限制每条内容的长度
                vector_context = "\n\n".join([
                    f"【文档片段{i+1}】\n类型: {r.get('type', 'unknown')}\n相似度: {r['similarity']:.4f}\n来源: {r.get('source', '')}\n内容: {r['text'][:800]}"
                    for i, r in enumerate(vector_results)
                ])
                used_vector = True
            
            messages = []
            
            system_msg = """你是一个软件工程领域的专业问答助手，基于提供的文档内容回答问题。

你拥有经过检索的专业文档片段作为参考，这为你提供了比纯LLM更可靠的信息来源。

请按照以下原则回答：
1. 文档中的信息是权威参考资料，请以其为依据构建准确答案
2. 基于文档中的事实和数据构建详细、准确的答案，充分阐述相关知识点
3. 当文档信息部分覆盖时，以文档内容为核心，适当补充必要的专业背景
4. 如果文档信息与自身知识存在冲突，以文档信息为准
5. 使用专业术语，提供有组织的答案
6. 使用markdown格式使答案更易阅读，包括标题、列表等
7. 答案应详尽但聚焦于文档所涵盖的内容范围"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            user_content = question
            if vector_context:
                user_content = f"""【参考文档】
{vector_context}

【用户问题】
{question}"""
            
            messages.append({"role": "user", "content": user_content})
            
            logger.info(f"[QA服务] 用户提问: {question[:100]}...")
            logger.debug(f"[QA服务] 历史对话数: {len(conversation_history) if conversation_history else 0}")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": used_vector,
                "context_snippet": vector_context,
                "vector_results": vector_results if used_vector else [],
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[QA服务] RAG回答失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            return {
                "success": False,
                "answer": "处理问题时发生错误",
                "used_context": False,
                "error": str(e)
            }
    
    def answer_with_llm(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer using LLM directly (no context).
        
        Args:
            question: User's question
            conversation_history: Previous conversation messages
            session_id: Session ID for continuous conversation
        
        Returns:
            Dictionary with answer and metadata
        """
        if not self.ai_client:
            return {
                "success": False,
                "answer": "AI服务未配置",
                "used_context": False,
                "error": "AI客户端未初始化"
            }
        
        try:
            messages = []
            
            system_msg = """你是一个问答助手，请仅基于你自身的知识回答用户的问题。

严格限制：
1. 不要进行网络检索、知识库检索或任何外部信息查询
2. 你没有访问任何专业资料库的权限，只能依靠自身知识"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            messages.append({"role": "user", "content": question})
            
            logger.info(f"[QA服务] 纯LLM用户提问: {question[:100]}...")
            logger.debug(f"[QA服务] 历史对话数: {len(conversation_history) if conversation_history else 0}")

            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": False,
                "context_snippet": None,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[QA服务] LLM回答失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            return {
                "success": False,
                "answer": "处理问题时发生错误",
                "used_context": False,
                "error": str(e)
            }

    def get_history(
            self,
            session_id: Optional[str] = None,
            limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取问答历史记录。

        Args:
            session_id: 可选会话ID筛选
            limit: 返回记录数量

        Returns:
            历史记录列表
        """
        try:
            if session_id:
                cypher = """
                MATCH (q:QARecord {session_id: $session_id})
                RETURN q.id as id,
                       q.question as question,
                       q.answer as answer,
                       q.timestamp as timestamp,
                       q.session_id as session_id,
                       q.used_context as used_context
                ORDER BY q.timestamp DESC
                LIMIT $limit
                """
                parameters = {"session_id": session_id, "limit": limit}
            else:
                cypher = """
                MATCH (q:QARecord)
                RETURN q.id as id,
                       q.question as question,
                       q.answer as answer,
                       q.timestamp as timestamp,
                       q.session_id as session_id,
                       q.used_context as used_context
                ORDER BY q.timestamp DESC
                LIMIT $limit
                """
                parameters = {"limit": limit}

            results = neo4j_client.execute_query(cypher, parameters)

            history = []
            for record in results:
                history.append({
                    "id": record.get("id"),
                    "question": record.get("question"),
                    "answer": record.get("answer"),
                    "timestamp": record.get("timestamp"),
                    "session_id": record.get("session_id"),
                    "used_context": record.get("used_context")
                })

            return history

        except Exception as e:
            logger.error(f"[QA服务] 获取历史记录失败: {e}")
            return []

    def add_feedback(self, feedback: Dict[str, Any]) -> bool:
        """
        添加问答反馈。

        Args:
            feedback: 反馈信息字典

        Returns:
            是否成功
        """
        try:
            if hasattr(feedback, 'qa_id'):
                qa_id = feedback.qa_id
                rating = feedback.rating
                feedback_text = feedback.feedback or ""
                helpful = feedback.helpful
            elif isinstance(feedback, dict):
                qa_id = feedback.get("qa_id")
                rating = feedback.get("rating", 5)
                feedback_text = feedback.get("feedback", "")
                helpful = feedback.get("helpful", True)
            else:
                logger.warning(f"[QA服务] 不支持的反馈类型: {type(feedback)}")
                return False

            if not qa_id:
                logger.warning("[QA服务] 反馈缺少QA ID")
                return False

            cypher = """
            MATCH (q:QARecord {id: $qa_id})
            SET q.feedback_rating = $rating,
                q.feedback_text = $feedback_text,
                q.helpful = $helpful,
                q.feedback_time = datetime()
            RETURN q.id as id
            """

            result = neo4j_client.execute_query(
                cypher,
                parameters={
                    "qa_id": qa_id,
                    "rating": rating,
                    "feedback_text": feedback_text,
                    "helpful": helpful
                }
            )

            if result:
                logger.info(f"[QA服务] 反馈已保存: {qa_id}")
                return True
            else:
                logger.warning(f"[QA服务] 未找到QA记录: {qa_id}")
                return False

        except Exception as e:
            logger.error(f"[QA服务] 保存反馈失败: {e}")
            return False

    def get_session_ids(self) -> List[str]:
        """
        获取所有会话ID。

        Returns:
            会话ID列表
        """
        try:
            cypher = """
            MATCH (q:QARecord)
            RETURN DISTINCT q.session_id as session_id
            ORDER BY q.session_id
            """

            results = neo4j_client.execute_query(cypher)
            return [record.get("session_id") for record in results if record.get("session_id")]

        except Exception as e:
            logger.error(f"[QA服务] 获取会话ID失败: {e}")
            return []

    def clear_old_records(self, days: int = 30) -> int:
        """
        清理指定天数前的旧记录。

        Args:
            days: 保留天数

        Returns:
            删除的记录数量
        """
        try:
            cypher = """
            MATCH (q:QARecord)
            WHERE q.timestamp < datetime() - duration('P' + $days + 'D')
            DELETE q
            RETURN count(q) as deleted_count
            """

            result = neo4j_client.execute_query(cypher, {"days": days})
            if result and result[0]:
                deleted_count = result[0].get("deleted_count", 0)
                logger.info(f"[QA服务] 清理了 {deleted_count} 条旧记录")
                return deleted_count
            return 0

        except Exception as e:
            logger.error(f"[QA服务] 清理旧记录失败: {e}")
            return 0


# 全局 QA 服务实例
qa_service = QAService()