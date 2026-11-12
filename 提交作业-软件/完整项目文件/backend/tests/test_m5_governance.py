"""M5 用户与治理：用户资料/评价/投诉/黑名单 + 治理类定时任务（FR-040～FR-044）。"""

from datetime import date, datetime, time, timedelta

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    BlacklistMode,
    ComplaintStatus,
    ComplaintTargetType,
    ReservationStatus,
    Role,
)
from app.schemas.blacklist import BlacklistCreate
from app.schemas.complaint import ComplaintCreate, ComplaintHandle
from app.schemas.review import ReviewCreate
from app.schemas.user import UserUpdate
from app.services import (
    blacklist_service,
    complaint_service,
    notification_service,
    review_service,
    user_service,
)


@pytest.fixture(autouse=True)
def _disable_external_notifications(monkeypatch):
    """站内通知使用独立 MySQL 会话，测试中改为空操作。"""
    monkeypatch.setattr(
        notification_service, "notify_safe", lambda **kwargs: None
    )


def _error_of(func, *args, **kwargs) -> BusinessError:
    with pytest.raises(BusinessError) as exc:
        func(*args, **kwargs)
    return exc.value


# ---------------- M5 用户资料（FR-040） ----------------


def test_update_my_profile_changes_contact_only(db, make_user) -> None:
    user = make_user(name="李四", contact=None)

    updated = user_service.update_my_profile(
        db, user, UserUpdate(contact="13800000000")
    )

    assert updated.contact == "13800000000"
    assert updated.name == "李四"
    assert updated.role == Role.STUDENT.value


def test_list_users_pagination(db, make_user) -> None:
    for index in range(3):
        make_user(student_no=f"S100{index}")

    first = user_service.list_users(db, page=1, page_size=2)
    second = user_service.list_users(db, page=2, page_size=2)

    assert first.total == 3
    assert len(first.items) == 2
    assert len(second.items) == 1
    assert first.items[0].student_no == "S1000"


# ---------------- M5 评价（FR-041 / BR-013） ----------------


