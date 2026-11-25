from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import AccountStatus, Role
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import PasswordChangeRequest
from app.services import audit_service
from app.utils import time_utils


def _registration_whitelist() -> set[str]:
    """解析可注册学号白名单；空字符串表示不限制。"""
    raw = (settings.registration_whitelist or "").strip()
    if not raw:
        return set()
    return {
        item.strip()
        for item in raw.replace(";", ",").replace("\n", ",").split(",")
        if item.strip()
    }


def _ensure_registration_allowed(student_no: str) -> None:
    """A2 注册身份核验：关闭开关或白名单不匹配时拒绝注册。

    默认 ``registration_enabled=True`` 且白名单为空，保持课程演示可用；
    真实上线可在 ``backend/.env`` 中关闭自助注册，或配置学籍白名单。
    """
    if not settings.registration_enabled:
        raise BusinessError(
            "自助注册已关闭，请联系管理员开户",
            code="REGISTRATION_CLOSED",
            status_code=403,
        )
    allowed = _registration_whitelist()
    if allowed and student_no not in allowed:
        raise BusinessError(
            "该学号不在可注册名单内，请联系管理员",
            code="STUDENT_NO_NOT_ALLOWED",
            status_code=403,
        )


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    """学生自助注册：创建「学生用户」账号并直接签发令牌。

    学号/工号唯一；并发下由数据库唯一约束兜底，重复提交返回 409 而不是 500。
    注册前先按 A2 策略校验：自助注册开关与可选学籍白名单。
    """
    _ensure_registration_allowed(payload.student_no)

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
    return TokenResponse(
        access_token=create_access_token(
            str(user.id), user.role, user.token_version or 0
        )
    )


def change_password(
    db: Session, user: User, payload: PasswordChangeRequest
) -> TokenResponse:
    """B1：本人自助修改密码，并递增 token 版本使旧令牌失效。

    - 必须校验旧密码（防止令牌被盗后直接改密）；
    - 新密码不能与原密码相同；
    - 成功后返回新令牌，当前会话可继续使用；其他设备的旧令牌立即 401。
    - 审计只记录“已修改”，绝不记录密码或哈希。
    """
    if not verify_password(payload.old_password, user.password_hash):
        raise BusinessError(
            "原密码错误",
            code="INVALID_OLD_PASSWORD",
            status_code=400,
        )
    if payload.old_password == payload.new_password:
        raise BusinessError(
            "新密码不能与原密码相同",
            code="PASSWORD_UNCHANGED",
            status_code=400,
        )

    user.password_hash = hash_password(payload.new_password)
    user.token_version = (user.token_version or 0) + 1
    audit_service.record(
        db,
        operator_id=user.id,
        action_type="PASSWORD_CHANGED",
        target_type="USER",
        target_id=user.id,
        reason="用户自助修改密码",
    )
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(
            str(user.id), user.role, user.token_version
        )
    )


def logout(db: Session, user: User) -> None:
    """登出：递增令牌版本，使当前及所有旧令牌立即失效。

    客户端随后清除本地凭据；服务端不保存会话，靠 token_version 做撤销。
    """
    user.token_version = (user.token_version or 0) + 1
    audit_service.record(
        db,
        operator_id=user.id,
        action_type="LOGOUT",
        target_type="USER",
        target_id=user.id,
        reason="用户主动退出登录",
    )
    db.commit()


