"""白盒测试：黑名单列表筛选、加入/解除校验、阈值限制与到期释放分支。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode, Role, ViolationType
from app.models.violation import ViolationRecord
from app.schemas.blacklist import BlacklistCreate
from app.services import blacklist_service, notification_service
from app.utils import time_utils

NOW = datetime(2026, 11, 24, 10, 0)


@pytest.fixture(autouse=True)
def _silence_and_freeze(monkeypatch):
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)
    monkeypatch.setattr(time_utils, "now", lambda: NOW)


def _entry(
    db,
    user_id: int,
    *,
    mode: str = BlacklistMode.MANUAL.value,
    expire_at: datetime | None = None,
    released_at: datetime | None = None,
    active: bool = True,
) -> BlacklistEntry:
    entry = BlacklistEntry(
        user_id=user_id,
        reason="白盒测试",
        mode=mode,
        start_at=NOW - timedelta(days=30),
        expire_at=expire_at,
        released_at=released_at,
        release_reason="解除" if released_at else None,
        active_user_id=user_id if active and released_at is None else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def test_list_entries_state_mode_and_user_filters(db, make_user) -> None:
    student = make_user(student_no="WBL001")
    other = make_user(student_no="WBL002")

    manual = _entry(db, student.id, expire_at=NOW + timedelta(days=3))
    auto_expired = _entry(
        db,
        student.id,
        mode=BlacklistMode.AUTO.value,
        expire_at=NOW - timedelta(days=1),
        active=False,  # 已到期但尚未由任务清理的有效标记
    )
    released = _entry(
        db,
        other.id,
        released_at=NOW - timedelta(days=2),
    )

    active = blacklist_service.list_entries(db, 1, 10, state="生效中", now=NOW)
    assert {item.id for item in active.items} == {manual.id}

    expired = blacklist_service.list_entries(db, 1, 10, state="已过期", now=NOW)
    assert {item.id for item in expired.items} == {auto_expired.id}

    released_page = blacklist_service.list_entries(db, 1, 10, state="已解除", now=NOW)
    assert {item.id for item in released_page.items} == {released.id}

    auto_page = blacklist_service.list_entries(
        db, 1, 10, mode=BlacklistMode.AUTO.value, now=NOW
    )
    assert {item.id for item in auto_page.items} == {auto_expired.id}

    by_user = blacklist_service.list_entries(db, 1, 10, user_id=student.id, now=NOW)
    assert {item.id for item in by_user.items} == {manual.id, auto_expired.id}

    empty = blacklist_service.list_entries(db, 1, 10, user_id=9999, now=NOW)
    assert empty.total == 0
    assert empty.items == []


def test_add_entry_validations(db, make_user) -> None:
    admin = make_user(student_no="WBL101", role=Role.ADMIN.value)
    student = make_user(student_no="WBL102")
    other_admin = make_user(student_no="WBL103", role=Role.ADMIN.value)

    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db, admin, BlacklistCreate(user_id=student.id, reason=" ")
        )
    _assert_code(exc, "BLACKLIST_REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db, admin, BlacklistCreate(user_id=9999, reason="测试")
        )
    _assert_code(exc, "USER_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db, admin, BlacklistCreate(user_id=admin.id, reason="测试")
        )
    _assert_code(exc, "SELF_OPERATION_FORBIDDEN")

    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db, admin, BlacklistCreate(user_id=other_admin.id, reason="测试")
        )
    _assert_code(exc, "BLACKLIST_TARGET_NOT_STUDENT")

    _entry(db, student.id)
    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db, admin, BlacklistCreate(user_id=student.id, reason="重复限制")
        )
    _assert_code(exc, "BLACKLIST_ALREADY_ACTIVE")

    fresh = make_user(student_no="WBL104")
    with pytest.raises(BusinessError) as exc:
        blacklist_service.add_entry(
            db,
            admin,
            BlacklistCreate(
                user_id=fresh.id,
                reason="过期时间",
                expire_at=NOW - timedelta(minutes=1),
            ),
        )
    _assert_code(exc, "BLACKLIST_EXPIRE_INVALID")


def test_add_entry_success_restricts_account(db, make_user) -> None:
    admin = make_user(student_no="WBL201", role=Role.ADMIN.value)
    student = make_user(student_no="WBL202")

    entry = blacklist_service.add_entry(
        db,
        admin,
        BlacklistCreate(
            user_id=student.id,
            reason="多次占座不签到",
            expire_at=NOW + timedelta(days=7),
        ),
    )

    assert entry.mode == BlacklistMode.MANUAL.value
    assert entry.active_user_id == student.id
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value


def test_release_entry_validations_and_restore(db, make_user) -> None:
    admin = make_user(student_no="WBL301", role=Role.ADMIN.value)
    student = make_user(
        student_no="WBL302", account_status=AccountStatus.RESTRICTED.value
    )
    entry = _entry(db, student.id)

    with pytest.raises(BusinessError) as exc:
        blacklist_service.release_entry(db, admin, entry.id, " ")
    _assert_code(exc, "BLACKLIST_RELEASE_REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        blacklist_service.release_entry(db, admin, 9999, "解除")
    _assert_code(exc, "BLACKLIST_NOT_FOUND")

    released = blacklist_service.release_entry(db, admin, entry.id, "表现良好")
    assert released.released_at == NOW
    assert released.active_user_id is None
    db.refresh(student)
    assert student.account_status == AccountStatus.NORMAL.value

    with pytest.raises(BusinessError) as exc:
        blacklist_service.release_entry(db, admin, entry.id, "再次解除")
    _assert_code(exc, "BLACKLIST_ALREADY_RELEASED")


def test_release_one_of_two_keeps_account_restricted(db, make_user) -> None:
    admin = make_user(student_no="WBL401", role=Role.ADMIN.value)
    student = make_user(
        student_no="WBL402", account_status=AccountStatus.RESTRICTED.value
    )
    first = _entry(db, student.id)
    second = _entry(
        db,
        student.id,
        mode=BlacklistMode.AUTO.value,
        expire_at=NOW + timedelta(days=3),
        active=False,  # 历史数据允许多条，服务层只解除指定记录
    )

    blacklist_service.release_entry(db, admin, first.id, "先解除一条")

    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value
    assert second.released_at is None


def test_restrict_if_threshold_guards_and_success(db, make_user) -> None:
    admin = make_user(student_no="WBL501", role=Role.ADMIN.value)
    student = make_user(student_no="WBL502")

    assert blacklist_service.restrict_if_threshold(db, 9999, now=NOW) is None
    assert blacklist_service.restrict_if_threshold(db, admin.id, now=NOW) is None

    student.violation_count = 1
    db.commit()
    assert blacklist_service.restrict_if_threshold(db, student.id, now=NOW, commit=False) is None

    student.violation_count = 3
    db.commit()
    entry = blacklist_service.restrict_if_threshold(db, student.id, now=NOW)
    assert entry is not None
    assert entry.mode == BlacklistMode.AUTO.value
    assert entry.expire_at == NOW + timedelta(days=7)
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value

    # 已有有效限制时不重复创建
    assert blacklist_service.restrict_if_threshold(db, student.id, now=NOW) is None


def test_restrict_if_threshold_counts_records_after_last_auto_release(db, make_user) -> None:
    student = make_user(student_no="WBL601")
    _entry(
        db,
        student.id,
        mode=BlacklistMode.AUTO.value,
        expire_at=NOW - timedelta(days=20),
        released_at=NOW - timedelta(days=19),
        active=False,
    )
    for index in range(3):
        db.add(
            ViolationRecord(
                user_id=student.id,
                reservation_id=1000 + index,
                type=ViolationType.AUTO.value,
                reason="历史违约",
                created_at=NOW - timedelta(days=5),
            )
        )
    db.commit()

    entry = blacklist_service.restrict_if_threshold(db, student.id, now=NOW)

    assert entry is not None
    db.refresh(student)
    assert student.violation_count == 3


def test_restrict_if_threshold_concurrent_unique_conflict(db, make_user, monkeypatch) -> None:
    student = make_user(student_no="WBL701")
    _entry(db, student.id)
    student.violation_count = 3
    db.commit()

    # 模拟另一个事务已插入有效限制：查询时没看到，INSERT 撞唯一约束
    monkeypatch.setattr(blacklist_service, "_active_entries", lambda *a, **k: [])
    monkeypatch.setattr(blacklist_service, "_clear_stale_auto_keys", lambda *a, **k: None)

    assert blacklist_service.restrict_if_threshold(db, student.id, now=NOW) is None


def test_restrict_if_threshold_commit_false_flushes(db, make_user) -> None:
    student = make_user(student_no="WBL801")
    student.violation_count = 3
    db.commit()

    entry = blacklist_service.restrict_if_threshold(db, student.id, now=NOW, commit=False)
    assert entry is not None
    # commit=False 时只 flush：同一事务内立即可见
    assert db.scalar(select(BlacklistEntry).where(BlacklistEntry.id == entry.id)) is not None
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value


def test_release_expired_only_auto_and_resets_count(db, make_user) -> None:
    auto_user = make_user(
        student_no="WBL901",
        account_status=AccountStatus.RESTRICTED.value,
        violation_count=3,
    )
    manual_user = make_user(
        student_no="WBL902",
        account_status=AccountStatus.RESTRICTED.value,
        violation_count=3,
    )
    _entry(
        db,
        auto_user.id,
        mode=BlacklistMode.AUTO.value,
        expire_at=NOW - timedelta(minutes=1),
    )
    manual = _entry(
        db,
        manual_user.id,
        expire_at=NOW - timedelta(minutes=1),
    )

    assert blacklist_service.release_expired(db, now=NOW) == 1

    db.refresh(auto_user)
    db.refresh(manual_user)
    assert auto_user.account_status == AccountStatus.NORMAL.value
    assert auto_user.violation_count == 0
    assert manual.released_at is None
    assert manual_user.account_status == AccountStatus.RESTRICTED.value
    assert blacklist_service.release_expired(db, now=NOW) == 0
