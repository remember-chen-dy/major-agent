"""报告管理 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from models.report import Report

router = APIRouter(prefix="/api", tags=["报告"])


class SaveReportRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    report_title: Optional[str] = None
    report_content: str


class PayReportRequest(BaseModel):
    # 预留字段，接入真实支付时扩展
    payment_method: Optional[str] = "wechat"


@router.post("/reports")
async def save_report(
    request: SaveReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """保存用户报告到 reports 表"""
    try:
        title = request.report_title or _build_default_title()
        report = Report(
            user_id=request.user_id,
            session_id=request.session_id,
            report_title=title,
            report_content=request.report_content,
            is_paid=False,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "report_id": report.id,
            "user_id": report.user_id,
            "session_id": report.session_id,
            "report_title": report.report_title,
            "is_paid": report.is_paid,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    except Exception as e:
        await db.rollback()
        print(f"保存报告失败: {e}")
        raise HTTPException(status_code=500, detail="保存报告失败")


@router.get("/users/{user_id}/reports/latest")
async def get_latest_report(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取用户最新的一份报告"""
    try:
        result = await db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()

        if not report:
            return {
                "has_report": False,
                "report": None,
            }

        return {
            "has_report": True,
            "report": _report_to_dict(report),
        }
    except Exception as e:
        print(f"查询最新报告失败: {e}")
        raise HTTPException(status_code=500, detail="查询最新报告失败")


@router.get("/users/{user_id}/reports")
async def get_user_reports(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取用户所有历史报告列表（按时间倒序）"""
    try:
        result = await db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
        )
        reports = result.scalars().all()

        return {
            "reports": [_report_to_dict(r) for r in reports],
        }
    except Exception as e:
        print(f"查询报告列表失败: {e}")
        raise HTTPException(status_code=500, detail="查询报告列表失败")


@router.get("/reports/by-session/{session_id}")
async def get_report_by_session(
    session_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """根据会话ID获取报告"""
    try:
        result = await db.execute(
            select(Report)
            .where(
                Report.session_id == session_id,
                Report.user_id == user_id,
            )
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {"report": _report_to_dict(report)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"按会话查询报告失败: {e}")
        raise HTTPException(status_code=500, detail="查询报告失败")


@router.post("/reports/{report_id}/pay")
async def pay_report(
    report_id: int,
    request: PayReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """支付查看完整报告（当前为预留接口，直接标记为已支付）

    TODO: 接入微信支付/支付宝真实回调后，在此校验支付结果再更新 is_paid。
    """
    try:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        # 真实支付流程：
        # 1. 调用微信支付统一下单接口，金额 3 元
        # 2. 等待微信支付回调
        # 3. 回调验证通过后，再设置 is_paid = True
        report.is_paid = True
        await db.commit()
        await db.refresh(report)

        return {
            "success": True,
            "report_id": report.id,
            "is_paid": report.is_paid,
            "message": "支付成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"支付报告失败: {e}")
        raise HTTPException(status_code=500, detail="支付处理失败")


def _build_default_title() -> str:
    now = datetime.now()
    return f"志愿规划报告 {now.strftime('%Y-%m-%d %H:%M')}"


def _report_to_dict(report: Report) -> dict:
    return {
        "report_id": report.id,
        "user_id": report.user_id,
        "session_id": report.session_id,
        "report_title": report.report_title,
        "report_content": report.report_content,
        "is_paid": report.is_paid,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
