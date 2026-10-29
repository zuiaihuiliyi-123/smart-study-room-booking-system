"""创建演示数据：python -m scripts.seed

幂等：已存在的用户、自习室、座位不会重复创建。
演示账户：admin / admin123（管理员），student / student123（学生）。
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import Role, SeatStatus
from app.models.room import Area, Room
from app.models.seat import Seat
from app.models.user import User

DEMO_USERS = [
    ("admin", "admin123", "演示管理员", Role.ADMIN.value),
    ("student", "student123", "演示学生", Role.STUDENT.value),
    ("student2", "student123", "演示学生二", Role.STUDENT.value),
]

ROOM_NAME = "图书馆三层自习室"
AREA_NAME = "A 区"
SEAT_COUNT = 10


def main() -> None:
    with SessionLocal() as db:
        for student_no, password, name, role in DEMO_USERS:
            exists = db.scalar(select(User).where(User.student_no == student_no))
            if exists is None:
                db.add(
                    User(
                        name=name,
                        student_no=student_no,
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
        db.commit()

        room = db.scalar(select(Room).where(Room.name == ROOM_NAME))
        if room is None:
            room = Room(
                name=ROOM_NAME,
                location="图书馆三层东侧",
                open_time="08:00",
                close_time="22:00",
                capacity=SEAT_COUNT,
                enabled=True,
            )
            db.add(room)
            db.commit()
            db.refresh(room)

        area = db.scalar(
            select(Area).where(Area.room_id == room.id, Area.name == AREA_NAME)
        )
        if area is None:
            area = Area(room_id=room.id, name=AREA_NAME)
            db.add(area)
            db.commit()
            db.refresh(area)

        existing_seat_nos = {
            seat.seat_no
            for seat in db.scalars(select(Seat).where(Seat.room_id == room.id)).all()
        }
        for index in range(1, SEAT_COUNT + 1):
            seat_no = f"A-{index:02d}"
            if seat_no in existing_seat_nos:
                continue
            db.add(
                Seat(
                    room_id=room.id,
                    area_id=area.id,
                    seat_no=seat_no,
                    seat_type="标准位",
                    has_power=index % 2 == 1,
                    status=SeatStatus.AVAILABLE.value,
                )
            )
        db.commit()

    print("演示数据已就绪：")
    print("  管理员：admin / admin123")
    print("  学生一：student / student123")
    print("  学生二：student2 / student123")
    print(f"  自习室：{ROOM_NAME}（{SEAT_COUNT} 个座位）")


if __name__ == "__main__":
    main()