def test_review_requires_completed_reservation(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_user(student_no="S2001")
    reservation = make_reservation(
        student.id, seat.id, status=ReservationStatus.PENDING.value
    )

    error = _error_of(
        review_service.create_review,
        db,
        student.id,
        ReviewCreate(reservation_id=reservation.id, score=5, content="很好"),
    )

    assert error.code == "REVIEW_NOT_ALLOWED"
    assert error.status_code == 409


def test_review_rejects_other_users_reservation(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    owner = make_user(student_no="S2002")
    other = make_user(student_no="S2003")
    reservation = make_reservation(
        owner.id, seat.id, status=ReservationStatus.COMPLETED.value
    )

    error = _error_of(
        review_service.create_review,
        db,
        other.id,
        ReviewCreate(reservation_id=reservation.id, score=4),
    )

    assert error.code == "REVIEW_NOT_OWNER"
    assert error.status_code == 403


def test_review_can_only_be_submitted_once(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_user(student_no="S2004")
    reservation = make_reservation(
        student.id, seat.id, status=ReservationStatus.COMPLETED.value
    )
    review_service.create_review(
        db, student.id, ReviewCreate(reservation_id=reservation.id, score=5)
    )

    error = _error_of(
        review_service.create_review,
        db,
        student.id,
        ReviewCreate(reservation_id=reservation.id, score=4),
    )

    assert error.code == "REVIEW_ALREADY_EXISTS"


def test_review_success(db, make_room, make_seat, make_user, make_reservation) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_user(student_no="S2005")
    reservation = make_reservation(
        student.id, seat.id, status=ReservationStatus.COMPLETED.value
    )

    review = review_service.create_review(
        db, student.id, ReviewCreate(reservation_id=reservation.id, score=5, content="安静")
    )

    assert review.id is not None
    assert review.score == 5
    page = review_service.list_my_reviews(db, student.id, 1, 20)
    assert page.total == 1


# ---------------- M5 投诉（FR-042/FR-043 / 状态机 SM-04） ----------------


def test_complaint_target_must_exist(db, make_user) -> None:
    student = make_user(student_no="S3001")

    error = _error_of(
        complaint_service.create_complaint,
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.SEAT, target_id=999, content="座位损坏"
        ),
    )

    assert error.code == "COMPLAINT_TARGET_NOT_FOUND"
    assert error.status_code == 404


def test_complaint_state_machine_full_flow(db, make_user, make_room) -> None:
    student = make_user(student_no="S3002")
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3002")
    room = make_room()

    complaint = complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM, target_id=room.id, content="空调太冷"
        ),
    )
    assert complaint.status == ComplaintStatus.PENDING.value

    # 待处理 → 已处理 不是合法迁移（必须先进“处理中”）
    error = _error_of(
        complaint_service.handle_complaint,
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.RESOLVED, handle_note="直接处理"),
    )
    assert error.code == "COMPLAINT_STATE_INVALID"
    assert error.status_code == 409

    processing = complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="已受理"),
    )
    assert processing.status == ComplaintStatus.PROCESSING.value
    assert processing.handler_id == admin.id
    assert processing.handled_at is not None

    resolved = complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.RESOLVED, handle_note="已调整空调"),
    )
    assert resolved.status == ComplaintStatus.RESOLVED.value

    # ST-063：管理员不能直接把「已处理」置为「已关闭」
    error = _error_of(
        complaint_service.handle_complaint,
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.CLOSED, handle_note="管理员关闭"),
    )
    assert error.code == "COMPLAINT_STATE_INVALID"

    # 只有投诉人本人可以确认关闭
    other = make_user(student_no="S3999")
    error = _error_of(
        complaint_service.confirm_close, db, other.id, complaint.id
    )
    assert error.code == "COMPLAINT_NOT_OWNER"

    closed = complaint_service.confirm_close(db, student.id, complaint.id)
    assert closed.status == ComplaintStatus.CLOSED.value

    # 终态不可再变更
    error = _error_of(
        complaint_service.handle_complaint,
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="重开"),
    )
    assert error.code == "COMPLAINT_STATE_INVALID"
    error = _error_of(
        complaint_service.confirm_close, db, student.id, complaint.id
    )
    assert error.code == "COMPLAINT_STATE_INVALID"

    # 受理、处理、投诉人确认各 1 条审计
    assert (
        db.query(AuditLog).filter(AuditLog.target_type == "COMPLAINT").count() == 3
    )


def test_complaint_rejects_blank_content_and_handle_note(
    db, make_user, make_room
) -> None:
    student = make_user(student_no="S3006")
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3006")
    room = make_room()

    error = _error_of(
        complaint_service.create_complaint,
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room.id,
            content="   ",
        ),
    )
    assert error.code == "COMPLAINT_CONTENT_REQUIRED"
    assert error.status_code == 422

    complaint = complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM,
            target_id=room.id,
            content="空调太冷",
        ),
    )
    error = _error_of(
        complaint_service.handle_complaint,
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="   "),
    )
    assert error.code == "COMPLAINT_NOTE_REQUIRED"
    assert error.status_code == 422
    db.refresh(complaint)
    assert complaint.status == ComplaintStatus.PENDING.value


def test_complaint_can_be_rejected(db, make_user, make_room) -> None:
    student = make_user(student_no="S3003")
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3003")
    room = make_room()
    complaint = complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM, target_id=room.id, content="无关投诉"
        ),
    )

    rejected = complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.REJECTED, handle_note="内容不实"),
    )

    assert rejected.status == ComplaintStatus.REJECTED.value


