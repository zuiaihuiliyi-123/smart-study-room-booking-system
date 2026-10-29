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
from app.schemas.blacklist import BlacklistCreate
from app.schemas.common import PageResult
from app.services import audit_service
from app.utils import time_utils


def active_entry_for_user(
    db: Session, user_id: int
) -> BlacklistEntry | None:
    """当前生效中的限制记录（未解除即视为生效）。"""
    return db.scalar(
        select(BlacklistEntry)
        .where(
            BlacklistEntry.user_id == user_id,
            BlacklistEntry.released_at.is_(None),
        )
        .order_by(BlacklistEntry.id.desc())
    )


def list_entries(
    db: Session, page: int, page_size: int
) -> PageResult[BlacklistEntry]:
    """M5 / FR-044：管理员查询黑名单记录（含历史记录）。"""
    total = db.scalar(select(func.count()).select_from(BlacklistEntry)) or 0
    rows = list(
        db.scalars(
            select(BlacklistEntry)
            .order_by(BlacklistEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PageResult(items=rows, total=total, page=page, page_size=page_size)


def add_entry(
    db: Session, admin: User, payload: BlacklistCreate
) -> BlacklistEntry:
    """M5 / FR-044：管理员手动加入黑名单，必须记录原因与期限（ST-041）。

    手动加入的限制到期后**不会**被定时任务自动解除（BR-010），
    须管理员显式调用 ``release_entry``（ST-043）。
    """
    reason = (payload.reason or "").strip()
    if not reason:
        raise BusinessError(
            "请填写限制原因（必填）", code="REASON_REQUIRED", status_code=422
        )

    user = db.get(User, payload.user_id)
    if user is None:
        raise BusinessError("用户不存在", code="USER_NOT_FOUND", status_code=404)
    if active_entry_for_user(db, user.id) is not None:
        raise BusinessError(
            "该账户当前已处于受限状态，无需重复加入",
            code="ST-041",
            status_code=409,
            details={"user_id": user.id},
        )

    now = time_utils.now()
    expire_at = payload.expire_at or now + timedelta(days=settings.restriction_days)
    if expire_at <= now:
        raise BusinessError(
            "限制期限必须晚于当前时间",
            code="VALIDATION_ERROR",
            status_code=422,
        )

    entry = BlacklistEntry(
        user_id=user.id,
        reason=reason,
        mode=BlacklistMode.MANUAL.value,
        start_at=now,
        expire_at=expire_at,
        operator_id=admin.id,
    )
    db.add(entry)
    if user.account_status == AccountStatus.NORMAL.value:
        user.account_status = AccountStatus.RESTRICTED.value

    audit_service.record(
        db,
        operator_id=admin.id,
        action_type="BLACKLIST_JOIN",
        target_type="user",
        target_id=user.id,
        reason=reason,
        before_value=str({"account_status": AccountStatus.NORMAL.value}),
        after_value=str(
            {
                "account_status": user.account_status,
                "expire_at": entry.expire_at.isoformat() if entry.expire_at else None,
                "mode": entry.mode,
            }
        ),
    )
    db.commit()
    db.refresh(entry)
    return entry


def release_entry(
    db: Session, admin: User, entry_id: int, reason: str
) -> BlacklistEntry:
    """M5 / FR-044 / ST-043：管理员解除黑名单，必须填写原因。"""
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError(
            "请填写解除原因（必填）", code="REASON_REQUIRED", status_code=422
        )

    entry = db.get(BlacklistEntry, entry_id)
    if entry is None:
        raise BusinessError(
            "黑名单记录不存在", code="BLACKLIST_NOT_FOUND", status_code=404
        )
    if entry.released_at is not None:
        raise BusinessError(
            "该限制记录已解除", code="ST-043", status_code=409
        )

    now = time_utils.now()
    entry.released_at = now
    db.flush()

    user = db.get(User, entry.user_id)
    # 若仍有其他生效中的限制（含管理员手动限制），不得恢复为正常
    if (
        user is not None
        and user.account_status == AccountStatus.RESTRICTED.value
        and active_entry_for_user(db, user.id) is None
    ):
        user.account_status = AccountStatus.NORMAL.value

    audit_service.record(
        db,
        operator_id=admin.id,
        action_type="BLACKLIST_RELEASE",
        target_type="blacklist_entry",
        target_id=entry.id,
        reason=reason,
        before_value=str({"released_at": None}),
        after_value=str({"released_at": now.isoformat()}),
    )
    db.commit()
    db.refresh(entry)
    return entry


def restrict_if_threshold(
    db: Session, user_id: int, now: datetime | None = None
) -> BlacklistEntry | None:
    """BR-009 / ST-040：有效违约次数达到阈值时自动限制 7 天。

    以违约记录数回写 ``user.violation_count``，保证计数与记录一致。
    账户已受限（含手动限制）时不重复创建自动限制记录。
    """
    now = now or time_utils.now()
    user = db.get(User, user_id)
    if user is None:
        return None

    count = (
        db.scalar(
            select(func.count())
            .select_from(ViolationRecord)
            .where(ViolationRecord.user_id == user_id)
        )
        or 0
    )
    user.violation_count = count

    if count < settings.violation_threshold:
        return None
    if user.account_status != AccountStatus.NORMAL.value:
        return None

    user.account_status = AccountStatus.RESTRICTED.value
    entry = BlacklistEntry(
        user_id=user.id,
        reason=(
            f"累计有效违约次数达到阈值（{settings.violation_threshold} 次），"
            f"系统自动限制预约 {settings.restriction_days} 天"
        ),
        mode=BlacklistMode.AUTO.value,
        start_at=now,
        expire_at=now + timedelta(days=settings.restriction_days),
        operator_id=None,
    )
    db.add(entry)
    db.flush()
    return entry


def auto_release_expired(
    db: Session, now: datetime | None = None
) -> int:
    """ST-042：自动限制到期自动解除；管理员手动限制保留（BR-010）。"""
    now = now or time_utils.now()
    entries = list(
        db.scalars(
            select(BlacklistEntry).where(
                BlacklistEntry.mode == BlacklistMode.AUTO.value,
                BlacklistEntry.released_at.is_(None),
                BlacklistEntry.expire_at.is_not(None),
                BlacklistEntry.expire_at <= now,
            )
        ).all()
    )
    if not entries:
        return 0

    user_ids = {entry.user_id for entry in entries}
    for entry in entries:
        entry.released_at = now
    db.flush()

    for user_id in user_ids:
        user = db.get(User, user_id)
        if user is None:
            continue
        if (
            user.account_status == AccountStatus.RESTRICTED.value
            and active_entry_for_user(db, user_id) is None
        ):
            user.account_status = AccountStatus.NORMAL.value

    db.commit()
    return len(entries)
