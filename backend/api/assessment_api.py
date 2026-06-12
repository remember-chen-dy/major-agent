"""测评相关 API 路由"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.assessment_service import AssessmentService

router = APIRouter(prefix="/api/assessment", tags=["测评"])


# ================================================================
# Request / Response Models
# ================================================================


class ChatRequest(BaseModel):
    """对话请求 —— 用户对当前问题的回答

    answer: 任意类型的答案值
        - form 类型: {"score": 620, "rank": 8500}
        - button_select: "一线"
        - tag_multi_select: ["物理", "化学"]
        - slider: 75
    """
    answer: Any = None


class InteractionMessage(BaseModel):
    """单条消息"""
    role: str = "ai"
    content: str = ""
    interaction: Optional[dict] = None


class ChatResponse(BaseModel):
    """对话响应

    问题阶段:
        messages: 包含引导语和 interaction 配置
        current_step: 当前问题 ID
        is_complete: False

    报告阶段:
        report: Markdown 报告文本
        report_pdf_url: PDF 下载链接
        current_step: "done"
        is_complete: True
    """
    messages: list[dict] = []
    current_step: str = ""
    is_complete: bool = False
    report: Optional[str] = None
    report_pdf_url: Optional[str] = None
    session_id: Optional[str] = None  # 仅在创建会话时返回


# ================================================================
# Endpoints
# ================================================================


@router.post("/session")
async def create_assessment_session():
    """创建新的测评会话

    返回:
    - session_id: 会话唯一标识，后续所有对话请求需带上
    - messages: [{"role": "ai", "content": "引导语", "interaction": {...}}]
    - current_step: 当前问题 ID (q1_score)
    """
    session_id, first_question = await AssessmentService.create_session()
    return {
        "session_id": session_id,
        **first_question,
    }


@router.post("/chat/{session_id}")
async def send_message(session_id: str, request: ChatRequest):
    """发送当前问题的答案，获取下一个问题或最终报告

    - 测评阶段：返回下一个问题的 messages + interaction 配置
    - 报告阶段：返回 Markdown 报告 + PDF 链接
    """
    result = await AssessmentService.chat(session_id, request.answer)

    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/session/{session_id}/results")
async def get_recommendations(session_id: str):
    """获取测评最终结果（报告 + 答案历史）"""
    results = await AssessmentService.get_results(session_id)

    if results.get("error"):
        raise HTTPException(status_code=404, detail=results["error"])

    return results
