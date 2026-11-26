"""M5 投诉单元测试：状态机、对象校验、超时关闭边界与处理说明。"""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import ComplaintStatus, ComplaintTargetType
from app.schemas.complaint import ComplaintHandle
from app.services import complaint_service


def test_admin_transition_table_invariants() -> None:
    transitions = complaint_service._ALLOWED_TRANSITIONS

    assert transitions[ComplaintStatus.PENDING.value] == {
        ComplaintStatus.PROCESSING.value,
        ComplaintStatus.REJECTED.value,
    }
    assert transitions[ComplaintStatus.PROCESSING.value] == {
        ComplaintStatus.RESOLVED.value
    }
    # 「已处理 → 已关闭」只能由投诉人确认或系统超时触发，不属于管理员迁移
    for terminal in (
        ComplaintStatus.RESOLVED,
        ComplaintStatus.REJECTED,
        ComplaintStatus.CLOSED,
    ):
        assert transitions[terminal.value] == set()


def test_ensure_target_exists_covers_all_four_types(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_user(student_no="S92001")
    reservation = make_reservation(student.id, seat.id)

    complaint_service._ensure_target_exists(db, ComplaintTargetType.SEAT.value, seat.id)
    complaint_service._ensure_target_exists(db, ComplaintTargetType.ROOM.value, room.id)
    complaint_service._ensure_target_exists(
        db, ComplaintTargetType.RESERVATION.value, reservation.id
    )
    complaint_service._ensure_target_exists(
        db, ComplaintTargetType.USER.value, student.id
    )

    with pytest.raises(BusinessError) as not_found:
        complaint_service._ensure_target_exists(
            db, ComplaintTargetType.ROOM.value, 999999
        )
    assert not_found.value.code == "COMPLAINT_TARGET_NOT_FOUND"
    assert not_found.value.status_code == 404

    with pytest.raises(BusinessError) as invalid:
        complaint_service._ensure_target_exists(db, "不存在的对象", 1)
    assert invalid.value.code == "COMPLAINT_TARGET_TYPE_INVALID"
    assert invalid.value.status_code == 422


def test_close_stale_boundary_is_idempotent_and_notifies_once(
    db, make_student, make_complaint, freeze_now, captured_notifications
) -> None:
    now = freeze_now
    student = make_student(student_no="S92010")
    deadline = now - timedelta(days=settings.complaint_close_days)

    due = make_complaint(
        student.id,
        status=ComplaintStatus.RESOLVED.value,
        handled_at=deadline,  # 恰好等于期限：应关闭（含端点）
        handle_note="已处理",
    )
    fresh = make_complaint(
        student.id,
        status=ComplaintStatus.RESOLVED.value,
        handled_at=deadline + timedelta(seconds=1),
        handle_note="已处理",
    )

    assert complaint_service.close_stale(db, now) == 1
    db.refresh(due)
    db.refresh(fresh)
    assert due.status == ComplaintStatus.CLOSED.value
    assert fresh.status == ComplaintStatus.RESOLVED.value
    assert len(captured_notifications) == 1
    assert captured_notifications[0]["related_id"] == due.id

    # 重复执行不得重复关闭、重复发消息
    assert complaint_service.close_stale(db, now) == 0
    assert len(captured_notifications) == 1


def test_handle_complaint_trims_note_and_writes_audit(
    db, make_student, make_admin, make_complaint, captured_notifications
) -> None:
    student = make_student(student_no="S92020")
    admin = make_admin()
    complaint = make_complaint(student.id, target_type=ComplaintTargetType.ROOM.value)

    with pytest.raises(BusinessError) as blank:
        complaint_service.handle_complaint(
            db,
            admin,
            complaint.id,
            ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="   "),
        )
    assert blank.value.code == "COMPLAINT_NOTE_REQUIRED"
    assert blank.value.status_code == 422

    handled = complaint_service.handle_complaint(
        db,
        admin,
        complaint.id,
        ComplaintHandle(status=ComplaintStatus.PROCESSING, handle_note="  已受理  "),
    )
    assert handled.status == ComplaintStatus.PROCESSING.value
    assert handled.handle_note == "已受理"
    assert handled.handled_at is not None

    log = db.scalars(
        select(AuditLog).where(AuditLog.action_type == "COMPLAINT_HANDLE")
    ).one()
    assert log.before_value == ComplaintStatus.PENDING.value
    assert log.after_value == ComplaintStatus.PROCESSING.value


def test_confirm_close_rejects_non_owner_and_wrong_state(
    db, make_student, make_complaint
) -> None:
    owner = make_student(student_no="S92030")
    other = make_student(student_no="S92031")
    resolved = make_complaint(owner.id, status=ComplaintStatus.RESOLVED.value)

    with pytest.raises(BusinessError) as not_owner:
        complaint_service.confirm_close(db, other.id, resolved.id)
    assert not_owner.value.code == "COMPLAINT_NOT_OWNER"
    assert not_owner.value.status_code == 403

    pending = make_complaint(owner.id, status=ComplaintStatus.PENDING.value)
    with pytest.raises(BusinessError) as wrong_state:
        complaint_service.confirm_close(db, owner.id, pending.id)
    assert wrong_state.value.code == "COMPLAINT_STATE_INVALID"
    assert wrong_state.value.details == {"status": ComplaintStatus.PENDING.value}

    closed = complaint_service.confirm_close(db, owner.id, resolved.id)
    assert closed.status == ComplaintStatus.CLOSED.value

    with pytest.raises(BusinessError) as again:
        complaint_service.confirm_close(db, owner.id, resolved.id)
    assert again.value.code == "COMPLAINT_STATE_INVALID"


def test_list_all_complaints_date_range_includes_end_day(
    db, make_student, make_complaint
) -> None:
    student = make_student(student_no="S92040")
    day = date(2026, 11, 24)
    in_day = make_complaint(
        student.id, created_at=datetime(2026, 11, 24, 23, 59, 59)
    )
    make_complaint(student.id, created_at=datetime(2026, 11, 25, 0, 0, 0))

    page = complaint_service.list_all_complaints(
        db, 1, 20, created_from=day, created_to=day
    )

    assert [item.id for item in page.items] == [in_day.id]
    assert page.total == 1
