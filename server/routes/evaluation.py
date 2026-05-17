"""Evaluation API routes for quality analysis."""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from evaluation import (
    PointwiseEvaluator,
    PairwiseEvaluator,
    EvaluationPipeline
)
from services.qa_service import qa_service
from utils.logger import get_logger

logger = get_logger("routes.evaluation")

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class AnswerEvaluationRequest(BaseModel):
    """Request model for answer quality evaluation."""
    question: str
    expected_answer: Optional[str] = None
    num_samples: int = 3


class AnswerEvaluationResponse(BaseModel):
    """Response model for answer quality evaluation."""
    success: bool
    question: str
    graphrag_answer: str
    rag_answer: str
    llm_answer: str
    evaluation: Dict[str, Any]
    improvement: Dict[str, float]
    timing: Optional[Dict[str, float]] = None
    pairwise: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None


class BatchEvaluationRequest(BaseModel):
    """Request model for batch evaluation."""
    questions: List[Dict[str, Any]]
    num_samples: int = 3
    enable_pairwise: bool = True


class BatchEvaluationResponse(BaseModel):
    """Response model for batch evaluation."""
    success: bool
    results: Dict[str, Any]


class PairwiseCompareRequest(BaseModel):
    """Request model for pairwise comparison."""
    question: str
    answer_a: str
    answer_b: str
    model_a_name: str = "模型A"
    model_b_name: str = "模型B"
    enable_position_swap: bool = True


class PairwiseCompareResponse(BaseModel):
    """Response model for pairwise comparison."""
    success: bool
    question: str
    comparison: Dict[str, Any]


