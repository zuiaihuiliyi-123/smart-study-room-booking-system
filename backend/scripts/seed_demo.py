"""创建演示资源数据（自习室 / 分区 / 座位）：python -m scripts.seed_demo

幂等：同名自习室已存在时整间跳过，不会重复插入分区或座位。
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
                ],
            },
        ],
    },
]


def main() -> None:
    created_rooms = 0
    created_seats = 0

    with SessionLocal() as db:
        for spec in DEMO_ROOMS:
            if db.scalar(select(Room).where(Room.name == spec["name"])) is not None:
                print(f"跳过已存在的自习室：{spec['name']}")
                continue

            seat_total = sum(len(area["seats"]) for area in spec["areas"])
            room = Room(
                name=spec["name"],
                location=spec["location"],
                open_time=spec["open_time"],
                close_time=spec["close_time"],
                capacity=seat_total,
            )
            db.add(room)
            db.flush()

            for area_spec in spec["areas"]:
                area = Area(room_id=room.id, name=area_spec["name"])
                db.add(area)
                db.flush()

                for seat_no, has_power, near_window in area_spec["seats"]:
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
                    created_seats += 1

            created_rooms += 1

        db.commit()

    print(f"演示资源已就绪：新增自习室 {created_rooms} 间，座位 {created_seats} 个")


if __name__ == "__main__":
    main()
