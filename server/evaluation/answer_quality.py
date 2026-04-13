"""
回答质量评估模块

参考论文:
- RAG vs. GraphRAG: A Systematic Evaluation (Han et al., 2025)
- GraphRAG vs Vector RAG: Accuracy Benchmark Insights (FalkorDB, 2025)
- A review on Graph RAG methods (Akbari, 2025)
"""

from typing import Dict, Any, List
import json
from datetime import datetime
import numpy as np

class AnswerQualityEvaluator:
    def __init__(self, llm_client=None, embedding_model=None):
        self.llm_client = llm_client
        self.embedding_model = embedding_model
    
    def evaluate(self, predicted: str, expected: str, context: str = "") -> Dict[str, Any]:
        result = {
            "predicted": predicted,
            "expected": expected,
            "context": context,
            "automatic": self._automatic_evaluation(predicted, expected),
            "llm_judge": self._llm_based_evaluation(predicted, expected, context) if self.llm_client else None,
            "overall_score": 0.0
        }
        
        result["overall_score"] = self._calculate_overall(result)
        
        return result
    
    def _automatic_evaluation(self, predicted: str, expected: str) -> Dict[str, float]:
        semantic_sim = self._semantic_similarity(predicted, expected)
        word_overlap = self._word_overlap_similarity(predicted, expected)
        length_match = self._length_match(predicted, expected)
        
        return {
            "semantic_similarity": round(semantic_sim, 4),
            "word_overlap": round(word_overlap, 4),
            "length_match": round(length_match, 4),
            "score": round((semantic_sim * 0.5 + word_overlap * 0.3 + length_match * 0.2), 4)
        }
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        if not self.embedding_model:
            return self._simple_similarity(text1, text2)
        
        try:
            emb1 = self.embedding_model.encode(text1)
            emb2 = self.embedding_model.encode(text2)
            return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        except:
            return self._simple_similarity(text1, text2)
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        if not text1 or not text2:
            return 0.0
        
        len1, len2 = len(text1), len(text2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if text1[i-1] == text2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_len = dp[len1][len2]
        return lcs_len / min(len1, len2) if min(len1, len2) > 0 else 0.0
    
    def _word_overlap_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _length_match(self, text1: str, text2: str) -> float:
        len1, len2 = len(text1), len(text2)
        
        if len1 == 0 and len2 == 0:
            return 1.0
        
        return 1 - abs(len1 - len2) / max(len1, len2)
    
    def _get_default_evaluation(self) -> Dict[str, Any]:
        """
        返回默认评估结果，当LLM评估失败时使用。
        采用中性评分（3分/5分 = 0.6），表示无法确定质量。
        """
        return {
            "accuracy": 3.0,
            "completeness": 3.0,
            "relevance": 3.0,
            "expertise": 3.0,
            "explainability": 3.0,
            "overall": 3.0,
            "comment": "LLM评估失败，使用默认评分"
        }
    
    def _llm_based_evaluation(self, predicted: str, expected: str, context: str = "") -> Dict[str, Any]:
        prompt = f"""
        你是一位软件工程领域的专业评估专家。请对比以下回答与参考答案：
        
        问题上下文（如适用）: {context}
        
        参考答案:
        {expected}
        
        待评估回答:
        {predicted}
        
        请从以下维度进行评分（1-5分，1分最差，5分最好）：
        
        1. 准确性（Accuracy）：回答内容是否正确无误？
        2. 完整性（Completeness）：是否覆盖了问题的所有关键点？
        3. 相关性（Relevance）：回答是否与问题直接相关？
        4. 专业性（Expertise）：是否正确使用了专业术语和概念？
        5. 可解释性（Explainability）：是否清晰说明推理过程？
        
        输出格式（JSON）：
        {{
            "accuracy": 分数,
            "completeness": 分数,
            "relevance": 分数,
            "expertise": 分数,
            "explainability": 分数,
            "overall": 平均分,
            "comment": "简短评语（不超过50字）"
        }}
        """
        
        try:
            response = self.llm_client.chat(prompt)
            if not response or not response.strip():
                raise ValueError("LLM返回空响应")
            
            result = json.loads(response)
            
            required_fields = ["accuracy", "completeness", "relevance", "expertise", "explainability", "overall"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"缺少字段: {field}")
            
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️ [LLM评估] JSON解析失败: {e}")
            print(f"   原始响应: {response[:200] if response else '空'}")
            return self._get_default_evaluation()
        except ValueError as e:
            print(f"⚠️ [LLM评估] 响应格式错误: {e}")
            return self._get_default_evaluation()
        except Exception as e:
            print(f"⚠️ [LLM评估] LLM-as-a-Judge 调用失败: {type(e).__name__}: {e}")
            return self._get_default_evaluation()
    
    def _calculate_overall(self, result: Dict[str, Any]) -> float:
        auto_score = result["automatic"]["score"]
        
        if result["llm_judge"]:
            llm_score = result["llm_judge"]["overall"] / 5.0
            return round((auto_score * 0.4 + llm_score * 0.6), 4)
        else:
            return auto_score


class ComparativeExperiment:
    def __init__(self, graphrag_service=None, rag_service=None, llm_service=None):
        self.graphrag = graphrag_service
        self.rag = rag_service
        self.llm = llm_service
        self.evaluator = AnswerQualityEvaluator(llm_client=llm_service)
    
    def run(self, test_dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("🔬 [对比实验] 开始 GraphRAG vs RAG vs LLM 对比实验")
        print("="*80)
        print(f"📊 测试数据集大小: {len(test_dataset)}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(test_dataset),
            "graphrag": [],
            "rag": [],
            "llm": [],
            "statistics": {},
            "improvement": {}
        }
        
        for idx, item in enumerate(test_dataset, 1):
            print(f"\n--- 问题 {idx}/{len(test_dataset)} ---")
            print(f"问题: {item['question'][:50]}...")
            
            print("   🟢 正在获取 GraphRAG 回答...")
            rag_answer = self._get_graphrag_answer(item["question"])
            
            print("   🟡 正在获取 RAG 回答...")
            vector_rag_answer = self._get_rag_answer(item["question"])
            
            print("   🔵 正在获取 LLM 回答...")
            llm_answer = self._get_llm_answer(item["question"])
            
            context = item.get("context", "")
            expected = item["expected"]
            
            results["graphrag"].append({
                "question": item["question"],
                "answer": rag_answer,
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": self.evaluator.evaluate(rag_answer, expected, context)
            })
            
            results["rag"].append({
                "question": item["question"],
                "answer": vector_rag_answer,
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": self.evaluator.evaluate(vector_rag_answer, expected, context)
            })
            
            results["llm"].append({
                "question": item["question"],
                "answer": llm_answer,
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": self.evaluator.evaluate(llm_answer, expected, context)
            })
        
        results["statistics"] = self._compute_statistics(results)
        results["improvement"] = self._compute_improvement(results)
        
        print("\n" + "="*80)
        print("✅ [对比实验] 实验完成")
        print("="*80)
        
        return results
    
    def _get_graphrag_answer(self, question: str) -> str:
        if self.graphrag:
            try:
                return self.graphrag.query(question)
            except Exception as e:
                print(f"⚠️ GraphRAG 查询失败: {e}")
                return "回答失败"
        return "GraphRAG 服务未配置"
    
    def _get_rag_answer(self, question: str) -> str:
        if self.rag:
            try:
                return self.rag.query(question)
            except Exception as e:
                print(f"⚠️ RAG 查询失败: {e}")
                return "回答失败"
        return "RAG 服务未配置"
    
    def _get_llm_answer(self, question: str) -> str:
        if self.llm:
            try:
                return self.llm.complete(question)
            except Exception as e:
                print(f"⚠️ LLM 查询失败: {e}")
                return "回答失败"
        return "LLM 服务未配置"
    
    def _compute_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        def get_metrics(items, key):
            if isinstance(key, str):
                scores = [item["evaluation"][key] for item in items]
            else:
                scores = [key(item) for item in items]
            return {
                "mean": round(sum(scores) / len(scores), 4),
                "std": round(np.std(scores), 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4)
            }
        
        return {
            "graphrag": {
                "overall": get_metrics(results["graphrag"], "overall_score"),
                "automatic": get_metrics(results["graphrag"], lambda x: x["evaluation"]["automatic"]["score"]),
                "llm_judge": get_metrics(results["graphrag"], lambda x: x["evaluation"]["llm_judge"]["overall"] / 5.0 if x["evaluation"]["llm_judge"] else 0)
            },
            "rag": {
                "overall": get_metrics(results["rag"], "overall_score"),
                "automatic": get_metrics(results["rag"], lambda x: x["evaluation"]["automatic"]["score"]),
                "llm_judge": get_metrics(results["rag"], lambda x: x["evaluation"]["llm_judge"]["overall"] / 5.0 if x["evaluation"]["llm_judge"] else 0)
            },
            "llm": {
                "overall": get_metrics(results["llm"], "overall_score"),
                "automatic": get_metrics(results["llm"], lambda x: x["evaluation"]["automatic"]["score"]),
                "llm_judge": get_metrics(results["llm"], lambda x: x["evaluation"]["llm_judge"]["overall"] / 5.0 if x["evaluation"]["llm_judge"] else 0)
            }
        }
    
    def _compute_improvement(self, results: Dict[str, Any]) -> Dict[str, float]:
        stats = results["statistics"]
        
        rag_mean = stats["rag"]["overall"]["mean"]
        llm_mean = stats["llm"]["overall"]["mean"]
        graphrag_mean = stats["graphrag"]["overall"]["mean"]
        
        return {
            "graphrag_over_rag_percent": round(((graphrag_mean - rag_mean) / rag_mean) * 100, 2) if rag_mean > 0 else 0,
            "graphrag_over_llm_percent": round(((graphrag_mean - llm_mean) / llm_mean) * 100, 2) if llm_mean > 0 else 0,
            "rag_over_llm_percent": round(((rag_mean - llm_mean) / llm_mean) * 100, 2) if llm_mean > 0 else 0
        }
    
    def save_report(self, results: Dict[str, Any], output_path: str = None):
        if not output_path:
            output_path = f"comparative_experiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 [对比实验] 报告已保存到: {output_path}")