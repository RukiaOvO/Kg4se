"""Intelligent Q&A service using Neo4j knowledge graph and AI providers."""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from infra.ai_providers import AIProviderFactory
from infra.neo4j_client import neo4j_client
from services.config_service import config_service
from utils.logger import get_logger

logger = get_logger("services.qa_service")


class QAService:
    """Service for intelligent Q&A using Neo4j knowledge graph."""
    
    def __init__(self):
        self.ai_client = self._initialize_ai_client()
        self.context_limit = 4000  # 字符限制，增加到4000以嵌入更多信息
    
    def chat(self, prompt: str, temperature: float = None) -> str:
        """通用聊天接口，供 PointwiseEvaluator 等评估器调用"""
        t = temperature if temperature is not None else 0.3
        system_msg = "You are a helpful assistant. Please respond in JSON format."
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
        logger.info(f"[QA服务 chat] 调用 judge_model，温度: {t}")
        return self.ai_client.chat_completion(messages=messages, temperature=t, json_mode=True)
    
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
                OR (n.aliases IS NOT NULL AND ANY(keyword IN $keywords WHERE 
                    ANY(alias IN n.aliases WHERE toLower(alias) CONTAINS toLower(keyword))
                ))
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
    
    def answer_question(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_kg: bool = True,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer user's question using AI and knowledge graph.
        
        Args:
            question: User's question
            conversation_history: Previous conversation messages
            use_kg: Whether to use knowledge graph context
            
        Returns:
            Dictionary with answer, used_context, and other metadata
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
            
            if use_kg:
                kg_data = self.query_knowledge_graph(question)
                entity_count = len(kg_data.get("entities", []))
                logger.debug(f"[QA服务] 知识图谱查询结果: {entity_count} 个实体")
                
                if kg_data.get("entities"):
                    kg_context = self._format_context(kg_data)
                    used_kg = True
                    logger.debug(f"[QA服务] 知识图谱上下文长度: {len(kg_context)} 字符")
                else:
                    logger.debug("[QA服务] 知识图谱未返回任何实体")
            
            messages = []
            
            system_msg = """你是一个智能问答助手，专门基于知识图谱回答用户提出的问题。

请按照以下指导原则：
1. 首先参考提供的知识图谱信息来答题
2. 如果知识图谱中有相关信息，优先使用这些信息。
3. 缺少的信息可以通过内置知识库补充，或者通过网络检索得到
4. 提供清晰、准确和有组织的答案
5. 答案应该简明扼要但足够详细
6. 使用markdown格式使答案更易阅读"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])  # 最多3轮对话
            
            user_content = question
            if kg_context:
                user_content = f"""【知识图谱信息】
{kg_context}

【用户问题】
{question}"""
            
            messages.append({"role": "user", "content": user_content})
            
            logger.info(f"[QA服务] 用户提问: {question[:100]}...")
            logger.debug(f"[QA服务] 历史对话数: {len(conversation_history) if conversation_history else 0}")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": used_kg,
                "context_snippet": kg_context,
                "entities": kg_data.get("entities", []),
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[QA服务] 回答问题失败: {e}")
            import traceback
            logger.debug(f"[错误详情] {traceback.format_exc()}")
            return {
                "success": False,
                "answer": "处理问题时发生错误",
                "used_context": False,
                "error": str(e)
            }
    
    def answer_with_graphrag(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer using GraphRAG (knowledge graph + AI).
        
        Args:
            question: User's question
            conversation_history: Previous conversation messages
            session_id: Session ID for continuous conversation
        
        Returns:
            Dictionary with answer and metadata
        """
        return self.answer_question(question, conversation_history, use_kg=True, session_id=session_id)
    
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
            
            system_msg = """你是一个智能问答助手，基于提供的文档内容和自身知识回答用户提出的问题。

请按照以下指导原则：
1. 首先参考提供的文档信息来答题，优先使用文档中的事实和数据
2. 如果文档信息不足以完整回答问题，可以结合自身知识库进行补充，但需要明确标注哪些内容来自文档、哪些是补充信息
3. 提供清晰、准确和有组织的答案
4. 如果文档信息与自身知识存在冲突，以文档信息为准
5. 答案应该简明扼要但足够详细
6. 使用markdown格式使答案更易阅读"""
            
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
                max_tokens=2048
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
            
            system_msg = """你是一个智能问答助手。请直接回答用户的问题。
            # 不要进行任何知识谱检索
            # 不要使用网络检索
            # 不能依赖任何外部信息"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            messages.append({"role": "user", "content": question})
            
            logger.info(f"[QA服务] 用户提问: {question[:100]}...")
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

    def _save_qa_record(self, question: str, answer: str, used_context: bool = False, session_id: Optional[str] = None) -> None:
        """
        保存问答记录到知识图谱。

        Args:
            question: 用户问题
            answer: AI回答
            used_context: 是否使用了知识图谱上下文
            session_id: 会话ID，如果未提供则生成新的
        """
        try:
            from uuid import uuid4
            qa_id = f"qa_{uuid4().hex[:12]}"
            timestamp = datetime.now().isoformat()

            if not session_id:
                import hashlib
                session_hash = hashlib.md5(timestamp.encode()).hexdigest()[:8]
                session_id = f"session_{session_hash}"

            cypher = """
            CREATE (q:QARecord {
                id: $qa_id,
                question: $question,
                answer: $answer,
                timestamp: datetime($timestamp),
                session_id: $session_id,
                used_context: $used_context,
                created_at: datetime()
            })
            RETURN q.id as id
            """

            neo4j_client.execute_query(
                cypher,
                parameters={
                    "qa_id": qa_id,
                    "question": question,
                    "answer": answer,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "used_context": used_context
                }
            )

            logger.info(f"[QA服务] 问答记录已保存: {qa_id}, 会话ID: {session_id}")

        except Exception as e:
            logger.error(f"[QA服务] 保存问答记录失败: {e}")

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