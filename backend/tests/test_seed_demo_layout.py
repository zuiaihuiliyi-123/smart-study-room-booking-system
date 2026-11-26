"""演示座位布局：保证新电脑执行 start.bat 后，预约座位图与演示版本一致。"""

from sqlalchemy import func, select

from app.models.room import Area, Room
from app.models.seat import Seat
from scripts.seed_demo import DEMO_ROOMS, ensure_demo_resources


def _seats_of(db, room_name: str) -> dict[str, Seat]:
    room = db.scalar(select(Room).where(Room.name == room_name))
    assert room is not None, f"缺少演示自习室：{room_name}"
    seats = db.scalars(select(Seat).where(Seat.room_id == room.id)).all()
    return {seat.seat_no: seat for seat in seats}


def test_demo_layout_creates_three_rooms_with_98_seats(db) -> None:
    created, reused, added = ensure_demo_resources(db)
    db.commit()

    assert (created, reused, added) == (3, 0, 98)
    assert db.scalar(select(func.count()).select_from(Seat)) == 98
    assert db.scalar(select(func.count()).select_from(Area)) == 10

    rooms = db.scalars(select(Room).order_by(Room.id)).all()
    assert [room.name for room in rooms] == [spec["name"] for spec in DEMO_ROOMS]
    assert [room.location for room in rooms] == [
        "图书馆 2 层东侧",
        "图书馆 3 层西侧",
        "图书馆 4 层北侧",
    ]
    assert [room.capacity for room in rooms] == [38, 30, 30]


def test_demo_layout_keeps_seat_attributes_for_seat_map(db) -> None:
    ensure_demo_resources(db)
    db.commit()

    first = _seats_of(db, "第一自习室")
    assert first["A-01"].has_power and not first["A-01"].near_window
    assert not first["A-04"].has_power and not first["A-04"].near_window
    assert first["B-01"].has_power and first["B-01"].near_window
    assert not first["B-04"].has_power and first["B-04"].near_window
    assert first["C-10"].has_power and not first["C-10"].near_window
    assert not first["D-08"].has_power

    second = _seats_of(db, "第二自习室")
    assert second["C-04"].has_power and not second["C-05"].has_power
    assert second["D-05"].has_power and second["D-05"].near_window
    assert not second["D-06"].has_power and second["D-06"].near_window
    assert second["E-10"].has_power

    third = _seats_of(db, "第三自习室")
    assert not third["D-01"].has_power and not third["D-01"].near_window
    assert third["E-01"].near_window and not third["E-01"].has_power
    assert third["F-10"].has_power


def test_demo_resources_are_idempotent(db) -> None:
    ensure_demo_resources(db)
    db.commit()

    assert ensure_demo_resources(db) == (0, 3, 0)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Seat)) == 98
    assert [room.capacity for room in db.scalars(select(Room).order_by(Room.id))] == [
        38,
        30,
        30,
    ]
