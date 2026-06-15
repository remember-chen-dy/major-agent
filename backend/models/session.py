"""会话数据模型"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="会话唯一标识",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="新会话",
        comment="会话标题",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        comment="会话状态: active/archived/deleted",
    )
    checkpointer_state: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="LangGraph checkpointer 状态",
    )
    report_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="报告状态: pending/generating/completed/failed",
    )
    report_progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="报告生成进度 0-100",
    )
    report_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="报告访问 URL",
    )
    report_file_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="对象存储文件 key",
    )
    langgraph_thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="LangGraph 会话线程 ID",
    )
    messages: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="对话消息历史 (JSON 数组)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
