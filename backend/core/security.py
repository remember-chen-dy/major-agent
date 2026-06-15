"""简单设备认证辅助模块"""
from datetime import datetime

from fastapi import Header, HTTPException, status, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from models.user import User
from core.dependencies import get_db


async def get_or_create_user(db: AsyncSession, device_id: str) -> User:
    """根据 device_id 获取或创建用户，同时更新 last_login_at"""
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(device_id=device_id)
        db.add(user)
        await db.flush()
    else:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login_at=func.now())
        )
        await db.flush()

    return user


async def get_current_user(
    x_device_id: str = Header(..., alias="X-Device-ID"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI 依赖注入：从请求头 X-Device-ID 中获取当前用户"""
    return await get_or_create_user(db, x_device_id)
