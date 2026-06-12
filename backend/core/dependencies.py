"""依赖注入模块"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from config.database import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
