"""报告管理 API"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.dependencies import get_db
from models.report import Report
from models.session import Session
from services.xpay_service import (
    XPayConfigError,
    XPayError,
    create_alipay_payment,
    extract_request_params,
    format_money,
    get_report_id_from_payment,
    parse_business_param,
    query_order,
    verify_sign,
)

router = APIRouter(prefix="/api", tags=["报告"])
settings = get_settings()


class SaveReportRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    report_title: Optional[str] = None
    report_content: str


class PayReportRequest(BaseModel):
    payment_method: Optional[str] = "alipay"


class ManualUnlockReportsRequest(BaseModel):
    unlock_code: str  # 支持 session_id 或 user_id


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
            session_result = await db.execute(
                select(Session).where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                    Session.report_status == "completed",
                )
            )
            session = session_result.scalar_one_or_none()
            if not session or not session.report:
                raise HTTPException(status_code=404, detail="报告不存在")

            report = Report(
                user_id=user_id,
                session_id=session_id,
                report_title=_build_default_title(),
                report_content=session.report,
                is_paid=False,
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)

        return {"report": _report_to_dict(report)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"按会话查询报告失败: {e}")
        raise HTTPException(status_code=500, detail="查询报告失败")


@router.post("/reports/manual-unlock")
async def manual_unlock_reports(
    payload: ManualUnlockReportsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    人工审核通过后解锁报告。
    优先按 session_id 精确解锁单个报告，回退到 user_id 解锁该用户所有报告。
    """
    unlock_code = payload.unlock_code.strip()
    if not unlock_code:
        raise HTTPException(status_code=400, detail="解锁码不能为空")

    try:
        # 优先尝试按 session_id 解锁（精确控制）
        result = await db.execute(
            select(Report).where(Report.session_id == unlock_code)
        )
        reports = result.scalars().all()

        # 如果 session_id 没找到，尝试按 user_id 解锁（兼容旧版）
        if not reports:
            result = await db.execute(
                select(Report).where(Report.user_id == unlock_code)
            )
            reports = result.scalars().all()

        if not reports:
            raise HTTPException(status_code=404, detail="未找到对应的报告")

        # 解锁找到的报告
        unlocked_count = 0
        for report in reports:
            if not report.is_paid:
                report.is_paid = True
                unlocked_count += 1

        if unlocked_count == 0:
            return {
                "success": True,
                "unlock_code": unlock_code,
                "unlocked_count": 0,
                "message": "报告已经是解锁状态",
            }

        await db.commit()
        return {
            "success": True,
            "unlock_code": unlock_code,
            "unlocked_count": unlocked_count,
            "is_paid": True,
            "message": f"已解锁 {unlocked_count} 份报告",
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"人工解锁报告失败: {e}")
        raise HTTPException(status_code=500, detail="人工解锁报告失败")


