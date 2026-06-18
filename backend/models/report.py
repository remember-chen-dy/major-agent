"""报告数据模型"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class Report(Base):
    """用户报告表

    每次生成报告后都会写入一条记录，is_paid 标记用户是否已支付查看完整报告。
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联会话ID",
    )
    report_title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="志愿规划报告",
        comment="报告标题",
    )
    report_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="报告全文（Markdown格式）",
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否已支付查看完整报告",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )
