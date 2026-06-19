"""ZPAY/xpay 支付服务。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urljoin
from urllib.request import Request as UrlRequest
from urllib.request import urlopen


class XPayError(Exception):
    """支付网关调用失败。"""


class XPayConfigError(XPayError):
    """支付配置不完整。"""


def normalize_gateway_url(gateway_url: str) -> str:
    gateway = (gateway_url or "").strip()
    if not gateway:
        raise XPayConfigError("支付网关地址未配置")
    return gateway.rstrip("/") + "/"


def format_money(value: str | int | float | Decimal) -> str:
    """统一金额格式，避免 3 与 3.00 的比较误差。"""
    try:
        money = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise XPayError("支付金额格式错误") from exc
    return str(money.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def sign_params(params: dict[str, Any], key: str) -> str:
    """按 ZPAY 文档生成 MD5 签名。"""
    sign_source = "&".join(
        f"{name}={params[name]}"
        for name in sorted(params)
        if name not in {"sign", "sign_type"}
        and params[name] is not None
        and str(params[name]) != ""
    )
    return hashlib.md5(f"{sign_source}{key}".encode("utf-8")).hexdigest()


def verify_sign(params: dict[str, Any], key: str) -> bool:
    sign = str(params.get("sign") or "").lower()
    if not sign:
        return False
    return sign == sign_params(params, key)


def build_out_trade_no(report_id: int) -> str:
    """生成不超过 32 位的商户订单号。"""
    return f"R{report_id}T{time.strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def build_business_param(report_id: int, session_id: str | None) -> str:
    parts = [f"report_id={report_id}"]
    if session_id:
        parts.append(f"session_id={session_id}")
    return ";".join(parts)


def parse_business_param(param: str | None) -> dict[str, str]:
    if not param:
        return {}
    parsed: dict[str, str] = {}
    for item in str(param).split(";"):
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        if name:
            parsed[name] = value
    return parsed


def get_report_id_from_payment(params: dict[str, Any]) -> int | None:
    business = parse_business_param(str(params.get("param") or ""))
    report_id = business.get("report_id")
    if report_id and report_id.isdigit():
        return int(report_id)

    out_trade_no = str(params.get("out_trade_no") or "")
    match = re.match(r"^R(\d+)T\d+", out_trade_no)
    if match:
        return int(match.group(1))
    return None


def build_submit_url(
    *,
    gateway_url: str,
    key: str,
    params: dict[str, Any],
) -> str:
    signed = {
        name: value
        for name, value in params.items()
        if value is not None and str(value) != ""
    }
    signed["sign"] = sign_params(signed, key)
    signed["sign_type"] = "MD5"
    return f"{urljoin(normalize_gateway_url(gateway_url), 'submit.php')}?{urlencode(signed)}"


def _post_form(url: str, params: dict[str, Any], timeout: int = 8) -> dict[str, Any] | str:
    data = urlencode(params).encode("utf-8")
    request = UrlRequest(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Accept": "application/json,text/plain,*/*",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise XPayError(f"支付网关请求失败: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise XPayError(f"支付网关响应不是 JSON: {body[:120]}") from exc
    if isinstance(payload, str):
        stripped = payload.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                nested_payload = json.loads(stripped)
            except json.JSONDecodeError:
                nested_payload = None
            if isinstance(nested_payload, dict):
                return nested_payload
        return payload
    if not isinstance(payload, dict):
        raise XPayError(f"支付网关响应格式异常: {str(payload)[:120]}")
    return payload


def _get_json(url: str, timeout: int = 8) -> dict[str, Any]:
    request = UrlRequest(url, headers={"Accept": "application/json,text/plain,*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise XPayError(f"支付网关查询失败: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise XPayError(f"支付网关查询响应不是 JSON: {body[:120]}") from exc
    if isinstance(payload, str):
        stripped = payload.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                nested_payload = json.loads(stripped)
            except json.JSONDecodeError:
                nested_payload = None
            if isinstance(nested_payload, dict):
                return nested_payload
    if not isinstance(payload, dict):
        raise XPayError(f"支付网关查询响应格式异常: {str(payload)[:120]}")
    return payload


async def create_alipay_payment(
    *,
    gateway_url: str,
    pid: str,
    key: str,
    report_id: int,
    session_id: str | None,
    amount: str,
    product_name: str,
    site_name: str,
    notify_url: str,
    return_url: str,
    client_ip: str,
) -> dict[str, Any]:
    if not pid or not key:
        raise XPayConfigError("支付商户信息未配置")

    gateway = normalize_gateway_url(gateway_url)
    out_trade_no = build_out_trade_no(report_id)
    money = format_money(amount)
    business_param = build_business_param(report_id, session_id)

    submit_params = {
        "pid": pid,
        "type": "alipay",
        "out_trade_no": out_trade_no,
        "notify_url": notify_url,
        "return_url": return_url,
        "name": product_name,
        "money": money,
        "sitename": site_name,
        "param": business_param,
    }
    submit_url = build_submit_url(gateway_url=gateway, key=key, params=submit_params)

    mapi_params = {
        "pid": pid,
        "type": "alipay",
        "out_trade_no": out_trade_no,
        "notify_url": notify_url,
        "return_url": return_url,
        "name": product_name,
        "money": money,
        "clientip": client_ip or "127.0.0.1",
        "device": "pc",
        "sitename": site_name,
        "param": business_param,
    }
    mapi_params["sign"] = sign_params(mapi_params, key)
    mapi_params["sign_type"] = "MD5"

    gateway_payload: dict[str, Any] | str | None = None
    gateway_error: str | None = None
    try:
        gateway_payload = await asyncio.to_thread(
            _post_form,
            urljoin(gateway, "mapi.php"),
            mapi_params,
        )
    except XPayError as exc:
        gateway_error = str(exc)

    pay_url = submit_url
    qr_image = None
    qr_code = None
    pay_url2 = None
    provider_trade_no = None

    if isinstance(gateway_payload, dict) and str(gateway_payload.get("code")) == "1":
        pay_url = gateway_payload.get("payurl") or submit_url
        pay_url2 = gateway_payload.get("payurl2")
        qr_image = gateway_payload.get("img")
        qr_code = gateway_payload.get("qrcode")
        provider_trade_no = gateway_payload.get("trade_no") or gateway_payload.get("O_id")
    elif isinstance(gateway_payload, str) and gateway_payload.startswith(("http://", "https://")):
        pay_url = gateway_payload
    elif isinstance(gateway_payload, dict):
        gateway_error = gateway_payload.get("msg") or "支付网关未返回可用支付地址"
    elif gateway_payload:
        gateway_error = str(gateway_payload)[:120] or "支付网关未返回可用支付地址"

    return {
        "out_trade_no": out_trade_no,
        "amount": money,
        "payment_method": "alipay",
        "pay_url": pay_url,
        "pay_url2": pay_url2,
        "qr_image": qr_image,
        "qr_code": qr_code,
        "cashier_url": submit_url,
        "provider_trade_no": provider_trade_no,
        "gateway_error": gateway_error,
    }


async def query_order(
    *,
    gateway_url: str,
    pid: str,
    key: str,
    out_trade_no: str,
) -> dict[str, Any]:
    if not pid or not key:
        raise XPayConfigError("支付商户信息未配置")

    params = urlencode({
        "act": "order",
        "pid": pid,
        "key": key,
        "out_trade_no": out_trade_no,
    })
    url = f"{urljoin(normalize_gateway_url(gateway_url), 'api.php')}?{params}"
    return await asyncio.to_thread(_get_json, url)


async def extract_request_params(request) -> dict[str, str]:
    params = dict(request.query_params)
    if request.method.upper() == "POST":
        body = (await request.body()).decode("utf-8", errors="replace")
        params.update(dict(parse_qsl(body, keep_blank_values=True)))
    return params
