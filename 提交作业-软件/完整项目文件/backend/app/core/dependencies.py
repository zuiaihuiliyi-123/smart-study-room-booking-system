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
    if user is None:
        raise unauthorized
    # 改密后 token_version 递增：此前签发的令牌立即失效（旧会话需重新登录）
    if payload.get("ver", 0) != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.account_status == AccountStatus.DISABLED.value:
        # 与 login 的口径保持一致：停用是「权限/资格」问题而非「登录过期」，
        # 返回 403 可避免前端把它误当成 token 失效而反复跳转登录页。
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已停用，请联系管理员",
        )
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
    """仅自习室管理员 R-02 可访问（业务管理权限）。

    系统管理员 R-04 本版**未被授予任何业务操作权限**——课程结构版 §4.1.1
    定稿矩阵明确 R-04 仅拥有"全局参数配置"（该接口本期未实现）。故 R-04 调用
    全部业务管理接口一律拒绝（AGENTS.md §12.4 第 3 项 BR-018 拆分）。
    """
    if current_user.role != Role.ADMIN.value:
        _record_unauthorized(db, current_user, "业务管理员专属操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限执行该操作",
        )
    return current_user


def require_system_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """仅系统管理员 R-04 可访问（全局参数配置等，本期接口未实现）。"""
    if current_user.role != Role.SYSTEM_ADMIN.value:
        _record_unauthorized(db, current_user, "系统管理员专属操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅限系统管理员",
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
    """预约与签到签退仅限学生 R-01（权限矩阵 §4.1.1；R-03 教师角色已于 V2.1 取消）。

    管理员 R-02/R-04 不得以个人身份预约（UCD-02"创建预约"仅出现在学生端）。
    """
    if current_user.role != Role.STUDENT.value:
        _record_unauthorized(db, current_user, "学生预约操作")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作仅限学生用户",
        )
    return current_user
