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
        assert "length_adequacy" in result
        assert "word_overlap" in result
        assert "keyword_f1" in result
        assert "rouge_l" in result
        assert "score" in result
        assert 0 <= result["score"] <= 1

    def test_length_adequacy_bounded(self):
        """测试长度充分度值域在[0,1]"""
        evaluator = PointwiseEvaluator()
        score_short = evaluator._length_score("短", "这是一段很长的参考答案内容")
        score_equal = evaluator._length_score("这是一段等长的参考答案内容", "这是一段等长的参考答案内容")
        score_long = evaluator._length_score("这是一段非常非常长的预测回答内容超过了参考答案", "短参考")
        
        assert 0 <= score_short <= 1.0
        assert score_equal == 1.0
        assert score_long == 1.0
        assert score_short < score_equal

    def test_keyword_f1_symmetry(self):
        """测试关键词F1的对称性：F1(A,B) == F1(B,A)"""
        evaluator = PointwiseEvaluator()
        f1_ab = evaluator._keyword_f1("软件工程方法论", "软件工程项目管理")
        f1_ba = evaluator._keyword_f1("软件工程项目管理", "软件工程方法论")
        assert abs(f1_ab - f1_ba) < 0.001

    def test_keyword_f1_penalizes_stuffing(self):
        """测试关键词F1惩罚关键词堆砌：纯召回率不惩罚，但F1会"""
        evaluator = PointwiseEvaluator()
        pred = "软件 工程 质量 成本 效率 维护 需求 可靠性 测试 设计 架构 数据库 算法 网络"
        ref = "软件工程的目标是提高软件质量和可靠性"
        f1 = evaluator._keyword_f1(pred, ref)
        assert f1 < 1.0
    
    def test_information_credibility_no_context(self):
        """测试无外部知识上下文时信息可信度为低分"""
        evaluator = PointwiseEvaluator()
        score = evaluator._information_credibility(
            predicted="LLM回答", context="", used_context=False, source_type="llm"
        )
        assert score == 0.15

    def test_information_credibility_with_context(self):
        """测试有上下文时信息可信度根据overlap计算"""
        evaluator = PointwiseEvaluator()
        score = evaluator._information_credibility(
            predicted="知识图谱中的实体和关系",
            context="知识图谱中的实体和关系信息",
            used_context=True,
            source_type="graphrag"
        )
        assert 0.4 <= score <= 1.0

    def test_information_credibility_rag_with_context(self):
        """测试RAG有上下文时信息可信度与GraphRAG使用同一公式"""
        evaluator = PointwiseEvaluator()
        score = evaluator._information_credibility(
            predicted="文档检索的回答内容",
            context="检索到的文档片段内容",
            used_context=True,
            source_type="rag"
        )
        assert 0.4 <= score <= 1.0

    def test_information_credibility_no_context_graphrag(self):
        """测试GraphRAG未检索到上下文时信息可信度同样为低分"""
        evaluator = PointwiseEvaluator()
        score = evaluator._information_credibility(
            predicted="回答", context="", used_context=False, source_type="graphrag"
        )
        assert score == 0.15

    def test_information_credibility_same_formula(self):
        """测试同一公式对所有方法公平：相同输入得到相同输出"""
        evaluator = PointwiseEvaluator()
        predicted = "基于知识库的回答内容"
        context = "知识库中的回答内容参考"
        score_gr = evaluator._information_credibility(predicted, context, True, "graphrag")
        score_rag = evaluator._information_credibility(predicted, context, True, "rag")
        score_llm = evaluator._information_credibility(predicted, context, True, "llm")
        assert score_gr == score_rag == score_llm
    
    def test_overall_score_with_credibility(self):
        """测试综合评分包含信息可信度"""
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
            predicted="这是测试回答",
            expected="这是参考答案",
            context="上下文信息",
            num_samples=1,
            source_type="graphrag",
            used_context=True
        )
        
        assert "info_credibility" in result
        assert result["info_credibility"] >= 0.4
        assert result["overall_score"] > 0


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