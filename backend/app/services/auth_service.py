from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import AccountStatus, Role
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services import audit_service


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    """学生自助注册：创建「学生用户」账号并直接签发令牌。

    学号/工号唯一；并发下由数据库唯一约束兜底，重复提交返回 409 而不是 500。
    """
    existing = db.scalar(
        select(User).where(User.student_no == payload.student_no)
    )
    if existing is not None:
        raise BusinessError(
            "该学号/工号已注册，请直接登录",
            code="STUDENT_NO_TAKEN",
            status_code=409,
        )

    user = User(
        name=payload.name,
        student_no=payload.student_no,
        password_hash=hash_password(payload.password),
        role=Role.STUDENT.value,
        account_status=AccountStatus.NORMAL.value,
        violation_count=0,
        contact=payload.contact,
    )
    db.add(user)
    try:
        db.flush()
        audit_service.record(
            db,
            operator_id=user.id,
            action_type="REGISTER_SUCCESS",
            target_type="USER",
            target_id=user.id,
            reason="学生自助注册",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessError(
            "该学号/工号已注册，请直接登录",
            code="STUDENT_NO_TAKEN",
            status_code=409,
        ) from None

    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id), user.role))


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
