"""白盒测试：可预约校验 C1～C6 的未覆盖分支与可约座位查询边界。"""

from datetime import date, datetime, time, timedelta

import pytest

from app.core.exceptions import BusinessError
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, BlacklistMode, SeatStatus
from app.models.room import RoomClosure
from app.services import availability_service
from app.utils import time_utils

NOW = datetime(2026, 11, 24, 10, 0)
D = date(2026, 11, 25)
START = time(14, 0)
END = time(16, 0)


@pytest.fixture(autouse=True)
def _freeze_now(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: NOW)


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def _check(db, user, seat, *, start=START, end=END, reserve_date=D):
    availability_service.check_reservation_rules(
        db,
        user_id=user.id,
        seat_id=seat.id,
        reserve_date=reserve_date,
        start_time=start,
        end_time=end,
        now=NOW,
    )


def test_parse_room_time_invalid() -> None:
    with pytest.raises(BusinessError) as exc:
        availability_service._parse_room_time("not-a-time")
    _assert_code(exc, "ROOM_TIME_INVALID")
    assert exc.value.status_code == 500


def test_check_rules_missing_user(db, make_seat, make_room) -> None:
    room = make_room()
    seat = make_seat(room.id)
    with pytest.raises(BusinessError) as exc:
        availability_service.check_reservation_rules(
            db,
            user_id=9999,
            seat_id=seat.id,
            reserve_date=D,
            start_time=START,
            end_time=END,
            now=NOW,
        )
    _assert_code(exc, "USER_NOT_FOUND")


def test_check_rules_restricted_details(db, make_user, make_room, make_seat) -> None:
    user = make_user(student_no="WBX001", violation_count=3)
    room = make_room()
    seat = make_seat(room.id)

    auto = BlacklistEntry(
        user_id=user.id,
        reason="自动限制",
        mode=BlacklistMode.AUTO.value,
        start_at=NOW - timedelta(days=1),
        expire_at=NOW + timedelta(days=6),
        active_user_id=user.id,
    )
    db.add(auto)
    user.account_status = AccountStatus.RESTRICTED.value
    db.commit()

    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "ST-047")
    assert exc.value.details["params"]["limit_until"] == auto.expire_at.isoformat()

    auto.released_at = NOW
    auto.release_reason = "人工解除"
    auto.active_user_id = None
    manual = BlacklistEntry(
        user_id=user.id,
        reason="手动限制",
        mode=BlacklistMode.MANUAL.value,
        start_at=NOW - timedelta(days=1),
        active_user_id=user.id,
    )
    db.add(manual)
    db.commit()

    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "ST-047")
    assert exc.value.details["params"]["manual_restriction"] is True


def test_check_rules_disabled_account(db, make_user, make_room, make_seat) -> None:
    user = make_user(student_no="WBX002", account_status=AccountStatus.DISABLED.value)
    room = make_room()
    seat = make_seat(room.id)

    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "ST-047")
    assert "停用" in exc.value.message


def test_check_rules_missing_or_unavailable_seat(
    db, make_user, make_room, make_seat
) -> None:
    user = make_user(student_no="WBX003")
    room = make_room()
    seat = make_seat(room.id, status=SeatStatus.MAINTENANCE.value)

    with pytest.raises(BusinessError) as exc:
        availability_service.check_reservation_rules(
            db,
            user_id=user.id,
            seat_id=9999,
            reserve_date=D,
            start_time=START,
            end_time=END,
            now=NOW,
        )
    _assert_code(exc, "SEAT_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "C1_BR-017")


def test_check_rules_room_disabled_and_open_hours(
    db, make_user, make_room, make_seat
) -> None:
    user = make_user(student_no="WBX004")
    disabled_room = make_room(enabled=False)
    disabled_seat = make_seat(disabled_room.id)
    with pytest.raises(BusinessError) as exc:
        _check(db, user, disabled_seat)
    _assert_code(exc, "C2")

    room = make_room(name="开放时间测试馆", open_time="08:00", close_time="22:00")
    seat = make_seat(room.id)
    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat, start=time(7, 0), end=time(8, 0))
    _assert_code(exc, "C2")
    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat, start=time(21, 0), end=time(23, 0))
    _assert_code(exc, "C2")


