"""创建演示资源数据（自习室 / 分区 / 座位）：python -m scripts.seed_demo

幂等：同名自习室已存在时不再重复建房间，但会把演示布局中缺少的座位补齐，
保证每个演示自习室至少有 12 个可预约座位（用户要求不少于 10 个）。
演示账户仍由 ``python -m scripts.seed`` 负责。
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import SeatStatus
from app.models.room import Area, Room
from app.models.seat import Seat

# (座位号, 是否有电源, 是否靠窗)
DEMO_ROOMS: list[dict] = [
    {
        "name": "第一自习室",
        "location": "图书馆 2 层东侧",
        "open_time": "08:00",
        "close_time": "22:00",
        "areas": [
            {
                "name": "A 区·安静区",
                "seats": [
                    ("A-01", True, False),
                    ("A-02", True, False),
                    ("A-03", True, False),
                    ("A-04", False, False),
                    ("A-05", False, False),
                    ("A-06", False, False),
                ],
            },
            {
                "name": "B 区·靠窗区",
                "seats": [
                    ("B-01", True, True),
                    ("B-02", True, True),
                    ("B-03", True, True),
                    ("B-04", False, True),
                    ("B-05", False, True),
                    ("B-06", False, True),
                ],
            },
        ],
    },
    {
        "name": "第二自习室",
        "location": "图书馆 3 层西侧",
        "open_time": "09:00",
        "close_time": "21:00",
        "areas": [
            {
                "name": "C 区·标准区",
                "seats": [
                    ("C-01", True, False),
                    ("C-02", True, False),
                    ("C-03", True, False),
                    ("C-04", True, False),
                    ("C-05", False, False),
                    ("C-06", False, False),
                    ("C-07", False, False),
                    ("C-08", False, False),
                    ("C-09", False, False),
                    ("C-10", False, False),
                    ("C-11", False, False),
                    ("C-12", False, False),
                ],
            },
        ],
    },
]


def _sync_room_layout(db, room: Room, spec: dict) -> int:
    """把一间演示自习室补齐到 spec 中的座位集合，返回新增座位数。

    已经存在的房间不清空、不重排，只补缺；这样既能修复历史上只有 8 座的演示房间，
    又不会影响用户后来手工添加的座号或预约。
    """
    added = 0
    for area_spec in spec["areas"]:
        area = db.scalar(
            select(Area).where(
                Area.room_id == room.id,
                Area.name == area_spec["name"],
            )
        )
        if area is None:
            area = Area(room_id=room.id, name=area_spec["name"])
            db.add(area)
            db.flush()

        existing_nos = set(
            db.scalars(select(Seat.seat_no).where(Seat.room_id == room.id)).all()
        )
        for seat_no, has_power, near_window in area_spec["seats"]:
            if seat_no in existing_nos:
                continue
            db.add(
                Seat(
                    room_id=room.id,
                    area_id=area.id,
                    seat_no=seat_no,
                    seat_type="普通",
                    has_power=has_power,
                    near_window=near_window,
                    status=SeatStatus.AVAILABLE.value,
                )
            )
            existing_nos.add(seat_no)
            added += 1

    db.flush()
    total = len(
        db.scalars(select(Seat.id).where(Seat.room_id == room.id)).all()
    )
    room.capacity = total
    return added


def main() -> None:
    created_rooms = 0
    added_seats = 0
    topped_up_rooms = 0

    with SessionLocal() as db:
        for spec in DEMO_ROOMS:
            room = db.scalar(select(Room).where(Room.name == spec["name"]))
            if room is None:
                room = Room(
                    name=spec["name"],
                    location=spec["location"],
                    open_time=spec["open_time"],
                    close_time=spec["close_time"],
                    capacity=0,
                )
                db.add(room)
                db.flush()
                created_rooms += 1
            else:
                topped_up_rooms += 1

            added = _sync_room_layout(db, room, spec)
            added_seats += added
            if added:
                print(f"补齐演示自习室「{spec['name']}」座位：+{added}")

        db.commit()

    print(
        "演示资源已就绪："
        f"新增自习室 {created_rooms} 间，补齐 {topped_up_rooms} 间，"
        f"新增座位 {added_seats} 个"
    )


if __name__ == "__main__":
    main()
