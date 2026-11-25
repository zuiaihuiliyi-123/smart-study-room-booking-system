"""白盒测试：签到/签退的归属、状态、时间窗口与并发状态变化分支。"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.models.reservation_slot import ReservationSlot
from app.services import attendance_service
from app.utils import time_utils

NOW = datetime(2026, 11, 24, 10, 0)
TODAY = date(2026, 11, 24)


@pytest.fixture(autouse=True)
def _freeze_now(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: NOW)


def _reservation(
    make_reservation,
    user,
    seat,
    *,
    status: str = ReservationStatus.PENDING.value,
    reserve_date: date = TODAY,
    start: time = time(10, 0),
    end: time = time(12, 0),
):
    return make_reservation(
        user.id,
        seat.id,
        status=status,
        reserve_date=reserve_date,
        start_time=start,
        end_time=end,
    )


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def test_check_in_missing_reservation(db, make_user) -> None:
    user = make_user(student_no="WBT001")
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, 9999)
    _assert_code(exc, "RESERVATION_NOT_FOUND")


def test_check_in_rejects_other_user_and_wrong_status(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBT002")
    other = make_user(student_no="WBT003")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(make_reservation, user, seat)

    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, other.id, reservation.id)
    _assert_code(exc, "FORBIDDEN")

    reservation.status = ReservationStatus.IN_USE.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, reservation.id)
    _assert_code(exc, "ST-030")

    reservation.status = ReservationStatus.CANCELLED.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, reservation.id)
    _assert_code(exc, "ST-031")


def test_check_in_window_before_and_after(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBT004")
    room = make_room()
    seat = make_seat(room.id)

    future = _reservation(
        make_reservation, user, seat, start=time(11, 0), end=time(12, 0)
    )
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, future.id)
    _assert_code(exc, "ST-027")

    past = _reservation(
        make_reservation,
        user,
        seat,
        reserve_date=TODAY - timedelta(days=1),
        start=time(10, 0),
        end=time(12, 0),
    )
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, past.id)
    _assert_code(exc, "ST-027")


def test_check_in_success(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBT005")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(make_reservation, user, seat)

    result = attendance_service.check_in(db, user.id, reservation.id)

    assert result.status == ReservationStatus.IN_USE.value
    assert result.check_in_time == NOW


def test_check_in_retry_reports_latest_in_use(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    user = make_user(student_no="WBT006")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(make_reservation, user, seat)

    monkeypatch.setattr(attendance_service, "transition_if_status", lambda *a, **k: False)
    original = attendance_service._get_reservation
    calls = {"n": 0}

    def fake_get(db_session, reservation_id):
        item = original(db_session, reservation_id)
        calls["n"] += 1
        if calls["n"] > 1:
            item.status = ReservationStatus.IN_USE.value
            item.check_in_time = NOW
        return item

    monkeypatch.setattr(attendance_service, "_get_reservation", fake_get)

    with pytest.raises(BusinessError) as exc:
        attendance_service.check_in(db, user.id, reservation.id)
    _assert_code(exc, "ST-030")


def test_check_out_ownership_and_status(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBT007")
    other = make_user(student_no="WBT008")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(
        make_reservation, user, seat, status=ReservationStatus.IN_USE.value
    )

    with pytest.raises(BusinessError) as exc:
        attendance_service.check_out(db, other.id, reservation.id)
    _assert_code(exc, "FORBIDDEN")

    reservation.status = ReservationStatus.PENDING.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_out(db, user.id, reservation.id)
    _assert_code(exc, "ST-031")

    reservation.status = ReservationStatus.COMPLETED.value
    db.commit()
    with pytest.raises(BusinessError) as exc:
        attendance_service.check_out(db, user.id, reservation.id)
    _assert_code(exc, "ST-031")


def test_check_out_success_releases_slots(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBT009")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(
        make_reservation, user, seat, status=ReservationStatus.IN_USE.value
    )
    db.add(
        ReservationSlot(
            reservation_id=reservation.id,
            seat_id=seat.id,
            user_id=user.id,
            slot_start=datetime.combine(TODAY, time(10, 0)),
        )
    )
    db.commit()

    result = attendance_service.check_out(db, user.id, reservation.id)

    assert result.status == ReservationStatus.COMPLETED.value
    assert result.check_out_time == NOW
    assert db.scalars(select(ReservationSlot)).all() == []


def test_check_out_state_changed_reports_conflict(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    user = make_user(student_no="WBT010")
    room = make_room()
    seat = make_seat(room.id)
    reservation = _reservation(
        make_reservation, user, seat, status=ReservationStatus.IN_USE.value
    )
    monkeypatch.setattr(attendance_service, "transition_if_status", lambda *a, **k: False)

    with pytest.raises(BusinessError) as exc:
        attendance_service.check_out(db, user.id, reservation.id)
    _assert_code(exc, "ST-031")