def test_check_rules_room_closure_area_scope(
    db, make_user, make_room, make_area, make_seat
) -> None:
    user = make_user(student_no="WBX005")
    room = make_room()
    area_a = make_area(room.id, "A 区")
    area_b = make_area(room.id, "B 区")
    seat = make_seat(room.id, area_id=area_a.id)

    other_area_closure = RoomClosure(
        room_id=room.id,
        area_id=area_b.id,
        start_at=datetime.combine(D, START),
        end_at=datetime.combine(D, END),
        reason="B 区维修",
        operator_id=1,
    )
    db.add(other_area_closure)
    db.commit()
    _check(db, user, seat)  # 其他分区关闭不影响本座位

    matching = RoomClosure(
        room_id=room.id,
        area_id=area_a.id,
        start_at=datetime.combine(D, START),
        end_at=datetime.combine(D, END),
        reason="A 区维修",
        operator_id=1,
    )
    db.add(matching)
    db.commit()
    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "ROOM_CLOSED")

    matching.area_id = None
    db.commit()
    with pytest.raises(BusinessError) as exc:
        _check(db, user, seat)
    _assert_code(exc, "ROOM_CLOSED")


def test_list_available_seats_validations_and_filters(
    db, make_user, make_room, make_area, make_seat
) -> None:
    user = make_user(student_no="WBX101")

    with pytest.raises(BusinessError) as exc:
        availability_service.list_available_seats(
            db, 1, D, END, START, user_id=user.id
        )
    _assert_code(exc, "C6_BR-020")

    with pytest.raises(BusinessError) as exc:
        availability_service.list_available_seats(
            db, 9999, D, START, END, user_id=user.id
        )
    _assert_code(exc, "ROOM_NOT_FOUND")

    disabled = make_room(name="停用馆", enabled=False)
    with pytest.raises(BusinessError) as exc:
        availability_service.list_available_seats(
            db, disabled.id, D, START, END, user_id=user.id
        )
    _assert_code(exc, "C2")

    room = make_room(name="可约查询馆", open_time="08:00", close_time="22:00")
    with pytest.raises(BusinessError) as exc:
        availability_service.list_available_seats(
            db, room.id, D, time(7, 0), time(8, 0), user_id=user.id
        )
    _assert_code(exc, "C2")


def test_list_available_seats_closure_and_success(
    db, make_user, make_room, make_area, make_seat
) -> None:
    user = make_user(student_no="WBX102")
    room = make_room(open_time="08:00", close_time="22:00")
    area = make_area(room.id, "A 区")
    seat = make_seat(room.id, area_id=area.id)
    other = make_seat(room.id)

    seats = availability_service.list_available_seats(
        db, room.id, D, START, END, user_id=user.id
    )
    assert {item.id for item in seats} == {seat.id, other.id}

    db.add(
        RoomClosure(
            room_id=room.id,
            area_id=area.id,
            start_at=datetime.combine(D, START),
            end_at=datetime.combine(D, END),
            reason="A 区维修",
            operator_id=1,
        )
    )
    db.commit()
    seats = availability_service.list_available_seats(
        db, room.id, D, START, END, user_id=user.id
    )
    assert {item.id for item in seats} == {other.id}

    db.add(
        RoomClosure(
            room_id=room.id,
            area_id=None,
            start_at=datetime.combine(D, START),
            end_at=datetime.combine(D, END),
            reason="全馆维修",
            operator_id=1,
        )
    )
    db.commit()
    assert (
        availability_service.list_available_seats(
            db, room.id, D, START, END, user_id=user.id
        )
        == []
    )
