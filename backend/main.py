"""FastAPI 应用入口"""
import sys
import os
from contextlib import asynccontextmanager

# 确保 backend 目录在 Python 路径中
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from config.database import init_db, close_db
from api import assessment_router, auth_router, sessions_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 导入所有模型，确保它们注册到 Base.metadata
    from models.user import User  # noqa: F401
    from models.session import Session  # noqa: F401

    await init_db()
    # 初始化 LangGraph 测评工作流
    import workflow.graph as wf_graph
    wf_graph.assessment_graph = await wf_graph.init_assessment_graph()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 已启动")
    yield
    await close_db()
    print("👋 应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(assessment_router)

# 挂载静态目录（保留给未来静态资源使用）
# 注意：生产环境使用 MinIO 对象存储，本地 static 目录仅用于开发调试
# static_dir = os.path.join(backend_dir, "static")
# os.makedirs(os.path.join(static_dir, "reports"), exist_ok=True)
# app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