@router.post("/answer", response_model=AnswerEvaluationResponse)
async def evaluate_answer_quality(request: AnswerEvaluationRequest):
    """
    Evaluate answer quality by comparing GraphRAG, RAG, and LLM responses.
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_evaluate_answer, request)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[评估服务] 回答质量评估失败: {e}")
        logger.debug(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"回答质量评估失败: {str(e)}")


def _save_evaluation_report(
    question: str,
    expected_answer: str,
    graphrag_answer: str,
    rag_answer: str,
    llm_answer: str,
    evaluation: Dict[str, Any],
    improvement: Dict[str, float],
    timing: Dict[str, float],
    pairwise_stats: Dict[str, Any]
):
    """将单次评估结果保存为JSON报告文件到 data/ 目录"""
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    import re
    safe_question = re.sub(r'[\\/:*?"<>|]', '', question[:30].replace(" ", "_"))
    if not safe_question:
        safe_question = "evaluation"
    filename = f"eval_{timestamp}_{safe_question}.json"
    filepath = data_dir / filename
    
    report = {
        "report_meta": {
            "generated_at": datetime.now().isoformat(),
            "type": "single_question_evaluation",
            "question": question,
            "expected_answer": expected_answer or "未提供参考答案",
            "num_samples": 3
        },
        "answers": {
            "graphrag": graphrag_answer,
            "rag": rag_answer,
            "llm": llm_answer
        },
        "scores": {
            "graphrag": {
                "overall_score": evaluation["graphrag"]["overall_score"],
                "automatic_score": evaluation["graphrag"].get("automatic", {}).get("score", 0),
                "llm_judge": evaluation["graphrag"].get("llm_judge", {}),
                "info_credibility": evaluation["graphrag"].get("info_credibility", 0)
            },
            "rag": {
                "overall_score": evaluation["rag"]["overall_score"],
                "automatic_score": evaluation["rag"].get("automatic", {}).get("score", 0),
                "llm_judge": evaluation["rag"].get("llm_judge", {}),
                "info_credibility": evaluation["rag"].get("info_credibility", 0)
            },
            "llm": {
                "overall_score": evaluation["llm"]["overall_score"],
                "automatic_score": evaluation["llm"].get("automatic", {}).get("score", 0),
                "llm_judge": evaluation["llm"].get("llm_judge", {}),
                "info_credibility": evaluation["llm"].get("info_credibility", 0)
            }
        },
        "improvement_percent": improvement,
        "timing": timing,
        "pairwise": {
            "graphrag_vs_rag": {
                "winner": pairwise_stats["graphrag_vs_rag"]["winner"],
                "vote_counts": pairwise_stats["graphrag_vs_rag"]["vote_counts"]
            },
            "graphrag_vs_llm": {
                "winner": pairwise_stats["graphrag_vs_llm"]["winner"],
                "vote_counts": pairwise_stats["graphrag_vs_llm"]["vote_counts"]
            },
            "rag_vs_llm": {
                "winner": pairwise_stats["rag_vs_llm"]["winner"],
                "vote_counts": pairwise_stats["rag_vs_llm"]["vote_counts"]
            }
        }
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"[评估服务] 报告已保存: {filepath}")


def _sync_evaluate_answer(request: AnswerEvaluationRequest) -> AnswerEvaluationResponse:
    """同步执行回答质量评估（在线程池中并行运行）"""
    _total_start = time.time()
    logger.info("\n" + "="*80)
    logger.info("[评估服务] 开始评估回答质量（并行模式）")
    logger.info(f"问题: {request.question}")
    logger.info(f"采样次数: {request.num_samples}")
    logger.info("="*80)
    
    logger.info("[评估服务] 阶段 1/2: 并行获取三种回答...")
    _phase1_start = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        submit_times = {}
        name_to_future = {}
        
        submit_times["graphrag"] = time.time()
        name_to_future["graphrag"] = executor.submit(qa_service.answer_with_graphrag, question=request.question)
        submit_times["rag"] = time.time()
        name_to_future["rag"] = executor.submit(qa_service.answer_with_rag, question=request.question)
        submit_times["llm"] = time.time()
        name_to_future["llm"] = executor.submit(qa_service.answer_with_llm, question=request.question)
        
        results_map = {}
        times_map = {}
        for future in as_completed(name_to_future.values()):
            for name, f in name_to_future.items():
                if f is future:
                    results_map[name] = future.result()
                    times_map[name] = round(time.time() - submit_times[name], 3)
                    break
    
    graphrag_result = results_map["graphrag"]
    graphrag_time = times_map["graphrag"]
    rag_result = results_map["rag"]
    rag_time = times_map["rag"]
    llm_result = results_map["llm"]
    llm_time = times_map["llm"]
    
    graphrag_answer = graphrag_result.get("answer", "回答失败")
    graphrag_context = graphrag_result.get("context_snippet", None)
    graphrag_used_context = graphrag_result.get("used_context", False)
    graphrag_entities = graphrag_result.get("entities", []) if "entities" in graphrag_result else []
    logger.info(f"[评估服务] GraphRAG 回答完成，长度: {len(graphrag_answer)} 字符")
    
    rag_answer = rag_result.get("answer", "回答失败")
    rag_context = rag_result.get("context_snippet", None)
    rag_used_context = rag_result.get("used_context", False)
    rag_vector_results = rag_result.get("vector_results", []) if "vector_results" in rag_result else []
    logger.info(f"[评估服务] RAG 回答完成，长度: {len(rag_answer)} 字符")
    
    llm_answer = llm_result.get("answer", "回答失败")
    logger.info(f"[评估服务] LLM 回答完成，长度: {len(llm_answer)} 字符")
    
    evaluator = PointwiseEvaluator(llm_client=qa_service)
    
    logger.info("[评估服务] 阶段 2/3: 并行评估三种回答质量...")
    _phase2_start = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_ge = executor.submit(
            evaluator.evaluate,
            graphrag_answer,
            request.expected_answer or "未提供参考答案",
            graphrag_context or request.question,
            num_samples=request.num_samples,
            source_type="graphrag",
            used_context=graphrag_used_context
        )
        future_re = executor.submit(
            evaluator.evaluate,
            rag_answer,
            request.expected_answer or "未提供参考答案",
            rag_context or request.question,
            num_samples=request.num_samples,
            source_type="rag",
            used_context=rag_used_context
        )
        future_le = executor.submit(
            evaluator.evaluate,
            llm_answer,
            request.expected_answer or "未提供参考答案",
            request.question,
            num_samples=request.num_samples,
            source_type="llm",
            used_context=False
        )
        
        graphrag_eval = future_ge.result()
        rag_eval = future_re.result()
        llm_eval = future_le.result()
    
    logger.info(f"[评估服务] GraphRAG 评估完成，得分: {graphrag_eval['overall_score']:.4f}")
    logger.info(f"[评估服务] RAG 评估完成，得分: {rag_eval['overall_score']:.4f}")
    logger.info(f"[评估服务] LLM 评估完成，得分: {llm_eval['overall_score']:.4f}")
    logger.info(f"[评估服务] 阶段 2 耗时: {round(time.time() - _phase2_start, 3)}秒")
    
    # 阶段 3: Pairwise 成对比较（位置交换策略消除偏差）
    logger.info("[评估服务] 阶段 3/3: 成对比较三种回答...")
    _pairwise_start = time.time()
    pairwise_evaluator = PairwiseEvaluator(llm_client=qa_service)
    
    pairwise_results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_gr = executor.submit(
            pairwise_evaluator.compare,
            request.question, graphrag_answer, rag_answer, "GraphRAG", "RAG",
            True
        )
        future_gl = executor.submit(
            pairwise_evaluator.compare,
            request.question, graphrag_answer, llm_answer, "GraphRAG", "LLM",
            True
        )
        future_rl = executor.submit(
            pairwise_evaluator.compare,
            request.question, rag_answer, llm_answer, "RAG", "LLM",
            True
        )
        
        pairwise_results["graphrag_vs_rag"] = future_gr.result()
        pairwise_results["graphrag_vs_llm"] = future_gl.result()
        pairwise_results["rag_vs_llm"] = future_rl.result()
    
    pairwise_time = round(time.time() - _pairwise_start, 3)
    logger.info(f"[评估服务] 成对比较完成，耗时: {pairwise_time}秒")
    
    # 计算胜率统计
    def _count_wins(results_dict, key_a, key_b):
        comp = results_dict[key_b]
        winner = comp["winner"]
        return {
            key_a: float(comp["vote_counts"].get(key_a, 0)),
            key_b: float(comp["vote_counts"].get(key_b, 0)),
            "tie": float(comp["vote_counts"].get("tie", 0))
        }
    
    pairwise_stats = {
        "graphrag_vs_rag": {
            "scores": pairwise_results["graphrag_vs_rag"]["scores"],
            "winner": pairwise_results["graphrag_vs_rag"]["winner"],
            "reasoning": pairwise_results["graphrag_vs_rag"]["reasoning"],
            "vote_counts": pairwise_results["graphrag_vs_rag"]["vote_counts"],
            "num_comparisons": pairwise_results["graphrag_vs_rag"]["num_comparisons"]
        },
        "graphrag_vs_llm": {
            "scores": pairwise_results["graphrag_vs_llm"]["scores"],
            "winner": pairwise_results["graphrag_vs_llm"]["winner"],
            "reasoning": pairwise_results["graphrag_vs_llm"]["reasoning"],
            "vote_counts": pairwise_results["graphrag_vs_llm"]["vote_counts"],
            "num_comparisons": pairwise_results["graphrag_vs_llm"]["num_comparisons"]
        },
        "rag_vs_llm": {
            "scores": pairwise_results["rag_vs_llm"]["scores"],
            "winner": pairwise_results["rag_vs_llm"]["winner"],
            "reasoning": pairwise_results["rag_vs_llm"]["reasoning"],
            "vote_counts": pairwise_results["rag_vs_llm"]["vote_counts"],
            "num_comparisons": pairwise_results["rag_vs_llm"]["num_comparisons"]
        }
    }
    
    total_time = round(time.time() - _total_start, 3)
    timing = {
        "graphrag_gen_time": graphrag_time,
        "rag_gen_time": rag_time,
        "llm_gen_time": llm_time,
        "pairwise_time": pairwise_time,
        "total_time": total_time
    }
    
    graphrag_score = graphrag_eval["overall_score"]
    rag_score = rag_eval["overall_score"]
    llm_score = llm_eval["overall_score"]
    
    improvement = {
        "graphrag_over_rag_percent": ((graphrag_score - rag_score) / rag_score * 100) if rag_score > 0 else 0,
        "graphrag_over_llm_percent": ((graphrag_score - llm_score) / llm_score * 100) if llm_score > 0 else 0,
        "rag_over_llm_percent": ((rag_score - llm_score) / llm_score * 100) if llm_score > 0 else 0
    }
    
    evaluation = {
        "graphrag": graphrag_eval,
        "rag": rag_eval,
        "llm": llm_eval,
        "statistics": {
            "graphrag_score": graphrag_score,
            "rag_score": rag_score,
            "llm_score": llm_score
        }
    }
    
    logger.info("\n[评估服务] 评估完成")
    logger.info(f"   GraphRAG 评分: {graphrag_score:.4f}  |  生成耗时: {graphrag_time}秒")
    logger.info(f"   RAG 评分: {rag_score:.4f}  |  生成耗时: {rag_time}秒")
    logger.info(f"   LLM 评分: {llm_score:.4f}  |  生成耗时: {llm_time}秒")
    logger.info(f"   总耗时: {total_time}秒")
    logger.info(f"   Pairwise 胜者: GRvsRAG={pairwise_results['graphrag_vs_rag']['winner']}, GRvsLLM={pairwise_results['graphrag_vs_llm']['winner']}, RAGvsLLM={pairwise_results['rag_vs_llm']['winner']}")
    logger.info("="*80 + "\n")
    
    _save_evaluation_report(
        question=request.question,
        expected_answer=request.expected_answer or "未提供参考答案",
        graphrag_answer=graphrag_answer,
        rag_answer=rag_answer,
        llm_answer=llm_answer,
        evaluation=evaluation,
        improvement=improvement,
        timing=timing,
        pairwise_stats=pairwise_stats
    )
    
    return AnswerEvaluationResponse(
        success=True,
        question=request.question,
        graphrag_answer=graphrag_answer,
        rag_answer=rag_answer,
        llm_answer=llm_answer,
        evaluation=evaluation,
        improvement=improvement,
        timing=timing,
        pairwise=pairwise_stats,
        trace={
            "graphrag": {
                "context_snippet": graphrag_context,
                "used_context": graphrag_used_context,
                "entities": graphrag_entities
            },
            "rag": {
                "context_snippet": rag_context,
                "used_context": rag_used_context,
                "vector_results": rag_vector_results
            },
            "llm": {
                "context_snippet": None,
                "used_context": False,
                "note": "纯LLM回答，无外部信息来源"
            }
        }
    )


@router.post("/batch", response_model=BatchEvaluationResponse)
async def batch_evaluate(request: BatchEvaluationRequest):
    """
    Run batch evaluation on a dataset of questions.
    """
    try:
        if not request.questions or len(request.questions) == 0:
            raise HTTPException(status_code=400, detail="问题列表不能为空")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_batch_evaluate, request)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[评估服务] 批量评估失败: {e}")
        logger.debug(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"批量评估失败: {str(e)}")


def _sync_batch_evaluate(request: BatchEvaluationRequest) -> BatchEvaluationResponse:
    """同步执行批量评估（在线程池中运行）"""
    logger.info("\n" + "="*80)
    logger.info("[评估服务] 开始批量评估")
    logger.info(f"问题数量: {len(request.questions)}")
    logger.info(f"采样次数: {request.num_samples}")
    logger.info(f"成对比较: {'启用' if request.enable_pairwise else '禁用'}")
    logger.info("="*80)
    
    pipeline = EvaluationPipeline(
        graphrag_service=qa_service,
        rag_service=qa_service,
        llm_service=qa_service
    )
    
    results = pipeline.run_full_evaluation(
        request.questions,
        num_samples=request.num_samples,
        enable_pairwise=request.enable_pairwise
    )
    
    logger.info("\n[评估服务] 批量评估完成")
    logger.info("="*80 + "\n")
    
    return BatchEvaluationResponse(
        success=True,
        results=results
    )


@router.post("/pairwise", response_model=PairwiseCompareResponse)
async def pairwise_compare(request: PairwiseCompareRequest):
    """
    Compare two answers using Pairwise evaluation.
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        if not request.answer_a or not request.answer_b:
            raise HTTPException(status_code=400, detail="两个回答都不能为空")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_pairwise_compare, request)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[评估服务] 成对比较失败: {e}")
        logger.debug(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"成对比较失败: {str(e)}")


