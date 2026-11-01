import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import AccountStatus, Role
from app.models.user import User
from app.services import audit_service

# 使用 HTTPBearer 而不是 OAuth2PasswordBearer：登录接口是 JSON 形式
# （前端契约），Swagger 的 Authorize 对话框因此改为直接粘贴 access_token。
bearer_scheme = HTTPBearer(auto_error=False, description="Bearer JWT")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 JWT 并加载当前用户；停用账户直接拒绝。"""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None or user.account_status == AccountStatus.DISABLED.value:
        raise unauthorized
    return user


def _record_unauthorized(db: Session, user: User, action: str) -> None:
    """ST-048：越权尝试写入审计日志（只追加）。"""
    audit_service.record(
        db,
        operator_id=user.id,
        action_type="UNAUTHORIZED_ATTEMPT",
        target_type="api",
        reason=f"角色「{user.role}」尝试执行 {action}",
        before_value=None,
        after_value=None,
    )
    db.commit()


def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """仅自习室管理员 / 系统管理员可访问。"""
    if current_user.role not in (Role.ADMIN.value, Role.SYSTEM_ADMIN.value):
        _record_unauthorized(db, current_user, "管理员专属操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限执行该操作",
        )
    return current_user


def require_student(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """仅学生用户可执行的操作（如提交投诉、评价；权限矩阵 4.1.1 R-01）。"""
    if current_user.role != Role.STUDENT.value:
        _record_unauthorized(db, current_user, "学生专属操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅限学生用户",
        )
    return current_user


def require_booking_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """预约与签到签退仅限学生 / 教师（R-01 / R-03），管理员不得以个人身份预约。"""
    if current_user.role not in (Role.STUDENT.value, Role.TEACHER.value):
        _record_unauthorized(db, current_user, "学生/教师预约操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅限学生或教师用户",
        )
    return current_user
