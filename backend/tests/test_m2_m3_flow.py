"""M2 预约 / M3 签到违约 / M6 看板 / M7 消息 / M1 扩展操作回归。"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.seat import Seat
from app.models.violation import ViolationRecord
from app.schemas.reservation import CancelRequest, ReservationCreate
from app.schemas.room import RoomCloseRequest
from app.schemas.seat import SeatStatusBatchUpdate
from app.services import (
    attendance_service,
    availability_service,
    dashboard_service,
    message_service,
    notification_service,
    reservation_service,
    room_service,
    seat_service,
    violation_service,
)
from app.utils import time_utils


@pytest.fixture(autouse=True)
def _disable_external_notifications(monkeypatch):
    """站内通知使用独立 MySQL 会话，测试中改为空操作。"""
    monkeypatch.setattr(
        notification_service, "notify_safe", lambda **kwargs: None
    )


def _payload(seat_id: int, day: date, key: str = "idem-key-0001") -> ReservationCreate:
    return ReservationCreate(
        seat_id=seat_id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
        idempotency_key=key,
    )


def test_create_reservation_is_idempotent_and_materializes_slots(
    db, make_user, make_room, make_seat, monkeypatch
) -> None:
    now = datetime(2026, 11, 2, 10, 0)
    monkeypatch.setattr(time_utils, "now", lambda: now)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = now.date() + timedelta(days=1)

    first = reservation_service.create_reservation(db, user, _payload(seat.id, day))
    second = reservation_service.create_reservation(db, user, _payload(seat.id, day))

    assert first.id == second.id
    assert first.status == ReservationStatus.PENDING.value
    slots = db.scalar(
        select(func.count())
        .select_from(ReservationSlot)
        .where(ReservationSlot.reservation_id == first.id)
    )
    assert slots == 4  # 14:00-16:00，每 30 分钟一个槽位


def test_available_seats_excludes_occupied_seat(
    db, make_user, make_room, make_seat, monkeypatch
) -> None:
    now = datetime(2026, 11, 2, 10, 0)
    monkeypatch.setattr(time_utils, "now", lambda: now)
    owner = make_user(student_no="S0001")
    other = make_user(student_no="S0002")
    room = make_room()
    busy = make_seat(room.id)
    free = make_seat(room.id)
    day = now.date() + timedelta(days=1)
    reservation_service.create_reservation(db, owner, _payload(busy.id, day))

    seats = availability_service.list_available_seats(
        db, room.id, day, time(14, 0), time(16, 0), user_id=other.id
    )

    assert [seat.id for seat in seats] == [free.id]


def test_cancel_releases_slot_and_allows_rebooking(
    db, make_user, make_room, make_seat, monkeypatch
) -> None:
    now = datetime(2026, 11, 2, 10, 0)
    monkeypatch.setattr(time_utils, "now", lambda: now)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = now.date() + timedelta(days=1)
    reservation = reservation_service.create_reservation(
        db, user, _payload(seat.id, day)
    )

    reservation_service.cancel_my_reservation(
        db, user.id, reservation.id, CancelRequest(reason="临时有事")
    )

    assert db.scalar(
        select(func.count())
        .select_from(ReservationSlot)
        .where(ReservationSlot.reservation_id == reservation.id)
    ) == 0
    again = reservation_service.create_reservation(
        db, user, _payload(seat.id, day, key="idem-key-0002")
    )
    assert again.id != reservation.id


def test_check_in_and_check_out(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    fixed = datetime(2026, 11, 2, 14, 0)
    monkeypatch.setattr(time_utils, "now", lambda: fixed)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=fixed.date(),
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    attendance_service.check_in(db, user.id, reservation.id)
    assert reservation.status == ReservationStatus.IN_USE.value
    assert reservation.check_in_time == fixed

    attendance_service.check_out(db, user.id, reservation.id)
    assert reservation.status == ReservationStatus.COMPLETED.value


def test_auto_violation_is_idempotent(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    fixed = datetime(2026, 11, 2, 14, 20)
    monkeypatch.setattr(time_utils, "now", lambda: fixed)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=fixed.date(),
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    first = violation_service.apply_auto_violation(db, reservation.id)
    second = violation_service.apply_auto_violation(db, reservation.id)

    assert first is not None and second is not None
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(ViolationRecord)) == 1
    assert db.get(Reservation, reservation.id).status == ReservationStatus.VIOLATED.value
    assert user.violation_count == 1


def test_dashboard_and_messages(
    db, make_user, make_room, make_seat, make_reservation, monkeypatch
) -> None:
    fixed = datetime(2026, 11, 2, 10, 0)
    monkeypatch.setattr(time_utils, "now", lambda: fixed)
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    make_reservation(
        user.id,
        seat.id,
        reserve_date=fixed.date(),
        start_time=time(14, 0),
        end_time=time(16, 0),
        created_at=fixed,
    )

    overview = dashboard_service.get_overview(db)
    assert overview.seat_total == 1
    assert overview.today_reservations == 1

    rows = dashboard_service.get_seat_usage_by_slot(
        db, fixed.date(), fixed.date()
    )
    assert len(rows) == 7
    assert {row.room_name for row in rows} == {room.name}

    notification_service.notify(
        db,
        user_id=user.id,
        message_type=notification_service.MessageType.SYSTEM,
        title="测试通知",
        content="内容",
    )
    db.commit()
    page = message_service.list_my_messages(db, user.id, 1, 20)
    assert page.total == 1
    assert message_service.unread_count(db, user.id) == 1
    message_service.mark_read(db, user.id, page.items[0].id)
    assert message_service.unread_count(db, user.id) == 0


def test_room_close_preview_then_execute(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = date(2026, 11, 3)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    window_start = datetime(2026, 11, 3, 13, 0)
    window_end = datetime(2026, 11, 3, 17, 0)

    seats, affected = room_service.preview_close(
        db, room.id, window_start, window_end, None
    )
    assert [item.id for item in seats] == [seat.id]
    assert [item.id for item in affected] == [reservation.id]

    result = room_service.close_room(
        db,
        room.id,
        RoomCloseRequest(
            start_at=window_start,
            end_at=window_end,
            reason="考试封场",
            cancel_affected=True,
            expected_reservation_ids=[reservation.id],
        ),
        operator_id=user.id,
    )

    assert result.closed_seats == 1
    assert result.cancelled == 1
    assert db.get(Seat, seat.id).status == SeatStatus.DISABLED.value
    assert db.get(Reservation, reservation.id).status == ReservationStatus.CANCELLED.value
    assert db.scalar(select(func.count()).select_from(AuditLog)) >= 1


def test_seat_occupancy_conflicts_and_batch(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user()
    room = make_room()
    seat = make_seat(room.id)
    day = date(2026, 11, 3)
    reservation = make_reservation(
        user.id,
        seat.id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
    )

    occupancy = seat_service.list_occupancy(
        db, room.id, day, time(15, 0), time(16, 0)
    )
    assert occupancy[0]["occupied"] is True
    assert occupancy[0]["reservation"].id == reservation.id

    conflicts = seat_service.list_conflicts(
        db,
        [seat.id],
        datetime(2026, 11, 3, 14, 30),
        datetime(2026, 11, 3, 15, 30),
    )
    assert [item.id for item in conflicts] == [reservation.id]

    updated, batch_conflicts = seat_service.update_status_batch(
        db,
        SeatStatusBatchUpdate(
            seat_ids=[seat.id], status=SeatStatus.MAINTENANCE, reason="检修"
        ),
        operator_id=user.id,
    )
    assert updated[0].status == SeatStatus.MAINTENANCE.value
    assert [item.id for item in batch_conflicts] == [reservation.id]
