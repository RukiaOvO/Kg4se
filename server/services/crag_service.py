"""CRAG (Corrective Retrieval Augmented Generation) service."""
from typing import Optional, List, Dict, Any
from infra.config import Settings
from infra.ai_providers import get_ai_client
from infra.web_search import web_search_service


class CragEvaluator:
    """CRAG evaluator for assessing retrieval quality and performing knowledge correction."""
    
    def __init__(self):
        self.settings = Settings()
        self.ai_client = self._initialize_ai_client()
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.4
        }
    
    def _initialize_ai_client(self):
        """Initialize AI client for evaluation."""
        try:
            client = get_ai_client(
                provider=self.settings.ai_provider,
                api_key=self.settings.ai_api_key,
                model=self.settings.ai_model,
                base_url=self.settings.ai_base_url
            )
            print(f"✅ [CRAG] AI客户端初始化成功: {self.settings.ai_provider}")
            return client
        except Exception as e:
            print(f"⚠️ [CRAG] AI客户端初始化失败: {e}")
            return None
    
    def evaluate_retrieval(self, question: str, context: str) -> Dict[str, Any]:
        """
        Evaluate the quality of retrieved knowledge graph context.
        
        Args:
            question: User's question
            context: Retrieved knowledge graph context
            
        Returns:
            Dict with confidence score and evaluation result
        """
        if not self.ai_client or not context:
            return {
                "confidence": 0.0,
                "evaluation": "low",
                "reason": "No context or AI client available"
            }
        
        try:
            # 使用AI评估检索结果的质量
            evaluation_prompt = f"""
            You are an expert evaluator for retrieval quality in RAG systems.
            
            Please evaluate the following knowledge graph context for answering the user's question.
            
            User Question:
            {question}
            
            Retrieved Context:
            {context}
            
            Evaluate based on the following criteria:
            1. Relevance: How relevant is the context to the question? (0-1)
            2. Completeness: Does the context contain enough information to answer the question? (0-1)
            3. Accuracy: Is the information in the context accurate? (0-1)
            4. Clarity: Is the context clear and well-structured? (0-1)
            
            Provide your evaluation in JSON format with:
            - confidence: Overall confidence score (0-1)
            - evaluation: "high", "medium", or "low"
            - reason: Brief explanation of your evaluation
            - scores: Object with individual scores for each criterion
            """
            
            response = self.ai_client.chat_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.1,
                json_mode=True
            )
            
            # 解析评估结果
            import json
            evaluation_result = json.loads(response)
            
            # 确保返回有效的评估结果
            if not isinstance(evaluation_result, dict):
                raise ValueError("Invalid evaluation result format")
            
            # 计算置信度并确定评估等级
            confidence = evaluation_result.get("confidence", 0.0)
            if confidence >= self.confidence_thresholds["high"]:
                evaluation = "high"
            elif confidence >= self.confidence_thresholds["medium"]:
                evaluation = "medium"
            else:
                evaluation = "low"
            
            return {
                "confidence": confidence,
                "evaluation": evaluation,
                "reason": evaluation_result.get("reason", ""),
                "scores": evaluation_result.get("scores", {})
            }
            
        except Exception as e:
            print(f"❌ [CRAG] 评估检索结果失败: {e}")
            # 如果评估失败，返回低置信度
            return {
                "confidence": 0.3,
                "evaluation": "low",
                "reason": f"Evaluation failed: {str(e)}",
                "scores": {}
            }
    
    def correct_knowledge(self, question: str, context: str, evaluation: Dict[str, Any]) -> str:
        """
        Perform knowledge correction based on evaluation result.
        
        Args:
            question: User's question
            context: Retrieved knowledge graph context
            evaluation: Evaluation result from evaluate_retrieval
            
        Returns:
            Corrected and enhanced context
        """
        evaluation_level = evaluation.get("evaluation", "low")
        
        if evaluation_level == "high":
            # 高置信度：知识精炼
            return self._refine_knowledge(context, question)
        elif evaluation_level == "medium":
            # 中置信度：结合网络搜索
            web_info = web_search_service.get_relevant_information(question, context)
            return self._merge_knowledge(context, web_info)
        else:
            # 低置信度：依赖网络搜索
            web_info = web_search_service.get_relevant_information(question, context)
            if web_info:
                return f"【知识图谱信息】\n{context}\n\n【网络搜索补充】\n{web_info}"
            else:
                return context
    
    def _refine_knowledge(self, context: str, question: str) -> str:
        """
        Refine knowledge by removing redundancy and focusing on relevant information.
        
        Args:
            context: Original knowledge graph context
            question: User's question
            
        Returns:
            Refined context
        """
        if not self.ai_client:
            return context
        
        try:
            refinement_prompt = f"""
            You are a knowledge refinement expert.
            
            Please refine the following knowledge graph context to make it more relevant and concise
            for answering the user's question.
            
            User Question:
            {question}
            
            Original Context:
            {context}
            
            Refinement guidelines:
            1. Remove irrelevant information
            2. Focus on the most relevant entities and relationships
            3. Keep the context concise but informative
            4. Maintain the original structure and format
            
            Return the refined context.
            """
            
            refined_context = self.ai_client.chat_completion(
                messages=[{"role": "user", "content": refinement_prompt}],
                temperature=0.1
            )
            
            return refined_context
            
        except Exception as e:
            print(f"❌ [CRAG] 知识精炼失败: {e}")
            return context
    
    def _merge_knowledge(self, kg_context: str, web_context: str) -> str:
        """
        Merge knowledge graph context with web search results.
        
        Args:
            kg_context: Knowledge graph context
            web_context: Web search results
            
        Returns:
            Merged and integrated context
        """
        if not web_context:
            return kg_context
        
        merged_context = f"【知识图谱信息】\n{kg_context}\n\n【网络搜索补充】\n{web_context}"
        return merged_context


class CragService:
    """CRAG service for integrating with QA service."""
    
    def __init__(self):
        self.evaluator = CragEvaluator()
    
    def enhance_context(self, question: str, context: str) -> Dict[str, Any]:
        """
        Enhance context using CRAG methodology.
        
        Args:
            question: User's question
            context: Original knowledge graph context
            
        Returns:
            Dict with enhanced context and evaluation metadata
        """
        # 评估检索结果
        evaluation = self.evaluator.evaluate_retrieval(question, context)
        
        # 执行知识纠正
        enhanced_context = self.evaluator.correct_knowledge(question, context, evaluation)
        
        return {
            "enhanced_context": enhanced_context,
            "evaluation": evaluation,
            "used_crag": True
        }


# 全局CRAG服务实例
crag_service = CragService()