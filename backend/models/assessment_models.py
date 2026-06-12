"""测评相关数据模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, Text, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.sql import func

from config.database import Base


class AssessmentSession(Base):
    """测评会话表"""
    __tablename__ = "assessment_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    session_id = Column(String(64), unique=True, nullable=False, index=True, comment="会话唯一标识")
    student_type = Column(String(32), nullable=True, comment="学生类型: 理科/文科/综合")
    current_step = Column(Integer, default=0, comment="当前测评步骤 0-4")
    status = Column(String(16), default="in_progress", comment="状态: in_progress/completed")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系
    records: list["AssessmentRecord"] = []  # type: ignore
    recommendations: list["RecommendationResult"] = []  # type: ignore

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_type": self.student_type,
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AssessmentRecord(Base):
    """测评记录表 - 存储用户每一步的选择"""
    __tablename__ = "assessment_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    session_id = Column(String(64), nullable=False, index=True, comment="关联会话ID")
    step = Column(Integer, nullable=False, comment="测评步骤 0-4")
    question = Column(Text, nullable=False, comment="问题内容")
    answer = Column(Text, nullable=False, comment="用户回答")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "step": self.step,
            "question": self.question,
            "answer": self.answer,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecommendationResult(Base):
    """推荐结果表"""
    __tablename__ = "recommendation_results"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="结果ID")
    session_id = Column(String(64), nullable=False, index=True, comment="关联会话ID")
    major_name = Column(String(128), nullable=False, comment="专业名称")
    match_score = Column(Float, nullable=False, comment="匹配度分数 0-100")
    description = Column(Text, nullable=True, comment="专业描述")
    universities = Column(JSON, nullable=True, comment="推荐院校列表")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "major_name": self.major_name,
            "match_score": self.match_score,
            "description": self.description,
            "universities": self.universities or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
