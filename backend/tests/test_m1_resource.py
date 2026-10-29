"""M1 座位资源：自习室/区域/座位/资源状态调整（FR-001～FR-004）。"""

from datetime import date, time

import pytest
from pydantic import ValidationError

from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import ReservationStatus, Role, SeatStatus
from app.schemas.room import AreaCreate, RoomCreate
from app.schemas.seat import SeatCreate, SeatStatusUpdate
from app.services import room_service, seat_service


def _error_of(func, *args, **kwargs) -> BusinessError:
    with pytest.raises(BusinessError) as exc:
        func(*args, **kwargs)
    return exc.value


def test_create_room_and_list_ordered(db, make_room) -> None:
    first = make_room(name="静学室")
    second = make_room(name="研修室")

    rooms = room_service.list_rooms(db)

    assert [room.id for room in rooms] == [first.id, second.id]


def test_create_room_defaults_enabled(db) -> None:
    room = room_service.create_room(
        db,
        RoomCreate(name="新自习室", location="图书馆 1 楼", capacity=40),
    )

    assert room.id is not None
    assert room.enabled is True
    assert room.open_time == "08:00"


def test_create_room_duplicate_name_rejected(db, make_room) -> None:
    make_room(name="静学室")

    error = _error_of(
        room_service.create_room,
        db,
        RoomCreate(name="静学室", location="图书馆 2 楼"),
    )

    assert error.code == "ROOM_NAME_DUPLICATED"
    assert error.status_code == 409


@pytest.mark.parametrize(
    ("open_time", "close_time"),
    [
        ("22:00", "08:00"),  # 开放时间晚于关闭时间
        ("8点", "22:00"),  # 非 HH:MM 格式
    ],
)
def test_create_room_time_rules_rejected_by_schema(open_time, close_time) -> None:
    """接口层由 RoomCreate 的 pattern + model_validator 拦截（422）。"""
    with pytest.raises(ValidationError):
        RoomCreate(
            name="时段测试室",
            location="图书馆",
            open_time=open_time,
            close_time=close_time,
        )


def test_create_room_time_rules_defended_in_service(db) -> None:
    """即使绕过 schema 校验（内部直调），服务层仍须拒绝。"""
    bad_range = RoomCreate.model_construct(
        name="时段测试室A",
        location="图书馆",
        open_time="22:00",
        close_time="08:00",
        capacity=0,
    )
    error = _error_of(room_service.create_room, db, bad_range)
    assert error.code == "ROOM_TIME_RANGE_INVALID"
    assert error.status_code == 422

    bad_format = RoomCreate.model_construct(
        name="时段测试室B",
        location="图书馆",
        open_time="8点",
        close_time="22:00",
        capacity=0,
    )
    error = _error_of(room_service.create_room, db, bad_format)
    assert error.code == "ROOM_TIME_FORMAT_INVALID"
    assert error.status_code == 422


def test_create_area_duplicated_in_same_room(db, make_room) -> None:
    room = make_room()
    room_service.create_area(db, room.id, AreaCreate(name="A 区"))

    error = _error_of(room_service.create_area, db, room.id, AreaCreate(name="A 区"))

    assert error.code == "AREA_NAME_DUPLICATED"


def test_create_area_room_not_found(db) -> None:
    error = _error_of(room_service.create_area, db, 999, AreaCreate(name="A 区"))

    assert error.code == "ROOM_NOT_FOUND"
    assert error.status_code == 404


def test_create_seat_default_available(db, make_room) -> None:
    room = make_room()

    seat = seat_service.create_seat(
        db, SeatCreate(room_id=room.id, seat_no="A-01", has_power=True)
    )

    # 座位只保存资源状态，不含“已预约/使用中”（MD-01）
    assert seat.status == SeatStatus.AVAILABLE.value
    assert seat.has_power is True


def test_create_seat_number_must_be_unique_in_room(db, make_room) -> None:
    room = make_room()
    seat_service.create_seat(db, SeatCreate(room_id=room.id, seat_no="A-01"))

    error = _error_of(
        seat_service.create_seat, db, SeatCreate(room_id=room.id, seat_no="A-01")
    )

    assert error.code == "SEAT_NO_DUPLICATED"


def test_create_seat_area_must_belong_to_room(db, make_room, make_area) -> None:
    room_a = make_room()
    room_b = make_room()
    area_b = make_area(room_b.id, name="B 区")

    error = _error_of(
        seat_service.create_seat,
        db,
        SeatCreate(room_id=room_a.id, area_id=area_b.id, seat_no="A-01"),
    )

    assert error.code == "AREA_NOT_IN_ROOM"


def test_seat_status_change_blocked_by_future_reservation(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    admin = make_user(role=Role.ADMIN.value, student_no="ADM1")
    student = make_user(student_no="S0002")
    make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2099, 1, 1),
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.PENDING.value,
    )

    error = _error_of(
        seat_service.update_seat_status,
        db,
        seat.id,
        SeatStatusUpdate(status=SeatStatus.MAINTENANCE, reason="灯管损坏"),
        admin.id,
    )

    # BR-019：只识别并列出冲突预约，不自动取消
    assert error.code == "SEAT_STATUS_CONFLICT"
    assert error.status_code == 409
    db.refresh(seat)
    assert seat.status == SeatStatus.AVAILABLE.value


def test_seat_status_change_writes_audit(db, make_room, make_seat, make_user) -> None:
    room = make_room()
    seat = make_seat(room.id)
    admin = make_user(role=Role.ADMIN.value, student_no="ADM2")

    updated = seat_service.update_seat_status(
        db,
        seat.id,
        SeatStatusUpdate(status=SeatStatus.MAINTENANCE, reason="灯管损坏"),
        admin.id,
    )

    assert updated.status == SeatStatus.MAINTENANCE.value
    log = db.query(AuditLog).filter(AuditLog.target_type == "SEAT").one()
    assert log.operator_id == admin.id
    assert log.before_value == SeatStatus.AVAILABLE.value
    assert log.after_value == SeatStatus.MAINTENANCE.value
    assert log.reason == "灯管损坏"


def test_seat_status_change_to_same_status_is_noop(
    db, make_room, make_seat, make_user
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    admin = make_user(role=Role.ADMIN.value, student_no="ADM3")

    seat_service.update_seat_status(
        db, seat.id, SeatStatusUpdate(status=SeatStatus.AVAILABLE), admin.id
    )

    assert db.query(AuditLog).count() == 0


def test_seat_status_can_be_restored_to_available(
    db, make_room, make_seat, make_user
) -> None:
    room = make_room()
    seat = make_seat(room.id, status=SeatStatus.DISABLED.value)
    admin = make_user(role=Role.ADMIN.value, student_no="ADM4")

    updated = seat_service.update_seat_status(
        db,
        seat.id,
        SeatStatusUpdate(status=SeatStatus.AVAILABLE, reason="恢复开放"),
        admin.id,
    )

    assert updated.status == SeatStatus.AVAILABLE.value


def test_seat_status_ignores_finished_reservations(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    admin = make_user(role=Role.ADMIN.value, student_no="ADM5")
    student = make_user(student_no="S0003")
    make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2020, 1, 1),
        status=ReservationStatus.COMPLETED.value,
    )

    updated = seat_service.update_seat_status(
        db, seat.id, SeatStatusUpdate(status=SeatStatus.MAINTENANCE), admin.id
    )

    assert updated.status == SeatStatus.MAINTENANCE.value

