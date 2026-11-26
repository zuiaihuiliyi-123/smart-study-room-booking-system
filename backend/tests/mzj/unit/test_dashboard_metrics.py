"""M6 看板单元测试：统计口径、30 分钟折算、Top N 排序与趋势区间。"""

from datetime import date, datetime, time

from app.models.enums import (
    AccountStatus,
    ReservationStatus,
    SeatStatus,
    ViolationType,
)
from app.services import dashboard_service


def test_seat_usage_counts_completed_blocks_only(
    db, make_room, make_seat, make_user, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    spare = make_seat(room.id)
    other_room = make_room()
    outside = make_seat(other_room.id)
    student = make_user(student_no="S94001")
    day = date(2026, 11, 26)

    def add(start: time, end: time, status: str) -> None:
        make_reservation(
            student.id,
            seat.id,
            reserve_date=day,
            start_time=start,
            end_time=end,
            status=status,
        )

    add(time(8, 0), time(8, 30), ReservationStatus.COMPLETED.value)  # 1 个统计块
    add(time(14, 0), time(18, 0), ReservationStatus.COMPLETED.value)  # 8 个统计块
    add(time(9, 0), time(9, 5), ReservationStatus.COMPLETED.value)  # 5 分钟不足一块
    add(time(10, 0), time(12, 0), ReservationStatus.CANCELLED.value)  # 不计
    add(time(12, 0), time(14, 0), ReservationStatus.VIOLATED.value)  # 不计
    make_reservation(
        student.id,
        outside.id,
        reserve_date=day,
        start_time=time(8, 0),
        end_time=time(10, 0),
        status=ReservationStatus.COMPLETED.value,
    )

    items = dashboard_service.get_seat_usage(db, day, day, room_id=room.id)
    values = {item.name: item.value for item in items}

    assert values[seat.seat_no] == 9
    assert values[spare.seat_no] == 0
    assert outside.seat_no not in values

    all_items = dashboard_service.get_seat_usage(db, day, day)
    assert {item.name for item in all_items} == {
        seat.seat_no,
        spare.seat_no,
        outside.seat_no,
    }


def test_seat_usage_by_slot_capacity_and_rate(
    db, make_room, make_seat, make_student, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_student(student_no="S94002")
    day = date(2026, 11, 26)
    make_reservation(
        student.id,
        seat.id,
        reserve_date=day,
        start_time=time(8, 0),
        end_time=time(8, 30),
        status=ReservationStatus.COMPLETED.value,
    )

    rows = dashboard_service.get_seat_usage_by_slot(db, day, day)
    bucket = next(row for row in rows if row.slot == "08:00-10:00")
    empty_bucket = next(row for row in rows if row.slot == "10:00-12:00")

    # 1 座 × 1 天 × 2 小时 / 30 分钟 = 4 个统计块
    assert bucket.capacity == 4
    assert bucket.occupied == 1.0
    assert bucket.rate == 0.25
    assert (empty_bucket.occupied, empty_bucket.rate) == (0.0, 0.0)


def test_seat_usage_by_slot_reads_short_reservation_as_fraction(
    db, make_room, make_seat, make_student, make_reservation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_student(student_no="S94003")
    day = date(2026, 11, 26)
    make_reservation(
        student.id,
        seat.id,
        reserve_date=day,
        start_time=time(10, 0),
        end_time=time(10, 5),
        status=ReservationStatus.COMPLETED.value,
    )

    rows = dashboard_service.get_seat_usage_by_slot(db, day, day)
    bucket = next(row for row in rows if row.slot == "10:00-12:00")

    # 5 / 30 → 0.17 块；0.17 / 4 → 0.0425，避免整数除法把短预约计成 0
    assert bucket.occupied == 0.17
    assert bucket.rate == 0.0425


def test_seat_usage_by_slot_handles_empty_room_and_invalid_range(db, make_room) -> None:
    make_room()

    rows = dashboard_service.get_seat_usage_by_slot(
        db, date(2026, 11, 26), date(2026, 11, 26)
    )

    assert len(rows) == 7
    assert all(row.capacity == 0 and row.rate == 0.0 for row in rows)
    assert (
        dashboard_service.get_seat_usage_by_slot(
            db, date(2026, 11, 26), date(2026, 11, 25)
        )
        == []
    )


def test_overview_scopes_by_room_but_restricted_accounts_global(
    db,
    freeze_now,
    make_room,
    make_seat,
    make_student,
    make_admin,
    make_reservation,
    make_violation,
) -> None:
    now = freeze_now
    today = now.date()
    room1 = make_room()
    room2 = make_room()
    seat1 = make_seat(room1.id)
    seat2 = make_seat(room1.id)
    make_seat(room1.id, status=SeatStatus.MAINTENANCE.value)
    seat3 = make_seat(room2.id)

    student = make_student(student_no="S94010")
    make_student(student_no="S94011", account_status=AccountStatus.RESTRICTED.value)
    admin = make_admin()

    in_use_1 = make_reservation(
        student.id,
        seat1.id,
        reserve_date=today,
        start_time=time(9, 0),
        end_time=time(11, 0),
        status=ReservationStatus.IN_USE.value,
    )
    make_reservation(
        student.id,
        seat3.id,
        reserve_date=today,
        start_time=time(9, 0),
        end_time=time(11, 0),
        status=ReservationStatus.IN_USE.value,
    )
    make_reservation(
        student.id,
        seat2.id,
        reserve_date=today,
        start_time=time(14, 0),
        end_time=time(16, 0),
        status=ReservationStatus.PENDING.value,
    )
    make_reservation(
        student.id,
        seat2.id,
        reserve_date=today,
        start_time=time(16, 0),
        end_time=time(18, 0),
        status=ReservationStatus.CANCELLED.value,
    )
    make_violation(student.id, in_use_1.id, created_at=now)
    # 管理员的历史违约不进入“学生今日违约”
    make_violation(
        admin.id,
        in_use_1.id,
        type=ViolationType.MANUAL.value,
        created_at=now,
    )

    scoped = dashboard_service.get_overview(db, room_id=room1.id)
    assert scoped.seat_total == 2  # 维修中座位不计入“可预约座位”
    assert scoped.in_use == 1
    assert scoped.today_reservations == 2  # 已取消不计
    assert scoped.today_violations == 1
    assert scoped.restricted_accounts == 1  # 账户不归属自习室，保持全局

    overall = dashboard_service.get_overview(db)
    assert overall.seat_total == 3
    assert overall.in_use == 2
    assert overall.today_reservations == 3
    assert overall.today_violations == 1
    assert overall.restricted_accounts == 1


def test_violation_top_is_student_only_with_limit_and_tie_order(
    db,
    freeze_now,
    make_room,
    make_seat,
    make_student,
    make_admin,
    make_reservation,
    make_violation,
) -> None:
    now = freeze_now
    today = now.date()
    room = make_room()
    seat = make_seat(room.id)
    first = make_student(student_no="S94020")
    second = make_student(student_no="S94021")
    third = make_student(student_no="S94022")
    admin = make_admin()

    def add_violation(user, hour: int) -> None:
        reservation = make_reservation(
            user.id,
            seat.id,
            reserve_date=today,
            start_time=time(hour, 0),
            end_time=time(hour + 1, 0),
        )
        make_violation(user.id, reservation.id, created_at=now)

    add_violation(first, 8)
    add_violation(first, 9)
    add_violation(second, 10)
    add_violation(second, 11)
    add_violation(third, 12)
    add_violation(admin, 13)

    response = dashboard_service.get_violation_top(db, today, today, limit=2)

    assert response.total_records == 5  # 管理员记录不计
    assert [item.user_id for item in response.items] == [first.id, second.id]
    assert [item.count for item in response.items] == [2, 2]
    assert all(item.name and item.student_no for item in response.items)


def test_trend_range_limit_and_transition_dedupe(
    db, make_student, make_room, make_seat, make_reservation, make_violation
) -> None:
    room = make_room()
    seat = make_seat(room.id)
    student = make_student(student_no="S94030")
    reservation = make_reservation(
        student.id,
        seat.id,
        reserve_date=date(2026, 11, 2),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status=ReservationStatus.COMPLETED.value,
        check_in_time=datetime(2026, 11, 2, 10, 0),
        check_out_time=datetime(2026, 11, 2, 12, 0),
    )
    make_violation(student.id, reservation.id, created_at=datetime(2026, 11, 2, 12, 1))

    points = dashboard_service.get_trend(db, date(2026, 11, 1), date(2026, 11, 2))

    assert len(points) == 2
    assert (points[0].reservations, points[0].violations) == (0, 0)
    # 同一天既签到又签退仍按“预约单张数”计 1
    assert (points[1].reservations, points[1].violations) == (1, 1)

    # 32 天超过服务层上限 → 返回空列表（API 层对应 422）
    assert dashboard_service.get_trend(db, date(2026, 11, 1), date(2026, 12, 3)) == []
    assert len(dashboard_service.get_trend(db, date(2026, 11, 1), date(2026, 12, 1))) == 31
