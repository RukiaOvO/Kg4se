"""Intelligent Q&A service using Neo4j knowledge graph and AI providers."""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from infra.ai_providers import AIProviderFactory
from infra.neo4j_client import neo4j_client
from infra.faiss_store import faiss_store
from services.config_service import config_service
from utils.logger import get_logger

logger = get_logger("services.qa_service")


class QAService:
    """Service for intelligent Q&A using Neo4j knowledge graph."""
    
    def __init__(self):
        self.ai_client = self._initialize_ai_client()
        self.context_limit = 2000  # 字符限制
    
    def _query_vector_store(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query vector store for similar documents."""
        try:
            from infra.ai_providers import AIProviderFactory
            
            ai_config = config_service.get_ai_provider_config()
            embedding_client = AIProviderFactory.create_client(
                provider=ai_config["provider"],
                api_key=ai_config["api_key"],
                model=ai_config["model"],
                base_url=ai_config["base_url"]
            )
            
            query_embedding = embedding_client.embedding(question)
            results = faiss_store.search(query_embedding, top_k=top_k)
            
            contexts = []
            for result in results:
                if result.metadata:
                    contexts.append({
                        "text": result.metadata.get("text", ""),
                        "source": result.metadata.get("source", ""),
                        "similarity": result.similarity
                    })
            
            return contexts
        except Exception as e:
            logger.error(f"[QA服务] 向量数据库查询失败: {e}")
            return []
        
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
    
    def query_knowledge_graph(self, question: str, limit: int = 5) -> Dict[str, Any]:
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
            
            if not keywords:
                return {"entities": [], "relationships": []}
            
            cypher = """
            MATCH (n:Concept)
            WHERE ANY(keyword IN $keywords WHERE toLower(n.name) CONTAINS toLower(keyword) 
                   OR ANY(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower(keyword)))
            WITH n LIMIT $limit
            OPTIONAL MATCH (n)-[r]-(related)
            WITH n, collect({
                type: type(r),
                target_name: related.name,
                target_type: coalesce(related.type, 'Unknown')
            }) AS rels
            RETURN {
                entity: {
                    id: id(n),
                    name: n.name,
                    type: n.type,
                    definition: n.definition,
                    domain: n.domain,
                    aliases: n.aliases
                },
                relationships: rels
            } AS result
            """
            
            results = neo4j_client.execute_query(
                cypher,
                parameters={
                    "keywords": keywords,
                    "limit": limit
                }
            )
            
            entities = []
            for record in results:
                if record and isinstance(record, dict) and "entity" in record:
                    entity = record["entity"]
                    entity["relationships"] = record.get("relationships", [])
                    entities.append(entity)
            
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
        
        words = []
        current = ""
        for char in question:
            if char in " \n\t，。！？,.:!?":
                if current:
                    words.append(current)
                    current = ""
            else:
                current += char
        if current:
            words.append(current)
        
        keywords = [w for w in words if w and len(w) > 1 and w not in stop_words]
        return keywords[:5]  # 最多5个关键词
    
    def _format_context(self, kg_data: Dict[str, Any]) -> str:
        """Format knowledge graph data as context for AI."""
        context_parts = []
        
        for entity in kg_data.get("entities", []):
            entity_str = f"【{entity.get('name', 'Unknown')}】"
            
            if entity.get("definition"):
                entity_str += f"\n定义: {entity['definition']}"
            
            if entity.get("type"):
                entity_str += f"\n类型: {entity['type']}"
            
            if entity.get("domain"):
                entity_str += f"\n领域: {entity['domain']}"
            
            if entity.get("relationships"):
                rel_strs = []
                for rel in entity.get("relationships", [])[:3]:  # 最多3个关系
                    rel_str = f"{rel.get('type', 'RELATED')} {rel.get('target_name', 'Unknown')}"
                    rel_strs.append(rel_str)
                if rel_strs:
                    entity_str += f"\n关系: {', '.join(rel_strs)}"
            
            context_parts.append(entity_str)
        
        return "\n\n".join(context_parts[:10])  # 最多10个实体
    
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
                if kg_data.get("entities"):
                    kg_context = self._format_context(kg_data)
                    used_kg = True
            
            messages = []
            
            system_msg = """你是一个智能问答助手，专门基于知识图谱回答用户提出的问题。

请按照以下指导原则：
1. 首先参考提供的知识图谱信息来答题
2. 如果知识图谱中有相关信息，优先使用这些信息
3. 提供清晰、准确和有组织的答案
4. 如果信息不足，请说明并给出可能的解释
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
            logger.debug(f"[QA服务] 完整Prompt:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": used_kg,
                "context_snippet": kg_context[:300] if kg_context else None,
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
                vector_context = "\n\n".join([
                    f"【文档片段】\n相似度: {r['similarity']:.4f}\n内容: {r['text'][:500]}"
                    for r in vector_results[:3]
                ])
                used_vector = True
            
            messages = []
            
            system_msg = """你是一个智能问答助手，专门基于提供的文档内容回答用户提出的问题。

请按照以下指导原则：
1. 首先参考提供的文档信息来答题
2. 如果文档中有相关信息，优先使用这些信息
3. 提供清晰、准确和有组织的答案
4. 如果信息不足，请说明并给出可能的解释
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
            logger.debug(f"[QA服务] 完整Prompt:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )
            
            return {
                "success": True,
                "answer": answer,
                "used_context": used_vector,
                "context_snippet": vector_context[:300] if vector_context else None,
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
            
            system_msg = """你是一个智能问答助手。请直接回答用户的问题，提供清晰、准确和有组织的答案。"""
            
            messages.append({"role": "system", "content": system_msg})
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            messages.append({"role": "user", "content": question})
            
            logger.info(f"[QA服务] 用户提问: {question[:100]}...")
            logger.debug(f"[QA服务] 历史对话数: {len(conversation_history) if conversation_history else 0}")
            logger.debug(f"[QA服务] 完整Prompt:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            answer = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1024
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