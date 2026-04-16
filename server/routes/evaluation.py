"""Evaluation API routes for quality analysis."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from evaluation import GraphQualityEvaluator, ComparativeExperiment
from services.qa_service import qa_service
from infra.neo4j_client import neo4j_client
from utils.logger import get_logger

logger = get_logger("routes.evaluation")

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class AnswerEvaluationRequest(BaseModel):
    """Request model for answer quality evaluation."""
    question: str
    expected_answer: Optional[str] = None


class AnswerEvaluationResponse(BaseModel):
    """Response model for answer quality evaluation."""
    success: bool
    question: str
    graphrag_answer: str
    rag_answer: str
    llm_answer: str
    evaluation: Dict[str, Any]
    improvement: Dict[str, float]


@router.get("/graph", response_model=Dict[str, Any])
async def evaluate_graph_quality():
    """
    Evaluate the quality of the knowledge graph.
    
    Returns:
        Graph quality metrics including structural quality, content quality, 
        construction efficiency, and overall score.
    """
    try:
        evaluator = GraphQualityEvaluator(neo4j_client)
        result = evaluator.evaluate()
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        with open("evaluation_error.log", "w", encoding="utf-8") as f:
            f.write(f"错误: {e}\n")
            f.write(f"详细错误:\n{error_details}")
        logger.error(f"[评估服务] 图谱质量评估失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"图谱质量评估失败: {str(e)}")


@router.post("/answer", response_model=AnswerEvaluationResponse)
async def evaluate_answer_quality(request: AnswerEvaluationRequest):
    """
    Evaluate answer quality by comparing GraphRAG, RAG, and LLM responses.
    
    Args:
        question: User question to evaluate
        expected_answer: Optional expected answer for evaluation
    
    Returns:
        Comparison results including answers from all three methods and evaluation metrics
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        logger.info("\n" + "="*80)
        logger.info("[评估服务] 开始评估回答质量")
        logger.info(f"问题: {request.question}")
        logger.info("="*80)
        
        # Get GraphRAG answer (with knowledge graph)
        logger.info("   获取 GraphRAG 回答...")
        graphrag_result = qa_service.answer_question(
            question=request.question,
            use_kg=True
        )
        graphrag_answer = graphrag_result.get("answer", "回答失败")
        
        # Get RAG answer (without knowledge graph)
        logger.info("   获取 RAG 回答...")
        rag_result = qa_service.answer_question(
            question=request.question,
            use_kg=False
        )
        rag_answer = rag_result.get("answer", "回答失败")
        
        # Get LLM answer (direct call)
        logger.info("   获取 LLM 回答...")
        llm_result = qa_service.answer_question(
            question=request.question,
            use_kg=False
        )
        llm_answer = llm_result.get("answer", "回答失败")
        
        # Prepare test dataset for evaluation
        test_item = {
            "question": request.question,
            "expected": request.expected_answer or "未提供参考答案",
            "category": "evaluation",
            "difficulty": "未知"
        }
        
        # Create experiment and evaluate
        experiment = ComparativeExperiment(
            graphrag_service=qa_service,
            rag_service=qa_service,
            llm_service=qa_service
        )
        
        # Manually evaluate each answer
        evaluator = experiment.evaluator
        
        graphrag_eval = evaluator.evaluate(graphrag_answer, test_item["expected"], request.question)
        rag_eval = evaluator.evaluate(rag_answer, test_item["expected"], request.question)
        llm_eval = evaluator.evaluate(llm_answer, test_item["expected"], request.question)
        
        # Calculate statistics
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
            improvement=improvement
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[评估服务] 回答质量评估失败: {e}")
        logger.debug(f"详细错误: {error_details}")
        raise HTTPException(status_code=500, detail=f"回答质量评估失败: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if evaluation service is available."""
    return {
        "status": "healthy",
        "has_qa_service": qa_service is not None,
        "neo4j_connected": neo4j_client.driver is not None
    }