def _sync_pairwise_compare(request: PairwiseCompareRequest) -> PairwiseCompareResponse:
    """同步执行成对比较（在线程池中运行）"""
    logger.info("\n" + "="*80)
    logger.info("[评估服务] 开始成对比较")
    logger.info(f"问题: {request.question[:50]}...")
    logger.info(f"模型A: {request.model_a_name}, 模型B: {request.model_b_name}")
    logger.info(f"位置交换: {'启用' if request.enable_position_swap else '禁用'}")
    logger.info("="*80)
    
    evaluator = PairwiseEvaluator(llm_client=qa_service)
    
    comparison = evaluator.compare(
        question=request.question,
        answer_a=request.answer_a,
        answer_b=request.answer_b,
        model_a_name=request.model_a_name,
        model_b_name=request.model_b_name,
        enable_position_swap=request.enable_position_swap
    )
    
    logger.info(f"\n[评估服务] 比较完成")
    logger.info(f"   获胜方: {comparison['winner']}")
    logger.info("="*80 + "\n")
    
    return PairwiseCompareResponse(
        success=True,
        question=request.question,
        comparison=comparison
    )


@router.get("/health")
async def health_check():
    """Check if evaluation service is available."""
    return {
        "status": "healthy",
        "has_qa_service": qa_service is not None
    }


