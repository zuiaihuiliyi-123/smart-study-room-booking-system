"""M5 用户管理：本人资料与管理员用户查询（FR-040）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode, Role
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.user import AccountStatusUpdate, UserRead, UserUpdate
from app.services import audit_service
from app.utils import masking, time_utils
from app.utils.pagination import to_offset


def _restrict_until(
    db: Session, user_id: int, now: datetime | None = None
) -> datetime | None:
    """受限账户的预计解除时间（FR-044 / ST-040）。

    只有自动限制会到期解除（BR-010）；管理员手动限制须由管理员显式解除，
    因此不返回“自动解除时间”，避免界面给出错误的预计解除日期。
    """
    current = now or time_utils.now()
    stmt = select(BlacklistEntry.expire_at).where(
        BlacklistEntry.user_id == user_id,
        BlacklistEntry.released_at.is_(None),
        BlacklistEntry.mode == BlacklistMode.AUTO.value,
        BlacklistEntry.expire_at.is_not(None),
        BlacklistEntry.expire_at > current,
    )
    expiries = list(db.scalars(stmt).all())
    return min(expiries) if expiries else None


def to_user_read(db: Session, user: User, *, mask_contact: bool = False) -> UserRead:
    """把 ORM 用户转换为响应模型，并补齐黑名单相关的派生字段。

    ``mask_contact=True`` 时对联系方式做服务端脱敏（§5.6 / NFR-006）——
    管理员读取他人资料的路径必须置 True，本人读取本人资料置 False。
    """
    read = UserRead.model_validate(user).model_copy(
        update={"restrict_until": _restrict_until(db, user.id)}
    )
    if mask_contact:
        read.contact = masking.mask_contact(user.contact)
    return read


def update_my_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """M5 / FR-040：学生仅可修改联系方式。

    姓名、学号、角色、账户状态等身份字段在 schema 层已不可提交（BR-018：
    管理员亦不可修改用户身份信息，账户状态统一走 FR-044 黑名单）。
    """
    if "contact" in payload.model_fields_set:
        user.contact = payload.contact
        db.commit()
        db.refresh(user)
    return user


def list_users(
    db: Session,
    page: int,
    page_size: int,
    *,
    keyword: str | None = None,
    role: str | None = None,
    account_status: str | None = None,
    violation_min: int | None = None,
) -> PageResult[UserRead]:
    """M5 / FR-040：管理员查询用户列表与账户状态（分页，按 id 升序）。"""
    conditions: list = []
    if keyword:
        pattern = f"%{keyword.strip()}%"
        conditions.append(
            or_(User.name.like(pattern), User.student_no.like(pattern))
        )
    if role:
        conditions.append(User.role == role)
    if account_status:
        conditions.append(User.account_status == account_status)
    if violation_min is not None:
        conditions.append(User.violation_count >= violation_min)

    total = (
        db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    )
    rows = db.scalars(
        select(User)
        .where(*conditions)
        .order_by(User.id)
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[UserRead](
        items=[to_user_read(db, row, mask_contact=True) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def set_account_status(
    db: Session, user_id: int, payload: AccountStatusUpdate, operator_id: int
) -> User:
    """FR-040 / FR-044 / ST-044 / ST-045 / ST-046：管理员停用或恢复**学生**账户。

    - 账户状态维护只作用于学生；管理员 / 系统管理员账号由信息中心或系统管理员维护，
      业务管理员不能通过本接口停用、恢复或把管理员拉入黑名单；
    - 停用（→停用）：账户无法登录、无法创建预约；名下待使用预约按 ST-049 保持原状，
      本版只提示与记录，不自动取消（须由管理员按 FR-011 显式强制取消）。
    - 恢复（→正常）：从「停用」恢复为「正常」；若该用户仍有未解除的「受限」黑名单
      记录，恢复「正常」会与之冲突，此时应先解除黑名单（ST-043）而非直接恢复。
    操作必须记录操作者与原因（NFR-009）。
    """
    user = db.get(User, user_id)
    if user is None:
        raise BusinessError("用户不存在", code="USER_NOT_FOUND", status_code=404)

    # BR-018：账户状态维护只针对学生。管理员/系统管理员账号由信息中心或
    # 系统管理员维护，业务管理员不得停用/恢复；同时禁止任何角色操作自己。
    if user.id == operator_id:
        raise BusinessError(
            "不能停用或恢复自己的账户",
            code="SELF_OPERATION_FORBIDDEN",
            status_code=403,
        )
    if user.role != Role.STUDENT.value:
        raise BusinessError(
            "管理员账号由信息中心/系统管理员维护，业务管理员不能停用或恢复",
            code="TARGET_ROLE_NOT_ALLOWED",
            status_code=403,
        )

    new_status = payload.account_status
    old_status = user.account_status

    # 「受限」只能由黑名单/自动违约流程产生，且必须先解除限制，
    # 不能通过账户状态接口覆盖，否则会留下无法解释的账户状态。
    if old_status == AccountStatus.RESTRICTED.value:
        raise BusinessError(
            "该账户当前为「受限」，请先在黑名单管理中解除限制后再调整账户状态",
            code="ACCOUNT_STILL_RESTRICTED",
            status_code=409,
        )

    if new_status == old_status:
        raise BusinessError(
            f"账户当前已是「{old_status}」，无需重复操作",
            code="ACCOUNT_STATUS_NO_CHANGE",
            status_code=409,
        )

    # 恢复为「正常」时，若仍有未解除的「受限」黑名单，不可直接恢复（须先解除黑名单）
    if new_status == AccountStatus.NORMAL.value:
        active_restriction = db.scalar(
            select(BlacklistEntry)
            .where(
                BlacklistEntry.user_id == user_id,
                BlacklistEntry.released_at.is_(None),
            )
            .order_by(BlacklistEntry.id.desc())
        )
        if active_restriction is not None:
            raise BusinessError(
                "该账户仍有未解除的限制记录，请先在黑名单管理中解除后再恢复账户",
                code="ACCOUNT_STILL_RESTRICTED",
                status_code=409,
                details={
                    "blacklist_entry_id": active_restriction.id,
                    "mode": active_restriction.mode,
                },
            )

    user.account_status = new_status
    audit_service.record(
        db,
        operator_id=operator_id,
        action_type="ACCOUNT_STATUS_UPDATE",
        target_type="USER",
        target_id=user.id,
        reason=payload.reason,
        before_value=old_status,
        after_value=new_status,
    )
    db.commit()
    db.refresh(user)
    return user
