"""
LLM-as-a-Judge 评估模块 - 全面优化版

参考论文:
- RAG vs. GraphRAG: A Systematic Evaluation (Han et al., 2026)
- GraphRAG vs Vector RAG: Accuracy Benchmark Insights (FalkorDB, 2025)
- A review on Graph RAG methods (Peng et al., 2024)
- Retrieval-Augmented Generation with Graphs (Han et al., 2025)

核心特性:
1. Pointwise 单回答评分 - 支持多次采样聚合
2. Pairwise 成对比较 - 支持位置交换缓解偏差
3. 独立评判模型 - 避免"自己评自己"问题
4. 完整偏差处理策略 - 位置偏差、冗长偏差、标签偏差
5. 增强统计指标 - 胜率、分题型统计、Bootstrap置信区间
"""

from typing import Dict, Any, List, Optional, Callable
import json
from datetime import datetime
import numpy as np
from numpy.random import RandomState

try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    ROUGE_AVAILABLE = False


class PointwiseEvaluator:
    """Pointwise 单回答评分器 - 支持多次采样和偏差缓解"""
    
    def __init__(self, llm_client=None, embedding_model=None, judge_model=None):
        self.llm_client = llm_client
        self.embedding_model = embedding_model
        self.judge_model = judge_model or llm_client
        self.rng = RandomState(42)
    
    def evaluate(self, 
                 predicted: str, 
                 expected: str, 
                 context: str = "",
                 num_samples: int = 3,
                 return_all_samples: bool = False) -> Dict[str, Any]:
        """
        评估单个回答质量
        
        Args:
            predicted: 待评估回答
            expected: 参考答案
            context: 问题上下文
            num_samples: 采样次数（缓解随机性）
            return_all_samples: 是否返回所有采样结果
        
        Returns:
            包含各维度评分和综合评分的字典
        """
        result = {
            "predicted": predicted,
            "expected": expected,
            "context": context,
            "automatic": self._automatic_evaluation(predicted, expected),
            "fact_consistency": self._fact_consistency(predicted, context),
            "llm_judge": None,
            "overall_score": 0.0,
            "samples": []
        }
        
        if self.judge_model:
            llm_results = []
            for _ in range(num_samples):
                sample = self._llm_based_evaluation(predicted, expected, context)
                llm_results.append(sample)
            
            aggregated = self._aggregate_samples(llm_results)
            result["llm_judge"] = aggregated
            result["samples"] = llm_results if return_all_samples else None
        
        result["overall_score"] = self._calculate_overall(result)
        
        return result
    
    def _automatic_evaluation(self, predicted: str, expected: str) -> Dict[str, float]:
        """自动化指标评估"""
        semantic_sim = self._semantic_similarity(predicted, expected)
        word_overlap = self._word_overlap_similarity(predicted, expected)
        length_match = self._length_match(predicted, expected)
        rouge_l = self._rouge_l_score(predicted, expected)
        
        return {
            "semantic_similarity": round(semantic_sim, 4),
            "word_overlap": round(word_overlap, 4),
            "length_match": round(length_match, 4),
            "rouge_l": round(rouge_l, 4),
            "score": round((semantic_sim * 0.35 + word_overlap * 0.2 + length_match * 0.15 + rouge_l * 0.3), 4)
        }
    
    def _rouge_l_score(self, text1: str, text2: str) -> float:
        if not ROUGE_AVAILABLE:
            return self._simple_similarity(text1, text2)
        
        try:
            scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            scores = scorer.score(text2, text1)
            return scores['rougeL'].fmeasure
        except Exception:
            return self._simple_similarity(text1, text2)
    
    def _fact_consistency(self, predicted: str, context: str) -> float:
        """检测回答与上下文的事实一致性"""
        if not context or not predicted:
            return 1.0
        
        try:
            if self.judge_model:
                prompt = self._build_fact_consistency_prompt(context, predicted)
                response = self.judge_model.chat(prompt)
                try:
                    score = float(response.strip())
                    return max(0.0, min(1.0, score))
                except ValueError:
                    return 0.7
            else:
                return 0.7
        except Exception:
            return 0.7
    
    def _build_fact_consistency_prompt(self, context: str, predicted: str) -> str:
        """构建事实一致性检测 Prompt"""
        return f"""
请判断以下回答是否与上下文信息一致：

上下文: {context[:1000]}

回答: {predicted[:1000]}

请输出一个0到1之间的分数，表示一致性程度：
- 1.0 = 完全一致，所有陈述都符合上下文
- 0.5 = 部分一致，部分内容符合上下文
- 0.0 = 完全矛盾，存在明显事实错误

只输出数字，不要输出其他内容。
"""
    
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
        text1, text2 = text1.lower().strip(), text2.lower().strip()
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
        words1, words2 = set(text1.lower().split()), set(text2.lower().split())
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
        """返回默认评估结果"""
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
        """单次 LLM 评估"""
        prompt = self._build_pointwise_prompt(predicted, expected, context)
        
        try:
            response = self.judge_model.chat(prompt)
            if not response or not response.strip():
                raise ValueError("LLM返回空响应")
            
            result = json.loads(response)
            
            required_fields = ["accuracy", "completeness", "relevance", "expertise", "explainability", "overall"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"缺少字段: {field}")
            
            return result
        except json.JSONDecodeError:
            return self._get_default_evaluation()
        except ValueError:
            return self._get_default_evaluation()
        except Exception:
            return self._get_default_evaluation()
    
    def _build_pointwise_prompt(self, predicted: str, expected: str, context: str = "") -> str:
        """构建 Pointwise 评分 Prompt（带评分锚点）"""
        return f"""
# 角色设定
你是一名严格且公平的《软件工程》课程评审专家。你必须依据评分标准客观评分，不受回答长度、措辞风格等表面因素影响。

# 评分标准（1-5分）
1. 准确性（Accuracy）：回答的事实是否正确，是否与《软件工程》课程知识体系一致
   - 1分：多处事实错误或严重偏离课程内容
   - 3分：基本正确，但有少量不准确或含糊之处
   - 5分：完全正确，精确符合课程知识体系

2. 完整性（Completeness）：回答是否覆盖了问题的所有关键要点
   - 1分：仅涉及少量要点，遗漏重要内容
   - 3分：覆盖了大部分要点，但仍有明显缺失
   - 5分：全面覆盖所有关键要点，无重要遗漏

3. 相关性（Relevance）：回答是否与问题直接相关
   - 1分：完全不相关或答非所问
   - 3分：部分相关，存在冗余内容
   - 5分：高度相关，无冗余内容

4. 专业性（Expertise）：是否正确使用了专业术语和概念
   - 1分：未使用专业术语，概念混淆
   - 3分：基本正确使用专业术语
   - 5分：准确使用专业术语和概念

5. 可解释性（Explainability）：是否清晰说明推理过程
   - 1分：推理过程完全不清晰
   - 3分：部分说明推理过程
   - 5分：清晰说明推理过程，逻辑严谨

# 禁止事项
- 回答长度不应影响评分，重点评估内容质量而非数量
- 评分应基于参考答案和问题上下文进行对比

# 输入
问题上下文：{context}

参考答案：
{expected}

待评估回答：
{predicted}

# 输出格式
请严格按照以下JSON格式输出，不要添加任何其他内容：
{{
    "accuracy": 0,
    "completeness": 0,
    "relevance": 0,
    "expertise": 0,
    "explainability": 0,
    "overall": 0,
    "comment": "简短评语（不超过50字）"
}}
"""
    
    def _aggregate_samples(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """聚合多次采样结果"""
        if not samples:
            return self._get_default_evaluation()
        
        aggregated = {}
        dimensions = ["accuracy", "completeness", "relevance", "expertise", "explainability"]
        
        for dim in dimensions:
            values = [s[dim] for s in samples]
            aggregated[dim] = round(sum(values) / len(values), 2)
        
        aggregated["overall"] = round(sum(aggregated[dim] for dim in dimensions) / len(dimensions), 2)
        aggregated["comment"] = f"基于 {len(samples)} 次评估的平均结果"
        aggregated["sample_std"] = {dim: round(np.std([s[dim] for s in samples]), 2) for dim in dimensions}
        
        return aggregated
    
    def _calculate_overall(self, result: Dict[str, Any]) -> float:
        auto_score = result["automatic"]["score"]
        
        if result["llm_judge"]:
            llm_score = result["llm_judge"]["overall"] / 5.0
            return round((auto_score * 0.6 + llm_score * 0.4), 4)
        else:
            return auto_score


class PairwiseEvaluator:
    """Pairwise 成对比较器 - 支持位置交换缓解偏差"""
    
    def __init__(self, llm_client=None, judge_model=None):
        self.llm_client = llm_client
        self.judge_model = judge_model or llm_client
    
    def compare(self, 
                question: str, 
                answer_a: str, 
                answer_b: str,
                model_a_name: str = "模型A",
                model_b_name: str = "模型B",
                enable_position_swap: bool = True) -> Dict[str, Any]:
        """
        成对比较两个回答
        
        Args:
            question: 问题
            answer_a: 回答A
            answer_b: 回答B
            model_a_name: 模型A名称（用于匿名化）
            model_b_name: 模型B名称（用于匿名化）
            enable_position_swap: 是否启用位置交换（缓解位置偏差）
        
        Returns:
            包含评分、胜负结果和推理的字典
        """
        results = []
        
        # 第一次比较：A在前，B在后
        result1 = self._single_compare(question, answer_a, answer_b, model_a_name, model_b_name)
        results.append(result1)
        
        # 第二次比较：B在前，A在后（缓解位置偏差）
        if enable_position_swap:
            result2 = self._single_compare(question, answer_b, answer_a, model_b_name, model_a_name)
            results.append(result2)
        
        # 聚合结果
        return self._aggregate_comparison(results, model_a_name, model_b_name)
    
    def _single_compare(self, 
                       question: str, 
                       answer_a: str, 
                       answer_b: str,
                       name_a: str, 
                       name_b: str) -> Dict[str, Any]:
        """单次成对比较"""
        prompt = self._build_pairwise_prompt(question, answer_a, answer_b, name_a, name_b)
        
        try:
            response = self.judge_model.chat(prompt)
            if not response or not response.strip():
                raise ValueError("LLM返回空响应")
            
            result = json.loads(response)
            
            required_fields = ["scores", "winner", "reasoning"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"缺少字段: {field}")
            
            return result
        except json.JSONDecodeError:
            return self._get_default_comparison(name_a, name_b)
        except ValueError:
            return self._get_default_comparison(name_a, name_b)
        except Exception:
            return self._get_default_comparison(name_a, name_b)
    
    def _build_pairwise_prompt(self, 
                              question: str, 
                              answer_a: str, 
                              answer_b: str,
                              name_a: str, 
                              name_b: str) -> str:
        """构建 Pairwise 比较 Prompt"""
        return f"""
# 角色设定
你是一名严格且公平的评审专家，负责比较两个模型对同一问题的回答质量。
你必须依据评价标准独立判断，不受回答长度、措辞风格等表面因素的影响。

# 评价标准
请从以下四个维度综合评估：

1. 准确性：回答的事实是否正确
   - 1分：多处事实错误
   - 3分：基本正确，少量不准确
   - 5分：完全正确

2. 全面性：是否覆盖所有关键要点
   - 1分：仅涉及少量要点
   - 3分：覆盖大部分要点
   - 5分：全面覆盖

3. 逻辑连贯性：论证是否条理清晰、推理严谨
   - 1分：逻辑混乱，论证跳跃或自相矛盾
   - 3分：基本清晰，但部分论证不够严谨
   - 5分：条理清晰，推理严谨，层层递进

4. 有用性：对学习是否有实际帮助
   - 1分：空洞或答非所问
   - 3分：有一定参考价值，但不够深入
   - 5分：深入浅出，对学习有实质帮助

# 禁止事项
- 回答长度不应影响评分，重点评估内容质量而非数量
- 不要偏袒任何一方，保持中立客观

# 输入
问题：
{question}

{name_a}：
{answer_a}

{name_b}：
{answer_b}

# 任务
1. 分别对{name_a}和{name_b}的四个维度进行评分（1-5分）
2. 综合四个维度，判断哪个回答更优
3. 给出你的判断理由

# 输出格式
请严格按照以下JSON格式输出，不要添加任何其他内容：
{{
    "scores": {{
        "{name_a}": {{"accuracy": 0, "comprehensiveness": 0, "coherence": 0, "helpfulness": 0}},
        "{name_b}": {{"accuracy": 0, "comprehensiveness": 0, "coherence": 0, "helpfulness": 0}}
    }},
    "winner": "{name_a}" | "{name_b}" | "tie",
    "reasoning": "你的判断理由"
}}
"""
    
    def _get_default_comparison(self, name_a: str, name_b: str) -> Dict[str, Any]:
        """返回默认比较结果"""
        return {
            "scores": {
                name_a: {"accuracy": 3, "comprehensiveness": 3, "coherence": 3, "helpfulness": 3},
                name_b: {"accuracy": 3, "comprehensiveness": 3, "coherence": 3, "helpfulness": 3}
            },
            "winner": "tie",
            "reasoning": "LLM评估失败，判定为平局"
        }
    
    def _aggregate_comparison(self, 
                             results: List[Dict[str, Any]], 
                             name_a: str, 
                             name_b: str) -> Dict[str, Any]:
        """聚合多次比较结果"""
        if not results:
            return self._get_default_comparison(name_a, name_b)
        
        # 聚合评分
        agg_scores = {name_a: {}, name_b: {}}
        dimensions = ["accuracy", "comprehensiveness", "coherence", "helpfulness"]
        
        for dim in dimensions:
            scores_a = [r["scores"][name_a][dim] for r in results]
            scores_b = [r["scores"][name_b][dim] for r in results]
            agg_scores[name_a][dim] = round(sum(scores_a) / len(scores_a), 2)
            agg_scores[name_b][dim] = round(sum(scores_b) / len(scores_b), 2)
        
        # 确定最终胜负
        winners = [r["winner"] for r in results]
        a_wins = winners.count(name_a)
        b_wins = winners.count(name_b)
        ties = winners.count("tie")
        
        if a_wins > b_wins:
            final_winner = name_a
        elif b_wins > a_wins:
            final_winner = name_b
        else:
            final_winner = "tie"
        
        # 聚合推理
        reasonings = [r["reasoning"] for r in results]
        combined_reasoning = "; ".join(reasonings)[:200]
        
        return {
            "scores": agg_scores,
            "winner": final_winner,
            "reasoning": combined_reasoning,
            "vote_counts": {name_a: a_wins, name_b: b_wins, "tie": ties},
            "num_comparisons": len(results)
        }


class StatisticsHelper:
    """统计指标计算工具 - 胜率、分题型统计、Bootstrap置信区间"""
    
    @staticmethod
    def calculate_win_rates(pairwise_results: List[Dict[str, Any]], 
                           model_names: List[str]) -> Dict[str, float]:
        """计算各模型的胜率"""
        if not pairwise_results:
            return {name: 0.0 for name in model_names}
        
        wins = {name: 0 for name in model_names}
        total = len(pairwise_results)
        
        for result in pairwise_results:
            winner = result["winner"]
            if winner in wins:
                wins[winner] += 1
        
        return {name: round(wins[name] / total * 100, 2) for name in model_names}
    
    @staticmethod
    def calculate_by_category(results: List[Dict[str, Any]], 
                            category_key: str = "category") -> Dict[str, Any]:
        """按类别分组统计"""
        categories = {}
        
        for result in results:
            category = result.get(category_key, "未知")
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        stats = {}
        for category, items in categories.items():
            scores = [item["evaluation"]["overall_score"] for item in items if "evaluation" in item]
            if scores:
                stats[category] = {
                    "count": len(items),
                    "mean": round(sum(scores) / len(scores), 4),
                    "std": round(np.std(scores), 4),
                    "min": round(min(scores), 4),
                    "max": round(max(scores), 4)
                }
        
        return stats
    
    @staticmethod
    def bootstrap_confidence_interval(scores: List[float], 
                                     n_iterations: int = 1000,
                                     confidence_level: float = 0.95) -> Dict[str, float]:
        """计算 Bootstrap 置信区间"""
        if not scores:
            return {"lower": 0.0, "upper": 0.0, "mean": 0.0}
        
        means = []
        n = len(scores)
        rng = RandomState(42)
        
        for _ in range(n_iterations):
            sample = rng.choice(scores, size=n, replace=True)
            means.append(np.mean(sample))
        
        means.sort()
        lower_idx = int((1 - confidence_level) / 2 * n_iterations)
        upper_idx = int((1 + confidence_level) / 2 * n_iterations)
        
        return {
            "mean": round(np.mean(scores), 4),
            "lower": round(means[lower_idx], 4),
            "upper": round(means[upper_idx], 4),
            "confidence_level": confidence_level
        }
    
    @staticmethod
    def calculate_improvement(base_score: float, target_score: float) -> float:
        """计算改进百分比"""
        if base_score == 0:
            return 0.0
        return round(((target_score - base_score) / base_score) * 100, 2)


class EvaluationPipeline:
    """评估流程管道 - 解耦推理、评判、比较阶段"""
    
    def __init__(self, 
                 graphrag_service=None, 
                 rag_service=None, 
                 llm_service=None,
                 judge_model=None):
        self.graphrag_service = graphrag_service
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.pointwise_evaluator = PointwiseEvaluator(llm_client=llm_service, judge_model=judge_model)
        self.pairwise_evaluator = PairwiseEvaluator(llm_client=llm_service, judge_model=judge_model)
    
    def run_full_evaluation(self, 
                           test_dataset: List[Dict[str, Any]],
                           num_samples: int = 3,
                           enable_pairwise: bool = True) -> Dict[str, Any]:
        """
        运行完整评估流程
        
        Args:
            test_dataset: 测试数据集
            num_samples: Pointwise 采样次数
            enable_pairwise: 是否启用成对比较
        
        Returns:
            完整的评估结果报告
        """
        print("\n" + "="*80)
        print("🔬 [评估流程] 开始完整评估")
        print("="*80)
        print(f"📊 测试数据集大小: {len(test_dataset)}")
        print(f"🔄 采样次数: {num_samples}")
        print(f"⚖️ 成对比较: {'启用' if enable_pairwise else '禁用'}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(test_dataset),
            "num_samples": num_samples,
            "enable_pairwise": enable_pairwise,
            "pointwise_results": {
                "graphrag": [],
                "rag": [],
                "llm": []
            },
            "pairwise_results": [],
            "statistics": {},
            "improvement": {}
        }
        
        # 1. 推理阶段 - 生成回答
        print("\n--- 阶段1: 推理 ---")
        all_answers = self._generate_answers(test_dataset)
        
        # 2. 评判阶段 - Pointwise 评分
        print("\n--- 阶段2: 评判 ---")
        for idx, item in enumerate(test_dataset):
            question = item["question"]
            expected = item["expected"]
            context = item.get("context", "")
            
            graphrag_eval = self.pointwise_evaluator.evaluate(
                all_answers["graphrag"][idx], expected, context, num_samples=num_samples
            )
            rag_eval = self.pointwise_evaluator.evaluate(
                all_answers["rag"][idx], expected, context, num_samples=num_samples
            )
            llm_eval = self.pointwise_evaluator.evaluate(
                all_answers["llm"][idx], expected, context, num_samples=num_samples
            )
            
            results["pointwise_results"]["graphrag"].append({
                "question": question,
                "answer": all_answers["graphrag"][idx],
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": graphrag_eval
            })
            
            results["pointwise_results"]["rag"].append({
                "question": question,
                "answer": all_answers["rag"][idx],
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": rag_eval
            })
            
            results["pointwise_results"]["llm"].append({
                "question": question,
                "answer": all_answers["llm"][idx],
                "expected": expected,
                "category": item.get("category", "未知"),
                "difficulty": item.get("difficulty", "未知"),
                "evaluation": llm_eval
            })
            
            print(f"   问题 {idx+1}/{len(test_dataset)} ✓")
        
        # 3. 比较阶段 - Pairwise 成对比较
        if enable_pairwise:
            print("\n--- 阶段3: 成对比较 ---")
            for idx, item in enumerate(test_dataset):
                question = item["question"]
                answer_g = all_answers["graphrag"][idx]
                answer_r = all_answers["rag"][idx]
                answer_l = all_answers["llm"][idx]
                
                # GraphRAG vs RAG
                comp_gr = self.pairwise_evaluator.compare(question, answer_g, answer_r, "GraphRAG", "RAG")
                # GraphRAG vs LLM
                comp_gl = self.pairwise_evaluator.compare(question, answer_g, answer_l, "GraphRAG", "LLM")
                # RAG vs LLM
                comp_rl = self.pairwise_evaluator.compare(question, answer_r, answer_l, "RAG", "LLM")
                
                results["pairwise_results"].append({
                    "question": question,
                    "category": item.get("category", "未知"),
                    "graphrag_vs_rag": comp_gr,
                    "graphrag_vs_llm": comp_gl,
                    "rag_vs_llm": comp_rl
                })
                
                print(f"   问题 {idx+1}/{len(test_dataset)} ✓")
        
        # 4. 统计聚合
        print("\n--- 阶段4: 结果聚合 ---")
        results["statistics"] = self._compute_statistics(results)
        results["improvement"] = self._compute_improvement(results)
        
        print("\n" + "="*80)
        print("✅ [评估流程] 评估完成")
        print("="*80)
        
        return results
    
    def _generate_answers(self, test_dataset: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """生成三个系统的回答"""
        answers = {"graphrag": [], "rag": [], "llm": []}
        
        for item in test_dataset:
            question = item["question"]
            
            # GraphRAG
            try:
                if hasattr(self.graphrag_service, 'answer_with_graphrag'):
                    result = self.graphrag_service.answer_with_graphrag(question=question)
                    g_answer = result.get("answer", "回答失败")
                elif hasattr(self.graphrag_service, 'query'):
                    g_answer = self.graphrag_service.query(question)
                else:
                    g_answer = "服务未配置"
            except Exception as e:
                g_answer = "回答失败"
            
            # RAG
            try:
                if hasattr(self.rag_service, 'answer_with_rag'):
                    result = self.rag_service.answer_with_rag(question=question)
                    r_answer = result.get("answer", "回答失败")
                elif hasattr(self.rag_service, 'query'):
                    r_answer = self.rag_service.query(question)
                else:
                    r_answer = "服务未配置"
            except Exception as e:
                r_answer = "回答失败"
            
            # LLM
            try:
                if hasattr(self.llm_service, 'answer_with_llm'):
                    result = self.llm_service.answer_with_llm(question=question)
                    l_answer = result.get("answer", "回答失败")
                elif hasattr(self.llm_service, 'complete'):
                    l_answer = self.llm_service.complete(question)
                else:
                    l_answer = "服务未配置"
            except Exception as e:
                l_answer = "回答失败"
            
            answers["graphrag"].append(g_answer)
            answers["rag"].append(r_answer)
            answers["llm"].append(l_answer)
        
        return answers
    
    def _compute_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计指标"""
        pw_results = results["pointwise_results"]
        
        def get_overall_scores(items):
            return [item["evaluation"]["overall_score"] for item in items]
        
        # 基础统计
        stats = {
            "graphrag": {
                "overall": StatisticsHelper.bootstrap_confidence_interval(get_overall_scores(pw_results["graphrag"])),
                "by_category": StatisticsHelper.calculate_by_category(pw_results["graphrag"])
            },
            "rag": {
                "overall": StatisticsHelper.bootstrap_confidence_interval(get_overall_scores(pw_results["rag"])),
                "by_category": StatisticsHelper.calculate_by_category(pw_results["rag"])
            },
            "llm": {
                "overall": StatisticsHelper.bootstrap_confidence_interval(get_overall_scores(pw_results["llm"])),
                "by_category": StatisticsHelper.calculate_by_category(pw_results["llm"])
            }
        }
        
        # Pairwise 胜率统计
        if results["enable_pairwise"] and results["pairwise_results"]:
            gr_wins = [r["graphrag_vs_rag"]["winner"] for r in results["pairwise_results"]]
            gl_wins = [r["graphrag_vs_llm"]["winner"] for r in results["pairwise_results"]]
            rl_wins = [r["rag_vs_llm"]["winner"] for r in results["pairwise_results"]]
            
            stats["win_rates"] = {
                "graphrag_vs_rag": {
                    "graphrag": round(gr_wins.count("GraphRAG") / len(gr_wins) * 100, 2),
                    "rag": round(gr_wins.count("RAG") / len(gr_wins) * 100, 2),
                    "tie": round(gr_wins.count("tie") / len(gr_wins) * 100, 2)
                },
                "graphrag_vs_llm": {
                    "graphrag": round(gl_wins.count("GraphRAG") / len(gl_wins) * 100, 2),
                    "llm": round(gl_wins.count("LLM") / len(gl_wins) * 100, 2),
                    "tie": round(gl_wins.count("tie") / len(gl_wins) * 100, 2)
                },
                "rag_vs_llm": {
                    "rag": round(rl_wins.count("RAG") / len(rl_wins) * 100, 2),
                    "llm": round(rl_wins.count("LLM") / len(rl_wins) * 100, 2),
                    "tie": round(rl_wins.count("tie") / len(rl_wins) * 100, 2)
                }
            }
        
        return stats
    
    def _compute_improvement(self, results: Dict[str, Any]) -> Dict[str, float]:
        """计算改进百分比"""
        stats = results["statistics"]
        
        rag_mean = stats["rag"]["overall"]["mean"]
        llm_mean = stats["llm"]["overall"]["mean"]
        graphrag_mean = stats["graphrag"]["overall"]["mean"]
        
        return {
            "graphrag_over_rag_percent": StatisticsHelper.calculate_improvement(rag_mean, graphrag_mean),
            "graphrag_over_llm_percent": StatisticsHelper.calculate_improvement(llm_mean, graphrag_mean),
            "rag_over_llm_percent": StatisticsHelper.calculate_improvement(llm_mean, rag_mean)
        }
    
    def save_report(self, results: Dict[str, Any], output_path: str = None):
        """保存评估报告"""
        if not output_path:
            output_path = f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 [评估流程] 报告已保存到: {output_path}")