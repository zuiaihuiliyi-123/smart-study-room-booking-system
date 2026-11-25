"""白盒测试：自习室 CRUD、分区、临时关闭与解除的异常/边界分支。"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import delete, select

from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import ReservationStatus, SeatStatus
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.room import Area, Room, RoomClosure
from app.models.seat import Seat
from app.schemas.room import (
    AreaCreate,
    RoomCloseRequest,
    RoomCreate,
    RoomUpdate,
)
from app.services import room_service

D = date(2099, 1, 1)
START = datetime(2099, 1, 1, 14, 0)
END = datetime(2099, 1, 1, 16, 0)


def _room(db, name: str = "白盒自习室", enabled: bool = True) -> Room:
    room = Room(
        name=name,
        location="测试楼",
        open_time="08:00",
        close_time="22:00",
        enabled=enabled,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def _reservation(db, user, seat, *, status: str = ReservationStatus.PENDING.value):
    item = Reservation(
        user_id=user.id,
        seat_id=seat.id,
        reserve_date=D,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=status,
        idempotency_key="wb-room-01",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _assert_code(exc_info, code: str) -> None:
    assert exc_info.value.code == code


def test_parse_hhmm_invalid(db) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service._parse_hhmm("25:99", "开放时间")
    _assert_code(exc, "ROOM_TIME_FORMAT_INVALID")


def test_create_room_rejects_invalid_range_duplicate_and_creates(db) -> None:
    bad = RoomCreate.model_construct(
        name="非法时间", location="测试", open_time="10:00", close_time="09:00", capacity=0
    )
    with pytest.raises(BusinessError) as exc:
        room_service.create_room(db, bad)
    _assert_code(exc, "ROOM_TIME_RANGE_INVALID")

    payload = RoomCreate(name="一号馆", location="图书馆")
    created = room_service.create_room(db, payload)
    assert created.id > 0

    with pytest.raises(BusinessError) as exc:
        room_service.create_room(
            db, RoomCreate(name="一号馆", location="别处")
        )
    _assert_code(exc, "ROOM_NAME_DUPLICATED")


def test_create_area_missing_room_duplicate_and_success(db) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.create_area(db, 9999, AreaCreate(name="A 区"))
    _assert_code(exc, "ROOM_NOT_FOUND")

    room = _room(db)
    area = room_service.create_area(db, room.id, AreaCreate(name="A 区"))
    assert area.room_id == room.id

    with pytest.raises(BusinessError) as exc:
        room_service.create_area(db, room.id, AreaCreate(name="A 区"))
    _assert_code(exc, "AREA_NAME_DUPLICATED")


def test_update_room_missing_duplicate_invalid_range_and_success(db, make_user) -> None:
    admin = make_user(student_no="WBA001", role="自习室管理员")
    with pytest.raises(BusinessError) as exc:
        room_service.update_room(db, 9999, RoomUpdate(reason="x"), admin.id)
    _assert_code(exc, "ROOM_NOT_FOUND")

    first = _room(db, "一号馆")
    _room(db, "二号馆")

    with pytest.raises(BusinessError) as exc:
        room_service.update_room(db, first.id, RoomUpdate(name="二号馆"), admin.id)
    _assert_code(exc, "ROOM_NAME_DUPLICATED")

    with pytest.raises(BusinessError) as exc:
        room_service.update_room(
            db,
            first.id,
            RoomUpdate.model_construct(open_time="20:00", close_time="09:00"),
            admin.id,
        )
    _assert_code(exc, "ROOM_TIME_RANGE_INVALID")

    updated = room_service.update_room(
        db,
        first.id,
        RoomUpdate(
            name="一号馆（新）",
            location="新地址",
            open_time="07:30",
            close_time="21:30",
            capacity=120,
            enabled=False,
            reason="调整开放时间",
        ),
        admin.id,
    )
    assert updated.name == "一号馆（新）"
    assert updated.enabled is False
    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action_type == "ROOM_UPDATE",
            AuditLog.target_id == first.id,
        )
    )
    assert audit is not None


def test_delete_room_requires_reason_and_existing_room(db) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.delete_room(db, 1, "   ", 1)
    _assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        room_service.delete_room(db, 9999, "清理", 1)
    _assert_code(exc, "ROOM_NOT_FOUND")


def test_delete_room_rejects_history_and_leftover_slots(db, make_user, make_seat) -> None:
    user = make_user(student_no="WBS001")
    room = _room(db)
    seat = make_seat(room.id)
    _reservation(db, user, seat)

    with pytest.raises(BusinessError) as exc:
        room_service.delete_room(db, room.id, "清理", 1)
    _assert_code(exc, "ROOM_HAS_HISTORY")

    # 只留下时段占位、预约主记录已不存在，也必须视为历史
    reservation = db.scalar(select(Reservation).where(Reservation.seat_id == seat.id))
    db.add(
        ReservationSlot(
            reservation_id=reservation.id,
            seat_id=seat.id,
            user_id=user.id,
            slot_start=START,
        )
    )
    db.commit()
    db.execute(delete(Reservation))
    db.commit()

    with pytest.raises(BusinessError) as exc:
        room_service.delete_room(db, room.id, "清理", 1)
    _assert_code(exc, "ROOM_HAS_HISTORY")


def test_delete_room_success_removes_children(db) -> None:
    room = _room(db)
    area = room_service.create_area(db, room.id, AreaCreate(name="A 区"))
    db.add(
        Seat(
            room_id=room.id,
            area_id=area.id,
            seat_no="A-01",
            status=SeatStatus.AVAILABLE.value,
        )
    )
    db.commit()

    room_service.delete_room(db, room.id, "空馆清理", 1)

    assert db.get(Room, room.id) is None
    assert db.get(Area, area.id) is None
    assert db.scalar(select(Seat).where(Seat.room_id == room.id)) is None


def test_list_areas_missing_and_success(db) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.list_areas(db, 9999)
    _assert_code(exc, "ROOM_NOT_FOUND")

    room = _room(db)
    room_service.create_area(db, room.id, AreaCreate(name="A 区"))
    assert len(room_service.list_areas(db, room.id)) == 1


def test_preview_close_validations_and_result(db, make_user, make_seat) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.preview_close(db, 9999, START, END, None)
    _assert_code(exc, "ROOM_NOT_FOUND")

    room = _room(db)
    with pytest.raises(BusinessError) as exc:
        room_service.preview_close(db, room.id, END, START, None)
    _assert_code(exc, "INVALID_ARGUMENT")

    other = _room(db, "另一馆")
    other_area = room_service.create_area(db, other.id, AreaCreate(name="B 区"))
    with pytest.raises(BusinessError) as exc:
        room_service.preview_close(db, room.id, START, END, other_area.id)
    _assert_code(exc, "AREA_NOT_IN_ROOM")

    user = make_user(student_no="WBP001")
    seat = make_seat(room.id)
    reservation = _reservation(db, user, seat)
    seats, affected = room_service.preview_close(db, room.id, START, END, None)
    assert [item.id for item in seats] == [seat.id]
    assert [item.id for item in affected] == [reservation.id]


def test_close_room_validations_and_list_changed(db, make_user, make_seat) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.close_room(
            db,
            1,
            RoomCloseRequest(
                start_at=START, end_at=END, reason=" ", expected_reservation_ids=[]
            ),
            1,
        )
    _assert_code(exc, "REASON_REQUIRED")

    room = _room(db)
    with pytest.raises(BusinessError) as exc:
        room_service.close_room(
            db,
            9999,
            RoomCloseRequest(
                start_at=START, end_at=END, reason="维修", expected_reservation_ids=[]
            ),
            1,
        )
    _assert_code(exc, "ROOM_NOT_FOUND")

    with pytest.raises(BusinessError) as exc:
        room_service.close_room(
            db,
            room.id,
            RoomCloseRequest(
                start_at=END, end_at=START, reason="维修", expected_reservation_ids=[]
            ),
            1,
        )
    _assert_code(exc, "INVALID_ARGUMENT")

    other = _room(db, "另一馆")
    other_area = room_service.create_area(db, other.id, AreaCreate(name="B 区"))
    with pytest.raises(BusinessError) as exc:
        room_service.close_room(
            db,
            room.id,
            RoomCloseRequest(
                start_at=START,
                end_at=END,
                area_id=other_area.id,
                reason="维修",
                expected_reservation_ids=[],
            ),
            1,
        )
    _assert_code(exc, "AREA_NOT_IN_ROOM")

    user = make_user(student_no="WBC001")
    seat = make_seat(room.id)
    _reservation(db, user, seat)
    with pytest.raises(BusinessError) as exc:
        room_service.close_room(
            db,
            room.id,
            RoomCloseRequest(
                start_at=START, end_at=END, reason="维修", expected_reservation_ids=[]
            ),
            1,
        )
    _assert_code(exc, "CONFLICT_LIST_CHANGED")


def test_close_room_success_cancels_affected(db, make_user, make_seat) -> None:
    room = _room(db)
    user = make_user(student_no="WBC101")
    seat = make_seat(room.id)
    reservation = _reservation(db, user, seat)

    result = room_service.close_room(
        db,
        room.id,
        RoomCloseRequest(
            start_at=START,
            end_at=END,
            reason="临时维修",
            cancel_affected=True,
            expected_reservation_ids=[reservation.id],
        ),
        user.id,
    )
    assert result.cancelled == 1
    assert result.closed_seats == 1
    assert db.get(Reservation, reservation.id).status == ReservationStatus.CANCELLED.value


def test_list_release_and_active_closures(db) -> None:
    with pytest.raises(BusinessError) as exc:
        room_service.list_closures(db, 9999)
    _assert_code(exc, "ROOM_NOT_FOUND")

    room = _room(db)
    closure = RoomClosure(
        room_id=room.id,
        start_at=START,
        end_at=END,
        reason="维修",
        operator_id=1,
    )
    db.add(closure)
    db.commit()
    assert [item.id for item in room_service.list_closures(db, room.id)] == [closure.id]
    assert [item.id for item in room_service.active_closures(db, room.id, START, END)] == [
        closure.id
    ]

    with pytest.raises(BusinessError) as exc:
        room_service.release_closure(db, room.id, closure.id, " ", 1)
    _assert_code(exc, "REASON_REQUIRED")

    with pytest.raises(BusinessError) as exc:
        room_service.release_closure(db, room.id, 9999, "恢复", 1)
    _assert_code(exc, "CLOSURE_NOT_FOUND")

    other = _room(db, "另一馆")
    with pytest.raises(BusinessError) as exc:
        room_service.release_closure(db, other.id, closure.id, "恢复", 1)
    _assert_code(exc, "CLOSURE_NOT_FOUND")

    room_service.release_closure(db, room.id, closure.id, "维修完成", 1)
    assert db.get(RoomClosure, closure.id) is None
