"""Evaluation API routes for quality analysis."""
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from evaluation import (
    PointwiseEvaluator,
    PairwiseEvaluator,
    EvaluationPipeline
)
from services.qa_service import qa_service
from infra.neo4j_client import neo4j_client
from utils.logger import get_logger

logger = get_logger("routes.evaluation")

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class AnswerEvaluationRequest(BaseModel):
    """Request model for answer quality evaluation."""
    question: str
    expected_answer: Optional[str] = None
    num_samples: int = 1


class AnswerEvaluationResponse(BaseModel):
    """Response model for answer quality evaluation."""
    success: bool
    question: str
    graphrag_answer: str
    rag_answer: str
    llm_answer: str
    evaluation: Dict[str, Any]
    improvement: Dict[str, float]
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
    
    Args:
        question: User question to evaluate
        expected_answer: Optional expected answer for evaluation
        num_samples: Number of samples for LLM judge (default: 1)
    
    Returns:
        Comparison results including answers from all three methods and evaluation metrics
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        logger.info("\n" + "="*80)
        logger.info("[评估服务] 开始评估回答质量")
        logger.info(f"问题: {request.question}")
        logger.info(f"采样次数: {request.num_samples}")
        logger.info("="*80)
        
        logger.info("[评估服务] 步骤 1/6: 获取 GraphRAG 回答...")
        graphrag_result = qa_service.answer_with_graphrag(question=request.question)
        graphrag_answer = graphrag_result.get("answer", "回答失败")
        graphrag_context = graphrag_result.get("context_snippet", None)
        graphrag_used_context = graphrag_result.get("used_context", False)
        graphrag_entities = graphrag_result.get("entities", []) if "entities" in graphrag_result else []
        logger.info(f"[评估服务] GraphRAG 回答完成，长度: {len(graphrag_answer)} 字符")
        
        logger.info("[评估服务] 步骤 2/6: 获取 RAG 回答...")
        rag_result = qa_service.answer_with_rag(question=request.question)
        rag_answer = rag_result.get("answer", "回答失败")
        rag_context = rag_result.get("context_snippet", None)
        rag_used_context = rag_result.get("used_context", False)
        rag_vector_results = rag_result.get("vector_results", []) if "vector_results" in rag_result else []
        logger.info(f"[评估服务] RAG 回答完成，长度: {len(rag_answer)} 字符")
        
        logger.info("[评估服务] 步骤 3/6: 获取 LLM 回答...")
        llm_result = qa_service.answer_with_llm(question=request.question)
        llm_answer = llm_result.get("answer", "回答失败")
        logger.info(f"[评估服务] LLM 回答完成，长度: {len(llm_answer)} 字符")
        
        evaluator = PointwiseEvaluator(llm_client=qa_service)
        
        logger.info("[评估服务] 步骤 4/6: 评估 GraphRAG 回答质量...")
        graphrag_eval = evaluator.evaluate(
            graphrag_answer, 
            request.expected_answer or "未提供参考答案", 
            request.question,
            num_samples=request.num_samples
        )
        logger.info(f"[评估服务] GraphRAG 评估完成，得分: {graphrag_eval['overall_score']:.4f}")
        
        logger.info("[评估服务] 步骤 5/6: 评估 RAG 回答质量...")
        rag_eval = evaluator.evaluate(
            rag_answer, 
            request.expected_answer or "未提供参考答案", 
            request.question,
            num_samples=request.num_samples
        )
        logger.info(f"[评估服务] RAG 评估完成，得分: {rag_eval['overall_score']:.4f}")
        
        logger.info("[评估服务] 步骤 6/6: 评估 LLM 回答质量...")
        llm_eval = evaluator.evaluate(
            llm_answer, 
            request.expected_answer or "未提供参考答案", 
            request.question,
            num_samples=request.num_samples
        )
        logger.info(f"[评估服务] LLM 评估完成，得分: {llm_eval['overall_score']:.4f}")
        
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
        logger.info(f"   GraphRAG 评分: {graphrag_score:.4f}")
        logger.info(f"   RAG 评分: {rag_score:.4f}")
        logger.info(f"   LLM 评分: {llm_score:.4f}")
        logger.info("="*80 + "\n")
        
        return AnswerEvaluationResponse(
            success=True,
            question=request.question,
            graphrag_answer=graphrag_answer,
            rag_answer=rag_answer,
            llm_answer=llm_answer,
            evaluation=evaluation,
            improvement=improvement,
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
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[评估服务] 回答质量评估失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"回答质量评估失败: {str(e)}")


@router.post("/batch", response_model=BatchEvaluationResponse)
async def batch_evaluate(request: BatchEvaluationRequest):
    """
    Run batch evaluation on a dataset of questions.
    
    Args:
        questions: List of question items with question, expected_answer, category, difficulty
        num_samples: Number of samples for LLM judge (default: 3)
        enable_pairwise: Enable pairwise comparison (default: True)
    
    Returns:
        Comprehensive evaluation report with statistics and improvement metrics
    """
    try:
        if not request.questions or len(request.questions) == 0:
            raise HTTPException(status_code=400, detail="问题列表不能为空")
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[评估服务] 批量评估失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"批量评估失败: {str(e)}")


@router.post("/pairwise", response_model=PairwiseCompareResponse)
async def pairwise_compare(request: PairwiseCompareRequest):
    """
    Compare two answers using Pairwise evaluation.
    
    Args:
        question: The question being answered
        answer_a: First answer to compare
        answer_b: Second answer to compare
        model_a_name: Name for first model (default: "模型A")
        model_b_name: Name for second model (default: "模型B")
        enable_position_swap: Enable position swap to mitigate position bias (default: True)
    
    Returns:
        Comparison result with scores, winner, and reasoning
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        if not request.answer_a or not request.answer_b:
            raise HTTPException(status_code=400, detail="两个回答都不能为空")
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[评估服务] 成对比较失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"成对比较失败: {str(e)}")


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