from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.core.security import create_access_token, verify_password
from app.models.enums import AccountStatus
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    """FR-040：学号/工号 + 密码登录，签发 JWT。"""
    user = db.scalar(select(User).where(User.student_no == payload.student_no))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise BusinessError(
            "学号或密码错误",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )
    if user.account_status == AccountStatus.DISABLED.value:
        raise BusinessError(
            "账户已停用，请联系管理员",
            code="ACCOUNT_DISABLED",
            status_code=403,
        )
    return TokenResponse(access_token=create_access_token(str(user.id), user.role))
