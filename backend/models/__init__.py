"""数据模型模块"""
from config.database import Base
from models.assessment_models import AssessmentSession, AssessmentRecord, RecommendationResult

__all__ = ["Base", "AssessmentSession", "AssessmentRecord", "RecommendationResult"]
