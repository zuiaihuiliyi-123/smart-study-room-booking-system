from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.core.security import create_access_token, verify_password
from app.models.enums import AccountStatus
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services import audit_service


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    """FR-040：学号/工号 + 密码登录，签发 JWT，并记录登录审计（NFR-009）。

    登录成功与失败均写审计：成功记 ``LOGIN_SUCCESS``；凭证错误 / 账户停用记
    ``LOGIN_FAILED``（不记录密码，仅记学号与失败原因，供安全审计与暴力探测排查）。
    """
    user = db.scalar(select(User).where(User.student_no == payload.student_no))

    if user is None or not verify_password(payload.password, user.password_hash):
        audit_service.record(
            db,
            operator_id=user.id if user is not None else None,
            action_type="LOGIN_FAILED",
            target_type="USER",
            target_id=user.id if user is not None else None,
            reason=f"学号「{payload.student_no}」凭证错误",
        )
        db.commit()
        raise BusinessError(
            "学号或密码错误",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )
    if user.account_status == AccountStatus.DISABLED.value:
        audit_service.record(
            db,
            operator_id=user.id,
            action_type="LOGIN_FAILED",
            target_type="USER",
            target_id=user.id,
            reason="账户已停用，拒绝登录",
        )
        db.commit()
        raise BusinessError(
            "账户已停用，请联系管理员",
            code="ACCOUNT_DISABLED",
            status_code=403,
        )

    audit_service.record(
        db,
        operator_id=user.id,
        action_type="LOGIN_SUCCESS",
        target_type="USER",
        target_id=user.id,
        reason=f"角色「{user.role}」登录成功",
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id), user.role))
