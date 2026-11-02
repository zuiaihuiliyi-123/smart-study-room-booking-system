"""PII 脱敏工具（NFR-006 / §5.6）。

管理端读取用户联系方式时**必须在服务端脱敏**，不能只依赖前端遮挡——
否则明文仍会暴露在 HTTP 响应体、导出与日志中（A 级个人信息保护硬约束）。
本人读取本人资料（``/users/me``、``/auth/me``）不在本模块处理，保持原值。
"""

from __future__ import annotations

HIDDEN = "—"


def _is_blank(value: str | None) -> bool:
    return (value or "").strip() == ""


def _mask_generic(text: str) -> str:
    """通用短串掩码：保留首尾各 1~2 位，中间用 ``***`` 代替。"""
    if len(text) <= 2:
        return "*" * len(text)
    if len(text) <= 5:
        return f"{text[0]}***{text[-1]}"
    return f"{text[:2]}***{text[-2:]}"


def mask_phone(value: str | None) -> str:
    """手机号 / 工号类数字串：保留前 3 位与后 4 位（``13800001234`` → ``138****1234``）。"""
    if _is_blank(value):
        return HIDDEN
    text = (value or "").replace(" ", "").replace("-", "")
    if text.isdigit() and len(text) >= 7:
        return f"{text[:3]}****{text[-4:]}"
    return _mask_generic((value or "").strip())


def mask_email(value: str | None) -> str:
    """邮箱：保留首字母与完整域名（``student@zju.edu.cn`` → ``s******@zju.edu.cn``）。"""
    if _is_blank(value):
        return HIDDEN
    text = (value or "").strip()
    at = text.rfind("@")
    if at <= 0:
        return _mask_generic(text)
    local = text[:at]
    domain = text[at:]
    stars = "*" * max(3, len(local) - 1)
    return f"{local[:1]}{stars}{domain}"


def mask_contact(value: str | None) -> str:
    """联系方式（手机号或邮箱）：按形态选择掩码方式，与前端 ``mask.ts`` 口径一致。"""
    if _is_blank(value):
        return HIDDEN
    text = (value or "").strip()
    if "@" in text:
        return mask_email(text)
    if all(ch.isdigit() or ch in " -" for ch in text):
        return mask_phone(text)
    return _mask_generic(text)


def contact_kind_label(value: str | None) -> str:
    """联系方式形态说明（手机号 / 邮箱 / 未填写）。"""
    if _is_blank(value):
        return "未填写"
    return "邮箱" if "@" in (value or "") else "手机号"
