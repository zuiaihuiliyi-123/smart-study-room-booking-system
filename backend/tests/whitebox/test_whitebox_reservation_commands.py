"""白盒测试：预约创建幂等、取消/强制取消的状态与并发分支。"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.models.reservation_slot import ReservationSlot
from app.schemas.reservation import CancelRequest, ForceCancelRequest, ReservationCreate
from app.services import notification_service, reservation_command_service
from app.utils import time_utils

NOW = datetime(2026, 11, 24, 10, 0)
TODAY = date(2026, 11, 24)
D = date(2026, 11, 25)


@pytest.fixture(autouse=True)
def _freeze_and_silence(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: NOW)
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def _payload(seat_id: int, key: str = "whitebox-key-0001", **kwargs) -> ReservationCreate:
    values = {
        "seat_id": seat_id,
        "reserve_date": D,
        "start_time": time(14, 0),
        "end_time": time(16, 0),
        "idempotency_key": key,
    }
    values.update(kwargs)
    return ReservationCreate(**values)


def _setup(make_user, make_room, make_seat, *, student_no="WBK001"):
    user = make_user(student_no=student_no)
    room = make_room()
    seat = make_seat(room.id)
    return user, seat


def test_create_replay_returns_existing_without_duplicate_notification(
    db, make_user, make_room, make_seat, monkeypatch
) -> None:
    user, seat = _setup(make_user, make_room, make_seat)
    messages: list[str] = []
    monkeypatch.setattr(
        notification_service,
        "notify_safe",
        lambda **kwargs: messages.append(kwargs.get("title", "")),
    )

    first = reservation_command_service.create_reservation(db, user, _payload(seat.id))
    second = reservation_command_service.create_reservation(db, user, _payload(seat.id))

    assert first.id == second.id
    assert messages == ["预约成功"]
    assert len(db.scalars(select(ReservationSlot)).all()) == 24  # 2 小时 / 5 分钟


def test_create_rejects_reused_key_with_different_payload(
    db, make_user, make_room, make_seat
) -> None:
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK002")
    reservation_command_service.create_reservation(db, user, _payload(seat.id))

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.create_reservation(
            db,
            user,
            _payload(seat.id, start_time=time(15, 0), end_time=time(17, 0)),
        )
    _assert_code(exc, "IDEMPOTENCY_KEY_REUSED")


def test_cancel_validations_and_deadline(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK003")
    other = make_user(student_no="WBK004")
    reservation = make_reservation(
        user.id, seat.id, reserve_date=D, start_time=time(14, 0), end_time=time(16, 0)
    )

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.cancel_my_reservation(
            db, user.id, 9999, CancelRequest()
        )
    _assert_code(exc, "RESERVATION_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.cancel_my_reservation(
            db, other.id, reservation.id, CancelRequest()
        )
    _assert_code(exc, "FORBIDDEN")

    reservation.status = ReservationStatus.CANCELLED.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        reservation_command_service.cancel_my_reservation(
            db, user.id, reservation.id, CancelRequest()
        )
    _assert_code(exc, "ST-031")

    soon = make_reservation(
        user.id,
        seat.id,
        reserve_date=TODAY,
        start_time=time(10, 20),
        end_time=time(12, 0),
    )
    with pytest.raises(BusinessError) as exc:
        reservation_command_service.cancel_my_reservation(
            db, user.id, soon.id, CancelRequest()
        )
    _assert_code(exc, "ST-029")


def test_cancel_state_changed_conflict(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK005")
    reservation = make_reservation(
        user.id, seat.id, reserve_date=D, start_time=time(14, 0), end_time=time(16, 0)
    )
    monkeypatch.setattr(
        reservation_command_service, "transition_if_status", lambda *a, **k: False
    )

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.cancel_my_reservation(
            db, user.id, reservation.id, CancelRequest(reason="临时有事")
        )
    _assert_code(exc, "ST-031")


def test_force_cancel_validations(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    admin = make_user(student_no="WBK101", role="自习室管理员")
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK102")

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.force_cancel(
            db, admin.id, 9999, ForceCancelRequest(reason=" ")
        )
    _assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        reservation_command_service.force_cancel(
            db, admin.id, 9999, ForceCancelRequest(reason="场地调整")
        )
    _assert_code(exc, "RESERVATION_NOT_FOUND")

    in_use = make_reservation(
        user.id,
        seat.id,
        reserve_date=D,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.IN_USE.value,
    )
    with pytest.raises(BusinessError) as exc:
        reservation_command_service.force_cancel(
            db, admin.id, in_use.id, ForceCancelRequest(reason="场地调整")
        )
    _assert_code(exc, "ST-022")
    assert exc.value.details["hint"]

    completed = make_reservation(
        user.id,
        seat.id,
        reserve_date=D,
        start_time=time(17, 0),
        end_time=time(18, 0),
        status=ReservationStatus.COMPLETED.value,
    )
    with pytest.raises(BusinessError) as exc:
        reservation_command_service.force_cancel(
            db, admin.id, completed.id, ForceCancelRequest(reason="场地调整")
        )
    _assert_code(exc, "ST-022")


def test_force_cancel_success_and_state_changed(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    admin = make_user(student_no="WBK201", role="自习室管理员")
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK202")
    reservation = make_reservation(
        user.id, seat.id, reserve_date=D, start_time=time(14, 0), end_time=time(16, 0)
    )

    result = reservation_command_service.force_cancel(
        db, admin.id, reservation.id, ForceCancelRequest(reason="场地临时调整")
    )
    assert result.status == ReservationStatus.CANCELLED.value
    assert result.cancelled_by_id == admin.id
    assert result.cancel_reason == "场地临时调整"

    pending = make_reservation(
        user.id,
        seat.id,
        reserve_date=D,
        start_time=time(17, 0),
        end_time=time(18, 0),
    )
    monkeypatch.setattr(
        reservation_command_service, "transition_if_status", lambda *a, **k: False
    )
    with pytest.raises(BusinessError) as exc:
        reservation_command_service.force_cancel(
            db, admin.id, pending.id, ForceCancelRequest(reason="场地临时调整")
        )
    _assert_code(exc, "ST-022")


def test_cancel_releases_slots(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user, seat = _setup(make_user, make_room, make_seat, student_no="WBK301")
    reservation = make_reservation(
        user.id, seat.id, reserve_date=D, start_time=time(14, 0), end_time=time(16, 0)
    )
    db.add(
        ReservationSlot(
            reservation_id=reservation.id,
            seat_id=seat.id,
            user_id=user.id,
            slot_start=datetime.combine(D, time(14, 0)),
        )
    )
    db.commit()

    cancelled = reservation_command_service.cancel_my_reservation(
        db, user.id, reservation.id, CancelRequest(reason="行程变化")
    )

    assert cancelled.status == ReservationStatus.CANCELLED.value
    assert db.scalars(select(ReservationSlot)).all() == []
