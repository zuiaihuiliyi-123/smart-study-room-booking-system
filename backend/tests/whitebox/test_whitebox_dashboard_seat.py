"""白盒测试：看板图表查询与座位资源状态调整的边界分支。"""

from datetime import date, datetime, time

import pytest

from app.core.exceptions import BusinessError
from app.models.enums import SeatStatus, ViolationType
from app.models.violation import ViolationRecord
from app.schemas.seat import SeatCreate, SeatStatusBatchUpdate, SeatStatusUpdate
from app.services import dashboard_service, seat_service

D = date(2026, 11, 24)


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def test_seat_usage_and_trend(
    db, make_user, make_room, make_seat, make_reservation
) -> None:
    user = make_user(student_no="WBD001")
    room = make_room()
    other_room = make_room(name="另一间")
    seat = make_seat(room.id, seat_no="A-01")
    other_seat = make_seat(other_room.id, seat_no="B-01")

    completed = make_reservation(
        user.id,
        seat.id,
        reserve_date=D,
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="已完成",
        check_in_time=datetime(2026, 11, 24, 10, 0),
        check_out_time=datetime(2026, 11, 24, 12, 0),
    )
    make_reservation(
        user.id,
        other_seat.id,
        reserve_date=D,
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="已取消",
    )

    usage = dashboard_service.get_seat_usage(db, D, D)
    usage_map = {item.name: item.value for item in usage}
    assert usage_map["A-01"] == 4  # 120 分钟 / 30 分钟
    assert usage_map["B-01"] == 0

    filtered = dashboard_service.get_seat_usage(db, D, D, room_id=room.id)
    assert [item.name for item in filtered] == ["A-01"]

    # 结束早于开始 → 空
    assert dashboard_service.get_seat_usage_by_slot(db, D, D - date.resolution) == []
    slot_rows = dashboard_service.get_seat_usage_by_slot(db, D, D, room_id=room.id)
    assert slot_rows

    assert dashboard_service.get_trend(db, D, D - date.resolution) == []
    trend = dashboard_service.get_trend(db, D, D)
    assert trend[0].date == D
    assert trend[0].reservations == 1

    db.add(
        ViolationRecord(
            user_id=user.id,
            reservation_id=completed.id,
            type=ViolationType.MANUAL.value,
            reason="白盒看板",
            created_at=datetime(2026, 11, 24, 11, 0),
        )
    )
    db.commit()
    trend = dashboard_service.get_trend(db, D, D, room_id=room.id)
    assert trend[0].violations == 1


def test_seat_listing_creation_and_status_validation(
    db, make_room, make_seat
) -> None:
    room = make_room()
    make_seat(room.id, seat_no="A-02")
    make_seat(room.id, seat_no="A-01")
    assert [seat.seat_no for seat in seat_service.list_seats(db, room.id)] == [
        "A-01",
        "A-02",
    ]

    with pytest.raises(BusinessError) as exc:
        seat_service.create_seat(
            db, SeatCreate(room_id=9999, seat_no="X-01")
        )
    _assert_code(exc, "ROOM_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        seat_service.update_seat_status(
            db, 9999, SeatStatusUpdate(status=SeatStatus.MAINTENANCE), 1
        )
    _assert_code(exc, "SEAT_NOT_FOUND")


def test_occupancy_and_conflict_validations(db, make_room, make_seat) -> None:
    room = make_room()
    seat = make_seat(room.id)

    with pytest.raises(BusinessError) as exc:
        seat_service.list_occupancy(
            db, room.id, D, time(12, 0), time(10, 0)
        )
    _assert_code(exc, "INVALID_ARGUMENT")
    rows = seat_service.list_occupancy(
        db, room.id, D, time(10, 0), time(12, 0)
    )
    assert rows[0]["seat"].id == seat.id
    assert rows[0]["occupied"] is False

    with pytest.raises(BusinessError) as exc:
        seat_service.list_conflicts(db, [], datetime(2026, 11, 24, 10), datetime(2026, 11, 24, 12))
    _assert_code(exc, "INVALID_ARGUMENT")

    with pytest.raises(BusinessError) as exc:
        seat_service.list_conflicts(
            db,
            [seat.id],
            datetime(2026, 11, 24, 12),
            datetime(2026, 11, 24, 10),
        )
    _assert_code(exc, "INVALID_ARGUMENT")

    with pytest.raises(BusinessError) as exc:
        seat_service.list_conflicts(
            db,
            [seat.id, 9999],
            datetime(2026, 11, 24, 10),
            datetime(2026, 11, 24, 12),
        )
    _assert_code(exc, "SEAT_NOT_FOUND")


def test_batch_status_validations_and_success(db, make_room, make_seat) -> None:
    room = make_room()
    seat = make_seat(room.id)

    with pytest.raises(BusinessError) as exc:
        seat_service.update_status_batch(
            db,
            SeatStatusBatchUpdate(
                seat_ids=[seat.id], status=SeatStatus.MAINTENANCE, reason=" "
            ),
            1,
        )
    _assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        seat_service.update_status_batch(
            db,
            SeatStatusBatchUpdate(
                seat_ids=[seat.id, 9999],
                status=SeatStatus.MAINTENANCE,
                reason="维护",
            ),
            1,
        )
    _assert_code(exc, "SEAT_NOT_FOUND")

    updated, conflicts = seat_service.update_status_batch(
        db,
        SeatStatusBatchUpdate(
            seat_ids=[seat.id], status=SeatStatus.MAINTENANCE, reason="维护"
        ),
        1,
    )
    assert updated[0].status == SeatStatus.MAINTENANCE.value
    assert conflicts == []
