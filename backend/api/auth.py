"""认证相关 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from core.security import get_current_user
from models.user import User
from models.session import Session

router = APIRouter(prefix="/api", tags=["认证"])


@router.post("/auth/login")
async def login(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """一键登录 - 根据 device_id 创建或获取用户"""
    device_id = request.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="缺少 device_id")

    # 查找或创建用户
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(device_id=device_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return {"user_id": str(user.id), "device_id": user.device_id}


@router.get("/users/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return {
        "user_id": str(current_user.id),
        "device_id": current_user.device_id,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取用户的所有会话"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "session_id": str(s.id),
                "title": s.title,
                "status": s.status,
                "report_status": s.report_status,
                "report_progress": s.report_progress,
                "report_url": s.report_url or "",
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]
    }
