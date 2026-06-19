"""清空数据库并重置表结构

用法：
    cd backend
    DATABASE_URL="你的数据库地址" python3 clear_db.py

警告：此操作会删除所有数据且不可恢复！
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import engine, Base


async def clear_database():
    """删除所有表并重新创建，清空全部数据"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库已清空，表结构已重建")


if __name__ == "__main__":
    from core.config import get_settings

    settings = get_settings()
    if not settings.DATABASE_URL:
        print("❌ 未设置 DATABASE_URL，请在 .env 文件或环境变量中配置")
        sys.exit(1)

    confirm = input(f"确定要清空数据库吗？{settings.DATABASE_URL}\n输入 yes 确认：")
    if confirm.strip().lower() != "yes":
        print("已取消")
        sys.exit(0)

    asyncio.run(clear_database())
