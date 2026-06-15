"""会话管理 API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from core.security import get_current_user
from models.user import User
from models.session import Session
from services.report_service import ReportService
from services.assessment_service import AssessmentService

router = APIRouter(prefix="/api", tags=["会话"])


@router.post("/sessions")
async def create_session(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新会话并初始化 LangGraph 测评流程

    返回:
    - session_id: 会话唯一标识
    - messages: 第一个问题的引导语和交互配置
    - current_step: 当前问题 ID
    """
    title = request.get("title", "新会话")

    session_id, first_question = await AssessmentService.create_session(
        db=db,
        user_id=current_user.id,
        title=title,
    )

    return {
        "session_id": session_id,
        "user_id": current_user.id,
        "title": title,
        **first_question,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取会话详情"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": str(session.id),
        "title": session.title,
        "status": session.status,
        "checkpointer_state": session.checkpointer_state,
        "report_status": session.report_status,
        "report_progress": session.report_progress,
        "report_url": session.report_url or "",
        "messages": session.messages or [],
        "is_complete": session.report_status == "completed",
        "is_generating": session.report_status == "generating",
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除当前用户的会话。"""
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.delete(session)
    await db.commit()

    return {"success": True}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取会话消息历史"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": str(session.id),
        "messages": session.messages or [],
        "is_complete": session.report_status == "completed",
    }


@router.put("/sessions/{session_id}/checkpoint")
async def save_checkpoint(
    session_id: str,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """保存检查点状态"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 更新检查点状态
    session.checkpointer_state = {
        "current_step": request.get("current_step"),
        "completed_questions": request.get("completed_questions", []),
        "answers": request.get("answers", {}),
    }
    await db.commit()

    return {"success": True}


@router.post("/sessions/{session_id}/submit")
async def submit_session(
    session_id: str,
    request: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """提交会话并触发报告生成"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 更新报告状态为生成中
    session.report_status = "generating"
    session.report_progress = 10
    await db.commit()

    # 启动后台任务生成报告
    final_answers = request.get("final_answers", {})
    background_tasks.add_task(
        ReportService.generate_report,
        str(session.id),
        str(session.user_id),
        final_answers
    )

    return {"status": "generating", "message": "报告生成已启动"}


@router.get("/sessions/{session_id}/report-status")
async def get_report_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取报告生成状态"""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "status": session.report_status,
        "progress": session.report_progress,
        "report_url": session.report_url or "",
    }
