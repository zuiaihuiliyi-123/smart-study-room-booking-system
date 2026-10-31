"""M5 黑名单与账户受限（FR-044，BR-009/BR-010，SM-03 的 ST-040～ST-043/ST-047）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.blacklist import BlacklistCreate, BlacklistRead
from app.schemas.common import PageResult
from app.services import audit_service
from app.utils.pagination import to_offset


def _active_entries(db: Session, user_id: int, now: datetime) -> list[BlacklistEntry]:
    """有效限制：未解除，且未到期（无期限视为永久有效）。"""
    stmt = select(BlacklistEntry).where(
        BlacklistEntry.user_id == user_id,
        BlacklistEntry.released_at.is_(None),
        (BlacklistEntry.expire_at.is_(None)) | (BlacklistEntry.expire_at > now),
    )
    return list(db.scalars(stmt))


def _sync_account_status(db: Session, user: User, now: datetime) -> str:
    """按“是否仍有有效限制”同步账户状态。

    - 仍有限制 → 受限（ST-040/ST-041）；
    - 无限制 → 由“受限”恢复为“正常”（ST-042/ST-043）；
    - “停用”不经由黑名单改变（ST-044/ST-046 由管理员显式操作）。
    """
    # 会话为 autoflush=False：先落盘本事务内的新增/变更，确保下面的查询看得到
    db.flush()
    still_restricted = bool(_active_entries(db, user.id, now))
    if still_restricted:
        if user.account_status == AccountStatus.NORMAL.value:
            user.account_status = AccountStatus.RESTRICTED.value
    elif user.account_status == AccountStatus.RESTRICTED.value:
        user.account_status = AccountStatus.NORMAL.value
    return user.account_status


def list_entries(
    db: Session,
    page: int,
    page_size: int,
    *,
    state: str | None = None,
    mode: str | None = None,
    user_id: int | None = None,
    now: datetime | None = None,
) -> PageResult[BlacklistRead]:
    """M5 / FR-044：管理员查询黑名单记录（含历史记录，按开始时间倒序）。"""
    current = now or datetime.now()
    conditions: list = []
    if state == "生效中":
        conditions.append(BlacklistEntry.released_at.is_(None))
        conditions.append(
            (BlacklistEntry.expire_at.is_(None))
            | (BlacklistEntry.expire_at > current)
        )
    elif state == "已解除":
        conditions.append(BlacklistEntry.released_at.is_not(None))
    elif state == "已过期":
        conditions.append(BlacklistEntry.released_at.is_(None))
        conditions.append(BlacklistEntry.expire_at.is_not(None))
        conditions.append(BlacklistEntry.expire_at <= current)
    if mode:
        conditions.append(BlacklistEntry.mode == mode)
    if user_id is not None:
        conditions.append(BlacklistEntry.user_id == user_id)

    total = (
        db.scalar(
            select(func.count())
            .select_from(BlacklistEntry)
            .where(*conditions)
        )
        or 0
    )
    rows = db.scalars(
        select(BlacklistEntry)
        .where(*conditions)
        .order_by(BlacklistEntry.start_at.desc(), BlacklistEntry.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[BlacklistRead](
        items=[BlacklistRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def add_entry(db: Session, admin: User, payload: BlacklistCreate) -> BlacklistEntry:
    """M5 / FR-044：管理员手动加入黑名单（必须记录原因与期限）。

    - 手动记录到期后**不得由系统自动解除**（BR-010），只能由管理员 ST-043 解除；
    - 同一用户不允许存在两条并行的有效限制。
    """
    now = datetime.now()
    user = db.get(User, payload.user_id)
    if user is None:
        raise BusinessError("用户不存在", code="USER_NOT_FOUND", status_code=404)

    if _active_entries(db, user.id, now):
        raise BusinessError(
            "该用户已存在有效的限制记录", code="BLACKLIST_ALREADY_ACTIVE", status_code=409
        )

    if payload.expire_at is not None and payload.expire_at <= now:
        raise BusinessError(
            "限制期限必须晚于当前时间", code="BLACKLIST_EXPIRE_INVALID", status_code=422
        )

    entry = BlacklistEntry(
        user_id=user.id,
        reason=payload.reason,
        mode=BlacklistMode.MANUAL.value,
        start_at=now,
        expire_at=payload.expire_at,
        operator_id=admin.id,
    )
    db.add(entry)
    _sync_account_status(db, user, now)

    audit_service.record(
        db,
        operator_id=admin.id,
        action_type="BLACKLIST_ADD",
        target_type="USER",
        target_id=user.id,
        reason=payload.reason,
        before_value=AccountStatus.NORMAL.value,
        after_value=AccountStatus.RESTRICTED.value,
    )
    db.commit()
    db.refresh(entry)
    return entry


def release_entry(
    db: Session, admin: User, entry_id: int, reason: str
) -> BlacklistEntry:
    """M5 / FR-044 / ST-043：管理员手动解除黑名单。

    - 必须填写解除原因（DR-008 的 release_reason，库层有 CHECK 约束）；
    - 解除后若该用户已无其它有效限制，账户由“受限”恢复为“正常”。
    """
    cleaned_reason = (reason or "").strip()
    if not cleaned_reason:
        raise BusinessError(
            "解除黑名单必须填写原因",
            code="BLACKLIST_RELEASE_REASON_REQUIRED",
            status_code=422,
        )

    now = datetime.now()
    entry = db.get(BlacklistEntry, entry_id)
    if entry is None:
        raise BusinessError(
            "黑名单记录不存在", code="BLACKLIST_NOT_FOUND", status_code=404
        )
    if entry.released_at is not None:
        raise BusinessError(
            "该限制已解除，无需重复操作",
            code="BLACKLIST_ALREADY_RELEASED",
            status_code=409,
        )

    entry.released_at = now
    entry.release_reason = cleaned_reason
    user = db.get(User, entry.user_id)
    if user is not None:
        _sync_account_status(db, user, now)
        audit_service.record(
            db,
            operator_id=admin.id,
            action_type="BLACKLIST_RELEASE",
            target_type="USER",
            target_id=user.id,
            reason=cleaned_reason,
            before_value=AccountStatus.RESTRICTED.value,
            after_value=user.account_status,
        )
    db.commit()
    db.refresh(entry)
    return entry


def restrict_if_threshold(
    db: Session, user_id: int, now: datetime | None = None
) -> BlacklistEntry | None:
    """BR-009 / BR-010 / ST-040：有效违约次数达到阈值时自动限制。

    由自动违约任务调用；幂等——已有有效限制时不重复创建，返回 None。
    """
    now = now or datetime.now()
    user = db.get(User, user_id)
    if user is None:
        return None

    # 以违约记录数回写累计次数，保证计数与记录一致（ST-034 幂等）
    record_count = (
        db.scalar(
            select(func.count())
            .select_from(ViolationRecord)
            .where(ViolationRecord.user_id == user_id)
        )
        or 0
    )
    # 计数与明细取较大值：历史数据可能已回写计数但明细尚未补齐
    count = max(user.violation_count, record_count)
    user.violation_count = count

    if count < settings.violation_threshold:
        return None
    if _active_entries(db, user.id, now):
        return None

    entry = BlacklistEntry(
        user_id=user.id,
        reason=f"累计有效违约达到 {settings.violation_threshold} 次（BR-009）",
        mode=BlacklistMode.AUTO.value,
        start_at=now,
        expire_at=now + timedelta(days=settings.restriction_days),
        operator_id=None,
    )
    db.add(entry)
    _sync_account_status(db, user, now)

    audit_service.record(
        db,
        operator_id=None,
        action_type="BLACKLIST_AUTO_RESTRICT",
        target_type="USER",
        target_id=user.id,
        reason=entry.reason,
        before_value=AccountStatus.NORMAL.value,
        after_value=AccountStatus.RESTRICTED.value,
    )
    db.commit()
    db.refresh(entry)
    return entry


def release_expired(db: Session, now: datetime | None = None) -> int:
    """ST-042：自动限制到期后解除账户受限。

    只处理 mode=自动 的记录；管理员手动加入的限制到期后**不自动解除**（BR-010），
    必须由管理员按 ST-043 显式解除。返回本次解除的记录数。
    """
    current = now or datetime.now()
    stmt = select(BlacklistEntry).where(
        BlacklistEntry.mode == BlacklistMode.AUTO.value,
        BlacklistEntry.released_at.is_(None),
        BlacklistEntry.expire_at.is_not(None),
        BlacklistEntry.expire_at <= current,
    )
    entries = list(db.scalars(stmt))
    if not entries:
        return 0

    touched: set[int] = set()
    for entry in entries:
        entry.released_at = current
        entry.release_reason = "自动限制期限届满，系统自动解除（ST-042）"
        touched.add(entry.user_id)

    for user_id in touched:
        user = db.get(User, user_id)
        if user is not None:
            _sync_account_status(db, user, current)

    db.commit()
    return len(entries)

