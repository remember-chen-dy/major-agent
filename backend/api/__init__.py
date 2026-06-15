"""API 路由模块"""
from api.assessment_api import router as assessment_router
from api.auth import router as auth_router
from api.sessions import router as sessions_router

__all__ = ["assessment_router", "auth_router", "sessions_router"]
