"""Q&A API routes for intelligent question answering."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from services.qa_service import qa_service
from utils.logger import get_logger

logger = get_logger("routes.qa")

# Request/Response models
class Message(BaseModel):
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str


class AskRequest(BaseModel):
    """Request model for asking a question."""
    question: str
    conversation_history: Optional[List[Message]] = None
    use_kg: bool = True  # Use knowledge graph context
    session_id: Optional[str] = None  # Session ID for continuous conversation


class AskResponse(BaseModel):
    """Response model for Q&A endpoint."""
    success: bool
    answer: str
    used_context: bool
    context_snippet: Optional[str] = None
    error: Optional[str] = None

class QARecord(BaseModel):
    """问答记录"""
    id: str
    question: str
    answer: str
    timestamp: str
    session_id: Optional[str] = None
    confidence: Optional[float] = None

class FeedbackRequest(BaseModel):
    """反馈请求"""
    qa_id: str
    rating: int = 5  # 1-5
    feedback: Optional[str] = None
    helpful: bool = True


# Create router
router = APIRouter(prefix="/qa", tags=["Q&A"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """
    Ask a question to the AI using knowledge graph context.
    
    Args:
        request: Question and optional conversation history
        
    Returns:
        Answer with metadata about context usage
    """
    try:
        # Validate input
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        # Convert Message objects to dicts
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Get answer from QA service
        result = qa_service.answer_question(
            question=request.question,
            conversation_history=history,
            use_kg=request.use_kg,
            session_id=request.session_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to answer question")
            )
        
        return AskResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] 问答请求失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/history", response_model=Dict[str, Any])
async def get_qa_history(
        session_id: Optional[str] = Query(None, description="会话ID"),
        limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """
    获取问答历史记录。

    Args:
        session_id: 可选会话ID筛选
        limit: 返回记录数量

    Returns:
        包含历史记录的响应
    """
    try:
        history = qa_service.get_history(session_id, limit)

        return {
            "history": history,
            "total": len(history),
            "session_id": session_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    提交答案反馈。

    Args:
        feedback: 反馈信息

    Returns:
        操作结果
    """
    try:
        if feedback.rating < 1 or feedback.rating > 5:
            raise HTTPException(status_code=400, detail="评分必须在1-5之间")

        qa_service.add_feedback(feedback)

        return {
            "success": True,
            "message": "反馈已提交",
            "qa_id": feedback.qa_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")

@router.get("/health")
async def health_check():
    """Check if Q&A service is available."""
    return {
        "status": "healthy" if qa_service.ai_client else "unhealthy",
        "provider": qa_service.settings.ai_provider,
        "has_ai_client": qa_service.ai_client is not None
    }