@router.post("/reports/{report_id}/pay")
async def pay_report(
    report_id: int,
    payload: PayReportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建支付宝支付订单。支付成功由 ZPAY 回调后再更新 reports.is_paid。"""
    try:
        if payload.payment_method != "alipay":
            raise HTTPException(status_code=400, detail="当前仅支持支付宝支付")

        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        if report.is_paid:
            return {
                "success": True,
                "paid": True,
                "report_id": report.id,
                "is_paid": True,
                "message": "报告已支付",
            }

        base_url = _payment_base_url(request)
        payment = await create_alipay_payment(
            gateway_url=settings.XPAY_GATEWAY_URL,
            pid=settings.XPAY_PID,
            key=settings.XPAY_KEY,
            report_id=report.id,
            session_id=report.session_id,
            amount=settings.XPAY_REPORT_AMOUNT,
            product_name=settings.XPAY_REPORT_NAME,
            site_name=settings.XPAY_SITE_NAME or settings.APP_NAME,
            notify_url=f"{base_url}/api/payments/xpay/notify",
            return_url=f"{base_url}/api/payments/xpay/return",
            client_ip=request.client.host if request.client else "127.0.0.1",
        )

        return {
            "success": True,
            "paid": False,
            "report_id": report.id,
            "session_id": report.session_id,
            "is_paid": False,
            "message": "请使用支付宝扫码支付",
            **payment,
        }
    except XPayConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except XPayError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"支付报告失败: {e}")
        raise HTTPException(status_code=500, detail="支付处理失败")


@router.get("/reports/{report_id}/payment-status")
async def get_report_payment_status(
    report_id: int,
    out_trade_no: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """查询报告支付状态；必要时向 ZPAY 查询订单并兜底回写。"""
    try:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        if report.is_paid:
            return {
                "success": True,
                "report_id": report.id,
                "is_paid": True,
                "message": "支付成功",
            }

        gateway_order = None
        gateway_error = None
        if out_trade_no:
            if get_report_id_from_payment({"out_trade_no": out_trade_no}) != report.id:
                raise HTTPException(status_code=400, detail="订单号与报告不匹配")

            try:
                gateway_order = await query_order(
                    gateway_url=settings.XPAY_GATEWAY_URL,
                    pid=settings.XPAY_PID,
                    key=settings.XPAY_KEY,
                    out_trade_no=out_trade_no,
                )
            except XPayError as e:
                gateway_error = str(e)

            if _is_gateway_order_paid_for_report(gateway_order, report.id):
                report.is_paid = True
                await db.commit()
                await db.refresh(report)

        return {
            "success": True,
            "report_id": report.id,
            "is_paid": report.is_paid,
            "message": "支付成功" if report.is_paid else "等待支付",
            "gateway_order": _safe_order_status(gateway_order),
            "gateway_error": gateway_error,
        }
    except XPayConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"查询支付状态失败: {e}")
        raise HTTPException(status_code=500, detail="查询支付状态失败")


@router.api_route("/payments/xpay/notify", methods=["GET", "POST"])
async def xpay_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """ZPAY 异步通知。成功处理后必须返回 success。"""
    params = await extract_request_params(request)
    handled = await _handle_xpay_payment_result(params, db)
    return PlainTextResponse("success" if handled else "fail", status_code=200 if handled else 400)


@router.api_route("/payments/xpay/return", methods=["GET", "POST"])
async def xpay_return(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """ZPAY 页面跳转通知，在弹框内通知前端刷新支付状态。"""
    params = await extract_request_params(request)
    handled = await _handle_xpay_payment_result(params, db)
    business = parse_business_param(params.get("param"))
    payload = {
        "type": "xpay-return",
        "paid": handled,
        "reportId": get_report_id_from_payment(params),
        "sessionId": business.get("session_id"),
    }
    message = "支付成功，正在打开报告..." if handled else "支付状态尚未确认，请回到页面稍后刷新。"
    html = f"""
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>支付结果</title>
        <style>
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: #1f2328;
            background: #f7f3ed;
          }}
          .box {{
            width: min(360px, calc(100vw - 32px));
            padding: 24px;
            border: 1px solid #eadfd3;
            border-radius: 16px;
            background: #fff;
            text-align: center;
            box-shadow: 0 16px 40px rgba(38, 29, 20, 0.08);
          }}
          p {{ margin: 0 0 14px; line-height: 1.7; }}
          button {{
            border: 0;
            border-radius: 10px;
            padding: 10px 16px;
            background: #1677ff;
            color: #fff;
            font-weight: 800;
            cursor: pointer;
          }}
        </style>
      </head>
      <body>
        <div class="box">
          <p>{message}</p>
          <button onclick="window.parent && window.parent !== window ? window.parent.postMessage(payload, '*') : window.close()">返回报告页</button>
        </div>
        <script>
          const payload = {json.dumps(payload, ensure_ascii=False)};
          if (window.parent && window.parent !== window) {{
            window.parent.postMessage(payload, '*');
          }}
          if (window.opener) {{
            window.opener.postMessage(payload, '*');
          }}
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html)


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


def _payment_base_url(request: Request) -> str:
    configured = settings.PAYMENT_PUBLIC_BASE_URL.strip()
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def _is_success_payment_params(params: dict[str, str]) -> bool:
    if params.get("pid") and str(params.get("pid")) != settings.XPAY_PID:
        return False
    if params.get("type") != "alipay":
        return False
    if params.get("trade_status") != "TRADE_SUCCESS":
        return False
    try:
        return format_money(params.get("money", "")) == format_money(settings.XPAY_REPORT_AMOUNT)
    except XPayError:
        return False


async def _handle_xpay_payment_result(params: dict[str, str], db: AsyncSession) -> bool:
    try:
        if not verify_sign(params, settings.XPAY_KEY):
            print("ZPAY 回调验签失败")
            return False
        if not _is_success_payment_params(params):
            print(f"ZPAY 回调状态或金额不匹配: {params}")
            return False

        report_id = get_report_id_from_payment(params)
        if not report_id:
            print(f"ZPAY 回调缺少 report_id: {params}")
            return False

        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            print(f"ZPAY 回调报告不存在: report_id={report_id}")
            return False

        if not report.is_paid:
            report.is_paid = True
            await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        print(f"处理 ZPAY 回调失败: {e}")
        return False


def _is_gateway_order_paid_for_report(order: dict | None, report_id: int) -> bool:
    if not order or str(order.get("code")) != "1":
        return False
    if str(order.get("status")) != "1":
        return False
    if order.get("type") != "alipay":
        return False
    if str(order.get("pid")) != settings.XPAY_PID:
        return False
    if get_report_id_from_payment(order) != report_id:
        return False
    try:
        return format_money(order.get("money", "")) == format_money(settings.XPAY_REPORT_AMOUNT)
    except XPayError:
        return False


def _safe_order_status(order: dict | None) -> dict | None:
    if not order:
        return None
    return {
        "code": order.get("code"),
        "msg": order.get("msg"),
        "status": order.get("status"),
        "out_trade_no": order.get("out_trade_no"),
        "trade_no": order.get("trade_no"),
        "type": order.get("type"),
        "money": order.get("money"),
    }