def _lock_remaining_minutes(locked_until: datetime, now: datetime) -> int:
    seconds = max(0.0, (locked_until - now).total_seconds())
    return max(1, int((seconds + 59) // 60))


def _normalize_ip(client_ip: str | None) -> str:
    """统一 IP 取值：缺省为 "unknown"，并截断到列宽（IPv6 最长 45）。"""
    return (client_ip or "unknown").strip()[:45] or "unknown"


def _load_login_attempt(
    db: Session, student_no: str, client_ip: str, now: datetime
) -> LoginAttempt | None:
    """读取「学号 + IP」的登录失败记录；仍在锁定期则直接拒绝，过期则清零。

    使用行锁串行化同一组合的并发失败请求；行不存在时的并发插入由
    ``_commit_login_failure`` 捕获唯一键冲突后重试。
    """
    attempt = db.scalar(
        select(LoginAttempt)
        .where(
            LoginAttempt.student_no == student_no,
            LoginAttempt.ip == client_ip,
        )
        .with_for_update()
    )
    if attempt is None:
        return None
    if attempt.locked_until is not None:
        if attempt.locked_until > now:
            minutes = _lock_remaining_minutes(attempt.locked_until, now)
            raise BusinessError(
                f"登录失败次数过多，请 {minutes} 分钟后重试",
                code="ACCOUNT_LOCKED",
                status_code=429,
            )
        # 锁定期已过：重新开始计数
        attempt.failed_count = 0
        attempt.first_failed_at = None
        attempt.locked_until = None
    return attempt


def _register_login_failure(
    db: Session,
    student_no: str,
    client_ip: str,
    attempt: LoginAttempt | None,
    user_id: int | None,
    now: datetime,
) -> datetime | None:
    """记录一次失败；达到阈值时设置锁定并写 ``LOGIN_LOCKED`` 审计。"""
    if attempt is None:
        attempt = LoginAttempt(
            student_no=student_no, ip=client_ip, failed_count=0
        )
        db.add(attempt)

    window_start = now - timedelta(minutes=settings.login_failure_window_minutes)
    if attempt.first_failed_at is None or attempt.first_failed_at < window_start:
        attempt.failed_count = 0
        attempt.first_failed_at = now

    attempt.failed_count = (attempt.failed_count or 0) + 1
    attempt.updated_at = now

    locked_until: datetime | None = None
    if attempt.failed_count >= settings.login_max_failures:
        locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        attempt.locked_until = locked_until
        audit_service.record(
            db,
            operator_id=user_id,
            action_type="LOGIN_LOCKED",
            target_type="USER",
            target_id=user_id,
            reason=(
                f"学号「{student_no}」连续失败 {attempt.failed_count} 次，"
                f"锁定至 {locked_until:%Y-%m-%d %H:%M:%S}"
            ),
        )
    return locked_until


def _commit_login_failure(
    db: Session,
    student_no: str,
    client_ip: str,
    attempt: LoginAttempt | None,
    user_id: int | None,
    now: datetime,
) -> datetime | None:
    """写入失败审计与计数；并发首次插入冲突时重试一次。

    两个请求同时为同一个“尚无记录”的学号写失败时，唯一键会拒绝后提交者。
    这里回滚后重新读取记录（此时行已存在）并再记一次，避免把并发失败变成 500。
    """
    current = attempt
    for retry in range(2):
        try:
            audit_service.record(
                db,
                operator_id=user_id,
                action_type="LOGIN_FAILED",
                target_type="USER",
                target_id=user_id,
                reason=f"学号「{student_no}」凭证错误",
            )
            locked_until = _register_login_failure(
                db, student_no, client_ip, current, user_id, now
            )
            db.commit()
            return locked_until
        except IntegrityError:
            db.rollback()
            if retry == 1:
                raise
            # 并发请求已创建该行；重新加锁读取后重试
            current = _load_login_attempt(db, student_no, client_ip, now)
    return None


def cleanup_login_attempts(db: Session, now: datetime | None = None) -> int:
    """Q4-02(E)：删除超过保留期的登录失败计数，返回删除行数。

    不存在的学号也会计数（防枚举），因此该表必须定期清理；保留期足够覆盖
    锁定窗口与事后审计排查即可，业务数据不受影响。
    """
    cutoff = (now or time_utils.now()) - timedelta(
        days=settings.login_attempt_retention_days
    )
    result = db.execute(
        delete(LoginAttempt).where(LoginAttempt.updated_at < cutoff)
    )
    db.commit()
    return result.rowcount or 0


def login(
    db: Session, payload: LoginRequest, client_ip: str | None = None
) -> TokenResponse:
    """FR-040：学号/工号 + 密码登录，签发 JWT，并记录登录审计（NFR-009）。

    登录成功与失败均写审计：成功记 ``LOGIN_SUCCESS``；凭证错误 / 账户停用记
    ``LOGIN_FAILED``（不记录密码，仅记学号与失败原因，供安全审计与暴力探测排查）。

    B5：同一「学号 + 客户端 IP」在窗口内连续失败达到上限后临时锁定；不存在的
    学号同样计数，避免通过“是否锁定”判断账号是否存在。锁定期间返回 429，
    不校验密码。锁定按 IP 隔离，他人无法从其他地址把受害者账号锁死（Q4-02）。
    """
    student_no = payload.student_no.strip()
    client_ip = _normalize_ip(client_ip)
    now = time_utils.now()
    attempt = _load_login_attempt(db, student_no, client_ip, now)
    user = db.scalar(select(User).where(User.student_no == student_no))

    if user is None or not verify_password(payload.password, user.password_hash):
        locked_until = _commit_login_failure(
            db,
            student_no,
            client_ip,
            attempt,
            user.id if user is not None else None,
            now,
        )
        if locked_until is not None:
            minutes = _lock_remaining_minutes(locked_until, now)
            raise BusinessError(
                f"登录失败次数过多，请 {minutes} 分钟后重试",
                code="ACCOUNT_LOCKED",
                status_code=429,
            )
        raise BusinessError(
            "学号或密码错误",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )

    if user.account_status == AccountStatus.DISABLED.value:
        # 正确密码但账户停用：不按“失败登录”计数，并清掉该学号的历史失败记录
        db.execute(
            delete(LoginAttempt).where(LoginAttempt.student_no == student_no)
        )
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

    # 登录成功：清空该学号在所有来源的失败计数（成功即证明账号归属）
    db.execute(
        delete(LoginAttempt).where(LoginAttempt.student_no == student_no)
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
    return TokenResponse(
        access_token=create_access_token(
            str(user.id), user.role, user.token_version or 0
        )
    )
