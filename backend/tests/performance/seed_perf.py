"""性能测试数据生成器（仅用于隔离数据库，禁止在生产库执行）。

用法：
    DATABASE_URL="mysql+pymysql://root:@127.0.0.1:3307/ssr_perf?charset=utf8mb4" \
      .venv/Scripts/python.exe -m tests.performance.seed_perf \
      --context ".perf/context.json"

生成：3 间自习室 × 2 区 × 50 座 = 300 座；200 名学生 + 1 名管理员
（前 100 名无预约用于写入测试，后 100 名承载历史数据）；
约 1790 张预约（历史已完成 / 明日待使用 / 已取消 / 已违约）、300 条违约、500 条审计。
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import insert, select

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    ReservationStatus,
    Role,
    SeatStatus,
    ViolationType,
)
from app.models.reservation import Reservation
from app.models.room import Area, Room
from app.models.seat import Seat
from app.models.user import User
from app.models.violation import ViolationRecord
from app.utils import time_utils

RNG = random.Random(42)
STUDENTS = 200
ROOMS = 3
AREAS_PER_ROOM = 2
SEATS_PER_AREA = 50


def _seed_users(db) -> tuple[list[User], User]:
    students = [
        User(
            name=f"性能学生{i:03d}",
            student_no=f"PERF{i:03d}",
            password_hash="perf-not-used",
            role=Role.STUDENT.value,
            account_status=AccountStatus.NORMAL.value,
        )
        for i in range(1, STUDENTS + 1)
    ]
    admin = User(
        name="性能管理员",
        student_no="perfadmin",
        password_hash=hash_password("admin123"),
        role=Role.ADMIN.value,
        account_status=AccountStatus.NORMAL.value,
    )
    db.add_all(students + [admin])
    db.flush()
    return students, admin


def _seed_rooms(db) -> tuple[list[Room], list[Area], list[Seat]]:
    rooms: list[Room] = []
    areas: list[Area] = []
    seats: list[Seat] = []
    for r in range(ROOMS):
        room = Room(
            name=f"性能测试馆{r + 1}",
            location=f"性能测试楼 {r + 1} 层",
            open_time="08:00",
            close_time="22:00",
            capacity=AREAS_PER_ROOM * SEATS_PER_AREA,
        )
        rooms.append(room)
        db.add(room)
        db.flush()

        for a in range(AREAS_PER_ROOM):
            area = Area(room_id=room.id, name=f"{chr(65 + a)} 区")
            areas.append(area)
            db.add(area)
            db.flush()
            for s in range(1, SEATS_PER_AREA + 1):
                seats.append(
                    Seat(
                        room_id=room.id,
                        area_id=area.id,
                        seat_no=f"{chr(65 + a)}-{s:03d}",
                        seat_type="普通",
                        has_power=s % 3 == 0,
                        near_window=a == 1,
                        status=SeatStatus.AVAILABLE.value,
                    )
                )
        db.add_all(seats[-AREAS_PER_ROOM * SEATS_PER_AREA :])
        db.flush()
    return rooms, areas, seats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True, help="性能测试上下文 JSON 输出路径")
    args = parser.parse_args()

    today = time_utils.now().date()
    tomorrow = today + timedelta(days=1)

    with SessionLocal() as db:
        students, admin = _seed_users(db)
        # 前 100 名用于写入测试（保证当日无预约、不会触发每日上限）；
        # 后 100 名承载历史/待使用/违约数据，用于读取与看板测试。
        free_students = students[:100]
        busy_students = students[100:]
        rooms, _areas, seats = _seed_rooms(db)
        db.commit()

        completed: list[dict] = []
        cancelled: list[dict] = []
        violated: list[dict] = []
        pending: list[dict] = []
        seq = 0

        # 历史已完成：过去 7 天，每天覆盖多个时段
        for day_offset in range(1, 8):
            day = today - timedelta(days=day_offset)
            for i in range(170):
                seq += 1
                start_hour = 8 + (i % 7) * 2
                start = time(start_hour, 0)
                end = time(start_hour + 2, 0)
                completed.append(
                    {
                        "user_id": busy_students[i % len(busy_students)].id,
                        "seat_id": seats[i % len(seats)].id,
                        "reserve_date": day,
                        "start_time": start,
                        "end_time": end,
                        "status": ReservationStatus.COMPLETED.value,
                        "check_in_time": datetime.combine(day, start),
                        "check_out_time": datetime.combine(day, end),
                        "idempotency_key": f"perf-completed-{seq}",
                        "created_at": datetime.combine(day, time(7, 30)),
                        "updated_at": datetime.combine(day, end),
                    }
                )

        # 明日待使用：避开 14:00-16:00，保证该时段可预约查询与写入测试有空位
        for i in range(200):
            seq += 1
            pending.append(
                {
                    "user_id": busy_students[(i + 20) % len(busy_students)].id,
                    "seat_id": seats[(i + 10) % len(seats)].id,
                    "reserve_date": tomorrow,
                    "start_time": time(18, 0),
                    "end_time": time(20, 0),
                    "status": ReservationStatus.PENDING.value,
                    "idempotency_key": f"perf-pending-{seq}",
                }
            )

        for i in range(200):
            seq += 1
            cancelled.append(
                {
                    "user_id": busy_students[(i + 40) % len(busy_students)].id,
                    "seat_id": seats[(i + 150) % len(seats)].id,
                    "reserve_date": tomorrow,
                    "start_time": time(20, 0),
                    "end_time": time(22, 0),
                    "status": ReservationStatus.CANCELLED.value,
                    "cancel_time": time_utils.now() - timedelta(hours=1),
                    "cancel_reason": "性能测试取消",
                    "idempotency_key": f"perf-cancelled-{seq}",
                }
            )

        for i in range(200):
            seq += 1
            violated.append(
                {
                    "user_id": busy_students[(i + 60) % len(busy_students)].id,
                    "seat_id": seats[(i + 250) % len(seats)].id,
                    "reserve_date": today - timedelta(days=1 + i % 3),
                    "start_time": time(8, 0),
                    "end_time": time(10, 0),
                    "status": ReservationStatus.VIOLATED.value,
                    "idempotency_key": f"perf-violated-{seq}",
                }
            )

        rows = completed + pending + cancelled + violated
        db.execute(insert(Reservation), rows)
        db.commit()

        violated_ids = list(
            db.scalars(
                select(Reservation.id)
                .where(Reservation.status == ReservationStatus.VIOLATED.value)
                .limit(200)
            ).all()
        )
        completed_ids = list(
            db.scalars(
                select(Reservation.id)
                .where(Reservation.status == ReservationStatus.COMPLETED.value)
                .limit(100)
            ).all()
        )
        violation_rows = [
            {
                "user_id": busy_students[i % len(busy_students)].id,
                "reservation_id": violated_ids[i],
                "type": ViolationType.AUTO.value,
                "reason": "性能测试自动违约",
                "created_at": time_utils.now() - timedelta(days=1, minutes=i),
            }
            for i in range(len(violated_ids))
        ] + [
            {
                "user_id": busy_students[(i + 30) % len(busy_students)].id,
                "reservation_id": completed_ids[i],
                "type": ViolationType.MANUAL.value,
                "reason": "性能测试手动违约",
                "created_at": time_utils.now() - timedelta(days=2, minutes=i),
            }
            for i in range(len(completed_ids))
        ]
        db.execute(insert(ViolationRecord), violation_rows)

        audit_rows = [
            {
                "operator_id": admin.id,
                "action_type": "PERF_AUDIT",
                "target_type": "USER",
                "target_id": students[i % len(students)].id,
                "reason": f"性能测试审计 {i}",
                "created_at": time_utils.now() - timedelta(minutes=i),
            }
            for i in range(500)
        ]
        db.execute(insert(AuditLog), audit_rows)
        db.commit()

        student_tokens = [
            create_access_token(str(user.id), user.role, user.token_version or 0)
            for user in busy_students
        ]
        free_tokens = [
            create_access_token(str(user.id), user.role, user.token_version or 0)
            for user in free_students
        ]
        admin_token = create_access_token(
            str(admin.id), admin.role, admin.token_version or 0
        )

        # 写入测试：明日 14:00-16:00，100 名学生各订不同座位
        write_cases = [
            {
                "token": free_tokens[i],
                "seat_id": seats[i].id,
                "reserve_date": tomorrow.isoformat(),
                "start_time": "14:00",
                "end_time": "16:00",
                "idempotency_key": f"perf-write-{i}-{tomorrow.isoformat()}",
            }
            for i in range(100)
        ]

        context = {
            "base_url": "http://127.0.0.1:8010",
            "room_id": rooms[0].id,
            "student_tokens": student_tokens,
            "admin_token": admin_token,
            "admin_login": {"student_no": "perfadmin", "password": "admin123"},
            "tomorrow": tomorrow.isoformat(),
            "write_cases": write_cases,
        }
        path = Path(args.context)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"性能数据已生成：{len(students)} 学生 / {len(seats)} 座位 / "
        f"{len(rows)} 预约 / {len(violation_rows)} 违约 / {len(audit_rows)} 审计"
    )
    print(f"上下文：{args.context}")


if __name__ == "__main__":
    main()