def test_close_stale_complaints(db, make_user, make_room) -> None:
    student = make_user(student_no="S3004")
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3004")
    room = make_room()
    complaint = complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM, target_id=room.id, content="空调太冷"
        ),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="已受理"),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.RESOLVED, handle_note="已处理"),
    )
    # 把处理时间推到关闭期限之前
    complaint.handled_at = datetime.now() - timedelta(
        days=settings.complaint_close_days + 1
    )
    db.commit()

    closed = complaint_service.close_stale(db)

    assert closed == 1
    db.refresh(complaint)
    assert complaint.status == ComplaintStatus.CLOSED.value


def test_close_stale_keeps_recently_resolved(db, make_user, make_room) -> None:
    student = make_user(student_no="S3005")
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3005")
    room = make_room()
    complaint = complaint_service.create_complaint(
        db,
        student.id,
        ComplaintCreate(
            target_type=ComplaintTargetType.ROOM, target_id=room.id, content="噪声"
        ),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="已受理"),
    )
    complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.RESOLVED, handle_note="已处理"),
    )

    assert complaint_service.close_stale(db) == 0


# ---------------- M5 黑名单（FR-044 / BR-009 / BR-010） ----------------


def test_manual_blacklist_restricts_then_release_restores(db, make_user) -> None:
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4001")
    student = make_user(student_no="S4001")

    entry = blacklist_service.add_entry(
        db,
        admin,
        BlacklistCreate(
            user_id=student.id,
            reason="多次占座",
            expire_at=datetime.now() + timedelta(days=3),
        ),
    )

    db.refresh(student)
    assert entry.mode == BlacklistMode.MANUAL.value
    assert student.account_status == AccountStatus.RESTRICTED.value

    released = blacklist_service.release_entry(
        db, admin, entry.id, "申诉通过，提前解除"
    )

    assert released.released_at is not None
    assert released.release_reason == "申诉通过，提前解除"
    db.refresh(student)
    assert student.account_status == AccountStatus.NORMAL.value


def test_blacklist_rejects_duplicate_active_entry(db, make_user) -> None:
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4002")
    student = make_user(student_no="S4002")
    blacklist_service.add_entry(
        db, admin, BlacklistCreate(user_id=student.id, reason="首次限制")
    )

    error = _error_of(
        blacklist_service.add_entry,
        db,
        admin,
        BlacklistCreate(user_id=student.id, reason="重复限制"),
    )

    assert error.code == "BLACKLIST_ALREADY_ACTIVE"
    assert error.status_code == 409


def test_blacklist_expire_must_be_future(db, make_user) -> None:
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4003")
    student = make_user(student_no="S4003")

    error = _error_of(
        blacklist_service.add_entry,
        db,
        admin,
        BlacklistCreate(
            user_id=student.id,
            reason="过期时间不合法",
            expire_at=datetime.now() - timedelta(days=1),
        ),
    )

    assert error.code == "BLACKLIST_EXPIRE_INVALID"
    assert error.status_code == 422


def test_blacklist_release_twice_rejected(db, make_user) -> None:
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4004")
    student = make_user(student_no="S4004")
    entry = blacklist_service.add_entry(
        db, admin, BlacklistCreate(user_id=student.id, reason="限制")
    )
    blacklist_service.release_entry(db, admin, entry.id, "首次解除")

    error = _error_of(
        blacklist_service.release_entry, db, admin, entry.id, "重复解除"
    )

    assert error.code == "BLACKLIST_ALREADY_RELEASED"


def test_threshold_auto_restriction_is_idempotent(db, make_user) -> None:
    student = make_user(
        student_no="S4005", violation_count=settings.violation_threshold
    )

    entry = blacklist_service.restrict_if_threshold(db, student.id)

    assert entry is not None
    assert entry.mode == BlacklistMode.AUTO.value
    assert entry.expire_at is not None
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value
    # 幂等：已存在有效限制时不重复创建
    assert blacklist_service.restrict_if_threshold(db, student.id) is None


