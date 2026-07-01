"""FastAPI 应用入口"""
import sys
import os
from contextlib import asynccontextmanager

# 确保 backend 目录在 Python 路径中
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from config.database import init_db, close_db
from api import assessment_router, auth_router, sessions_router, reports_router

# 人工解锁页面目录
manual_unlock_dir = os.path.join(backend_dir, "..", "manual-unlock")

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 导入所有模型，确保它们注册到 Base.metadata
    from models.user import User  # noqa: F401
    from models.session import Session  # noqa: F401
    from models.report import Report  # noqa: F401

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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(assessment_router)
app.include_router(reports_router)

# 前端构建产物目录
frontend_dist = os.path.join(backend_dir, "..", "frontend", "dist")

# 挂载前端静态资源（JS/CSS/图片）
if os.path.isdir(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/admin/manual-unlock", response_class=HTMLResponse)
async def manual_unlock_page():
    """人工解锁管理页面"""
    html_path = os.path.join(manual_unlock_dir, "index.html")
    if not os.path.isfile(html_path):
        return HTMLResponse("<h1>页面不存在</h1>", status_code=404)
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    # 自动替换后端地址为当前服务地址
    content = content.replace('value="http://127.0.0.1:8000"', 'value=""')
    return HTMLResponse(content)


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, full_path: str):
    """前端 SPA 兜底：所有非 API 路由返回 index.html"""
    # 尝试返回静态文件（favicon.svg 等）
    file_path = os.path.join(frontend_dist, full_path)
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)
    # 兜底返回 index.html
    index_path = os.path.join(frontend_dist, "index.html")
    with open(index_path, encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
