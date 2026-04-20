"""
测试 LLM-as-a-Judge 评估模块
"""

import pytest
import json
from unittest.mock import Mock, MagicMock
from evaluation import (
    PointwiseEvaluator,
    PairwiseEvaluator,
    StatisticsHelper,
    EvaluationPipeline
)


class TestPointwiseEvaluator:
    """测试 PointwiseEvaluator 单回答评分器"""
    
    def test_evaluate_basic(self):
        """测试基本评估功能"""
        mock_llm = Mock()
        mock_llm.chat.return_value = json.dumps({
            "accuracy": 4,
            "completeness": 4,
            "relevance": 5,
            "expertise": 4,
            "explainability": 4,
            "overall": 4.2,
            "comment": "测试"
        })
        
        evaluator = PointwiseEvaluator(llm_client=mock_llm)
        result = evaluator.evaluate(
            predicted="这是一个测试回答",
            expected="这是参考答案",
            context="问题上下文",
            num_samples=1
        )
        
        assert "llm_judge" in result
        assert result["llm_judge"]["overall"] == 4.2
        assert result["llm_judge"]["accuracy"] == 4
        mock_llm.chat.assert_called_once()
    
    def test_multiple_samples(self):
        """测试多次采样功能"""
        mock_llm = Mock()
        mock_llm.chat.return_value = json.dumps({
            "accuracy": 4,
            "completeness": 4,
            "relevance": 5,
            "expertise": 4,
            "explainability": 4,
            "overall": 4.2,
            "comment": "测试"
        })
        
        evaluator = PointwiseEvaluator(llm_client=mock_llm)
        result = evaluator.evaluate(
            predicted="测试回答",
            expected="参考答案",
            num_samples=3
        )
        
        assert mock_llm.chat.call_count == 3
        assert "sample_std" in result["llm_judge"]
    
    def test_automatic_evaluation(self):
        """测试自动化指标评估"""
        evaluator = PointwiseEvaluator()
        result = evaluator._automatic_evaluation(
            predicted="这是测试回答",
            expected="这是测试回答"
        )
        
        assert "semantic_similarity" in result
        assert "rouge_l" in result
        assert "score" in result
        assert 0 <= result["score"] <= 1


class TestPairwiseEvaluator:
    """测试 PairwiseEvaluator 成对比较器"""
    
    def test_compare_basic(self):
        """测试基本比较功能"""
        mock_llm = Mock()
        mock_llm.chat.return_value = json.dumps({
            "scores": {
                "模型A": {"accuracy": 4, "comprehensiveness": 4, "coherence": 4, "helpfulness": 4},
                "模型B": {"accuracy": 3, "comprehensiveness": 3, "coherence": 3, "helpfulness": 3}
            },
            "winner": "模型A",
            "reasoning": "模型A更好"
        })
        
        evaluator = PairwiseEvaluator(llm_client=mock_llm)
        result = evaluator.compare(
            question="测试问题",
            answer_a="回答A",
            answer_b="回答B",
            model_a_name="模型A",
            model_b_name="模型B",
            enable_position_swap=False
        )
        
        assert result["winner"] == "模型A"
        assert "vote_counts" in result
        mock_llm.chat.assert_called_once()
    
    def test_position_swap(self):
        """测试位置交换功能"""
        mock_llm = Mock()
        mock_llm.chat.return_value = json.dumps({
            "scores": {
                "模型A": {"accuracy": 4, "comprehensiveness": 4, "coherence": 4, "helpfulness": 4},
                "模型B": {"accuracy": 3, "comprehensiveness": 3, "coherence": 3, "helpfulness": 3}
            },
            "winner": "模型A",
            "reasoning": "测试"
        })
        
        evaluator = PairwiseEvaluator(llm_client=mock_llm)
        result = evaluator.compare(
            question="测试问题",
            answer_a="回答A",
            answer_b="回答B",
            model_a_name="模型A",
            model_b_name="模型B",
            enable_position_swap=True
        )
        
        assert mock_llm.chat.call_count == 2
        assert result["num_comparisons"] == 2


class TestStatisticsHelper:
    """测试 StatisticsHelper 统计工具"""
    
    def test_calculate_win_rates(self):
        """测试胜率计算"""
        results = [
            {"winner": "A"},
            {"winner": "A"},
            {"winner": "B"},
            {"winner": "tie"}
        ]
        win_rates = StatisticsHelper.calculate_win_rates(results, ["A", "B"])
        
        assert win_rates["A"] == 50.0
        assert win_rates["B"] == 25.0
    
    def test_bootstrap_confidence_interval(self):
        """测试 Bootstrap 置信区间计算"""
        scores = [0.8, 0.85, 0.9, 0.82, 0.88]
        ci = StatisticsHelper.bootstrap_confidence_interval(scores)
        
        assert "mean" in ci
        assert "lower" in ci
        assert "upper" in ci
        assert ci["lower"] <= ci["mean"] <= ci["upper"]
    
    def test_calculate_by_category(self):
        """测试分题型统计"""
        results = [
            {"category": "记忆", "evaluation": {"overall_score": 0.8}},
            {"category": "记忆", "evaluation": {"overall_score": 0.9}},
            {"category": "推理", "evaluation": {"overall_score": 0.7}}
        ]
        stats = StatisticsHelper.calculate_by_category(results)
        
        assert "记忆" in stats
        assert "推理" in stats
        assert stats["记忆"]["count"] == 2
        assert stats["记忆"]["mean"] == 0.85


class TestEvaluationPipeline:
    """测试 EvaluationPipeline 评估流程"""
    
    def test_run_full_evaluation(self):
        """测试完整评估流程"""
        mock_graphrag = Mock()
        mock_rag = Mock()
        mock_llm = Mock()
        
        mock_graphrag.query.return_value = "GraphRAG回答"
        mock_rag.query.return_value = "RAG回答"
        mock_llm.complete.return_value = "LLM回答"
        mock_llm.chat.return_value = json.dumps({
            "accuracy": 4,
            "completeness": 4,
            "relevance": 4,
            "expertise": 4,
            "explainability": 4,
            "overall": 4.0,
            "comment": "测试"
        })
        
        pipeline = EvaluationPipeline(
            graphrag_service=mock_graphrag,
            rag_service=mock_rag,
            llm_service=mock_llm
        )
        
        test_dataset = [
            {"question": "测试问题", "expected": "参考答案", "category": "测试"}
        ]
        
        results = pipeline.run_full_evaluation(
            test_dataset,
            num_samples=1,
            enable_pairwise=False
        )
        
        assert "pointwise_results" in results
        assert "statistics" in results
        assert len(results["pointwise_results"]["graphrag"]) == 1
    
    def test_improvement_calculation(self):
        """测试改进百分比计算"""
        base = 0.7
        target = 0.84
        improvement = StatisticsHelper.calculate_improvement(base, target)
        
        assert improvement == 20.0  # (0.84-0.7)/0.7 * 100 = 20