def test_threshold_not_reached_no_restriction(db, make_user) -> None:
    student = make_user(
        student_no="S4006", violation_count=settings.violation_threshold - 1
    )

    assert blacklist_service.restrict_if_threshold(db, student.id) is None
    db.refresh(student)
    assert student.account_status == AccountStatus.NORMAL.value


def test_release_expired_skips_manual_entries(db, make_user) -> None:
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4007")
    student = make_user(student_no="S4007")
    entry = blacklist_service.add_entry(
        db,
        admin,
        BlacklistCreate(
            user_id=student.id,
            reason="手动限制",
            expire_at=datetime.now() + timedelta(days=1),
        ),
    )
    # 手动限制即使过了期限，也不得由系统自动解除（BR-010）
    # 注：库层有 ck_blacklist_expire 约束，不能把 expire_at 改到 start_at 之前；
    # 这里通过传入“未来的 now”模拟时间推进。
    later = datetime.now() + timedelta(days=2)

    assert blacklist_service.release_expired(db, now=later) == 0
    db.refresh(entry)
    assert entry.released_at is None
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value


def test_expired_manual_entry_remains_active_until_released(db, make_user) -> None:
    """ST-042：手动限制到期后系统不得自动解除，也不能被新限制绕过。"""
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4009")
    student = make_user(
        student_no="S4009", violation_count=settings.violation_threshold
    )
    entry = blacklist_service.add_entry(
        db,
        admin,
        BlacklistCreate(
            user_id=student.id,
            reason="手动限制",
            expire_at=datetime.now() + timedelta(days=1),
        ),
    )
    later = datetime.now() + timedelta(days=2)

    # ST-042 只解除自动限制；手动记录保持未解除
    assert blacklist_service.release_expired(db, now=later) == 0
    db.refresh(entry)
    assert entry.released_at is None

    # 到期后仍是生效中的限制：不得重复加入，也不得再创建自动限制
    error = _error_of(
        blacklist_service.add_entry,
        db,
        admin,
        BlacklistCreate(user_id=student.id, reason="再次限制"),
    )
    assert error.code == "BLACKLIST_ALREADY_ACTIVE"
    assert blacklist_service.restrict_if_threshold(db, student.id, now=later) is None
    db.refresh(student)
    assert student.account_status == AccountStatus.RESTRICTED.value

    # 只有管理员显式解除后才恢复
    blacklist_service.release_entry(db, admin, entry.id, "管理员核实后解除")
    db.refresh(student)
    assert student.account_status == AccountStatus.NORMAL.value


def test_user_read_exposes_auto_restrict_until(db, make_user) -> None:
    auto_user = make_user(
        student_no="S4010", violation_count=settings.violation_threshold
    )
    entry = blacklist_service.restrict_if_threshold(db, auto_user.id)
    assert entry is not None

    profile = user_service.to_user_read(db, auto_user)
    assert profile.restrict_until == entry.expire_at

    admin = make_user(role=Role.ADMIN.value, student_no="ADM4010")
    manual_user = make_user(student_no="S4011")
    blacklist_service.add_entry(
        db,
        admin,
        BlacklistCreate(
            user_id=manual_user.id,
            reason="手动限制",
            expire_at=datetime.now() + timedelta(days=3),
        ),
    )

    manual_profile = user_service.to_user_read(db, manual_user)
    # 手动限制不会到期自动解除，不应给出“预计解除时间”
    assert manual_profile.restrict_until is None
    assert manual_profile.account_status == AccountStatus.RESTRICTED.value


def test_release_expired_releases_auto_entries(db, make_user) -> None:
    student = make_user(
        student_no="S4008", violation_count=settings.violation_threshold
    )
    entry = blacklist_service.restrict_if_threshold(db, student.id)
    assert entry is not None
    later = datetime.now() + timedelta(days=settings.restriction_days + 1)

    assert blacklist_service.release_expired(db, now=later) == 1
    db.refresh(entry)
    assert entry.released_at is not None
    db.refresh(student)
    assert student.account_status == AccountStatus.NORMAL.value