@router.get("/datasets")
async def list_datasets():
    """
    List available benchmark datasets.
    
    Returns:
        List of available datasets with metadata
    """
    import os
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    datasets = []
    
    if data_dir.exists():
        for file_path in data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    datasets.append({
                        "id": file_path.stem,
                        "filename": file_path.name,
                        "name": data.get("name", file_path.stem),
                        "version": data.get("version", "1.0.0"),
                        "description": data.get("description", ""),
                        "question_count": len(data.get("questions", [])),
                        "categories": data.get("categories", []),
                        "difficulty_levels": data.get("difficulty_levels", [])
                    })
            except Exception as e:
                logger.warning(f"Failed to load dataset {file_path}: {e}")
    
    return {"datasets": datasets}


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """
    Get a specific benchmark dataset.
    
    Args:
        dataset_id: Dataset identifier (filename without extension)
    
    Returns:
        Dataset content with all questions
    """
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    file_path = data_dir / f"{dataset_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"数据集 {dataset_id} 不存在")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            "success": True,
            "dataset": data
        }
    except Exception as e:
        logger.error(f"Failed to load dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"加载数据集失败: {str(e)}")


@router.post("/datasets/{dataset_id}/evaluate")
async def evaluate_dataset(
    dataset_id: str,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 10,
    num_samples: int = 1,
    enable_pairwise: bool = False
):
    """
    Run evaluation on a benchmark dataset.
    
    Args:
        dataset_id: Dataset identifier
        category: Filter by category (optional)
        difficulty: Filter by difficulty level (optional)
        limit: Maximum number of questions to evaluate
        num_samples: Number of LLM judge samples
        enable_pairwise: Enable pairwise comparison
    
    Returns:
        Evaluation results for the dataset
    """
    from pathlib import Path
    
    data_dir = Path(__file__).parent.parent.parent / "data"
    file_path = data_dir / f"{dataset_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"数据集 {dataset_id} 不存在")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        
        questions = dataset.get("questions", [])
        
        if category:
            questions = [q for q in questions if q.get("category") == category]
        
        if difficulty:
            questions = [q for q in questions if q.get("difficulty") == difficulty]
        
        questions = questions[:limit]
        
        if not questions:
            raise HTTPException(status_code=400, detail="没有符合条件的问题")
        
        logger.info("\n" + "="*80)
        logger.info(f"[评估服务] 开始数据集评估: {dataset_id}")
        logger.info(f"问题数量: {len(questions)}")
        logger.info(f"筛选条件: category={category}, difficulty={difficulty}")
        logger.info(f"采样次数: {num_samples}")
        logger.info("="*80)
        
        pipeline = EvaluationPipeline(
            graphrag_service=qa_service,
            rag_service=qa_service,
            llm_service=qa_service
        )
        
        test_data = [
            {
                "question": q["question"],
                "expected": q["expected_answer"],
                "category": q.get("category", "未知"),
                "difficulty": q.get("difficulty", "未知")
            }
            for q in questions
        ]
        
        results = pipeline.run_full_evaluation(
            test_data,
            num_samples=num_samples,
            enable_pairwise=enable_pairwise
        )
        
        logger.info("\n[评估服务] 数据集评估完成")
        logger.info("="*80 + "\n")
        
        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("name", dataset_id),
            "filters": {
                "category": category,
                "difficulty": difficulty
            },
            "questions_evaluated": len(questions),
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[评估服务] 数据集评估失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"数据集评估失败: {str(e)}")