from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    """业务异常：统一返回 code + message + 可选 details。

    ``code`` 建议直接使用需求编号（如 C3_BR-006、ST-029），便于前端提示与测试断言。
    ``details`` 用于携带未通过的判定项、参数值与冲突明细（FR-012 / IC-04）。
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "BUSINESS_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# ---------------------------------------------------------------------------
# 参数校验错误的人话翻译
#
# 直接抛出 Pydantic 的英文原文（如 "String should have at least 8 characters"）
# 或笼统的「请求参数校验失败」，用户都不知道该改哪里。这里按「字段 + 类型」拼一句
# 能照着改的提示，例如「密码至少 8 个字符」「请填写学号 / 工号」。
# `details.errors` 仍保留原始的 loc / msg / type，方便排查与前端按需处理。
# ---------------------------------------------------------------------------

_FIELD_LABELS: dict[str, str] = {
    "password": "密码",
    "new_password": "新密码",
    "old_password": "原密码",
    "confirm_password": "确认密码",
    "student_no": "学号 / 工号",
    "name": "姓名",
    "contact": "联系方式",
    "reason": "原因",
    "handle_note": "处理说明",
    "note": "备注",
    "max_uses": "可注册人数",
    "expires_at": "失效时间",
    "role": "角色",
    "account_status": "账户状态",
    "violation_min": "违约次数下限",
    "keyword": "关键词",
    "state": "状态",
    "status": "状态",
    "page": "页码",
    "page_size": "每页条数",
    "start_time": "开始时间",
    "end_time": "结束时间",
    "reserve_date": "预约日期",
    "reserve_date_from": "开始日期",
    "reserve_date_to": "结束日期",
    "seat_id": "座位",
    "room_id": "自习室",
    "area_id": "分区",
    "idempotency_key": "请求标识",
    "target_type": "对象类型",
    "cancel_affected": "是否取消受影响预约",
}

_TYPE_TEMPLATES: dict[str, str] = {
    "missing": "请填写{field}",
    "string_too_short": "{field}至少 {limit} 个字符",
    "string_too_long": "{field}最多 {limit} 个字符",
    "string_type": "{field}必须是文本",
    "int_type": "{field}必须是整数",
    "int_parsing": "{field}必须是整数",
    "float_parsing": "{field}必须是数字",
    "bool_type": "{field}必须是布尔值",
    "bool_parsing": "{field}必须是布尔值",
    "datetime_parsing": "{field}格式不正确，应为日期时间",
    "date_parsing": "{field}格式不正确，应为日期",
    "time_parsing": "{field}格式不正确，应为时间",
    "string_pattern_mismatch": "{field}格式不正确",
    "greater_than_equal": "{field}不能小于 {limit}",
    "less_than_equal": "{field}不能大于 {limit}",
    "greater_than": "{field}必须大于 {limit}",
    "less_than": "{field}必须小于 {limit}",
    "enum": "{field}取值不在允许范围内",
    "literal_error": "{field}取值不在允许范围内",
    "json_invalid": "提交的数据格式不正确",
}

_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


def _field_label(loc: Sequence[Any]) -> str:
    """把 loc 里最后一段字段名翻成中文；没有字段名时退回「参数」。"""
    for part in reversed(list(loc)):
        if isinstance(part, str) and part not in _LOCATION_PREFIXES:
            return _FIELD_LABELS.get(part, part)
    return "参数"


def _limit_of(ctx: dict[str, Any]) -> int | float | None:
    for key in ("min_length", "max_length", "ge", "le", "gt", "lt", "limit"):
        value = ctx.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _friendly_message(item: dict[str, Any]) -> str:
    """单条校验错误 → 一句中文提示；无法识别时退回通用文案。"""
    error_type = str(item.get("type", ""))
    raw_ctx = item.get("ctx")
    ctx: dict[str, Any] = raw_ctx if isinstance(raw_ctx, dict) else {}
    label = _field_label(item.get("loc") or [])

    # 字段自定义校验器（如「密码不能全为空白字符」）已自带中文，去掉 Pydantic 前缀即可
    if error_type == "value_error":
        error = ctx.get("error")
        text = str(error) if error is not None else str(item.get("msg", ""))
        text = text.removeprefix("Value error, ").strip()
        return text or f"{label}填写不正确"

    template = _TYPE_TEMPLATES.get(error_type)
    if template is None:
        return "请求参数校验失败"
    if "{limit}" in template:
        limit = _limit_of(ctx)
        if limit is None:
            return f"{label}填写不正确"
        return template.format(field=label, limit=limit)
    return template.format(field=label)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
        content: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.details:
            content["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        _: Request, exc: HTTPException
    ) -> JSONResponse:
        """把 FastAPI/依赖层异常也统一成 code + message 结构。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        messages = [_friendly_message(item) for item in errors]
        # 去重、最多列 3 条：一次报一长串用户同样看不懂
        unique = list(dict.fromkeys(text for text in messages if text))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "；".join(unique[:3]) or "请求参数校验失败",
                "details": {
                    "errors": [
                        {
                            "loc": list(item.get("loc", [])),
                            "msg": item.get("msg", ""),
                            "type": item.get("type", ""),
                        }
                        for item in errors
                    ]
                },
            },
        )

    @app.exception_handler(NotImplementedError)
    async def handle_not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "code": "NOT_IMPLEMENTED",
                "message": str(exc) or "该功能尚未实现",
            },
        )
