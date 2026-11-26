"""演示数据脚本：生成与重置的回归测试（SQLite 内存库）。"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select

from app.models.enums import ReservationStatus
from app.models.message import StationMessage
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from scripts import seed_demo_data as seed


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_seed_and_reset_demo_data(db, monkeypatch):
    # 站内通知默认走独立 SessionLocal（真实 MySQL）；测试中改为空操作。
    from app.services import notification_service

    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)

    # 非演示用户的数据：重置时必须原样保留。
    outsider = User(
        name="普通同学",
        student_no="S9999",
        password_hash="hash",
        role="学生用户",
    )
    db.add(outsider)
    db.flush()
    outsider_reservation = Reservation(
        user_id=outsider.id,
        seat_id=1,  # 外键在 SQLite 测试库中未开启，仅用于计数
        reserve_date=date(2026, 1, 1),
        start_time=time(9, 0),
        end_time=time(10, 0),
        status=ReservationStatus.COMPLETED.value,
        idempotency_key="outsider-key",
    )
    db.add(outsider_reservation)
    db.add(StationMessage(user_id=outsider.id, type="系统通知", title="保留", content="保留"))
    db.commit()

    stats = seed.seed_demo_data(db)
    assert stats["reservations"] >= 14
    assert stats["violations"] == 5
    assert stats["complaints"] == 4
    assert stats["reviews"] == 4
    assert stats["closures"] == 1

    # 演示数据必须覆盖当前 3 间自习室，而不是旧版的 2 间布局。
    used_rooms = set(
        db.scalars(
            select(Seat.room_id)
            .join(Reservation, Reservation.seat_id == Seat.id)
            .where(Reservation.idempotency_key.like("demo-seed-%"))
        ).all()
    )
    assert len(used_rooms) == 3

    student = db.scalar(select(User).where(User.student_no == "student"))
    wang = db.scalar(select(User).where(User.student_no == "demo_wang"))
    assert student is not None and student.violation_count == 1
    assert wang is not None and wang.account_status == "受限"

    # 预约槽位只属于有效预约；历史终态不占用时段。
    from app.models.reservation_slot import ReservationSlot

    active = db.scalar(
        select(func.count())
        .select_from(ReservationSlot)
        .where(ReservationSlot.user_id == student.id)
    )
    assert active and active > 0

    removed = seed.reset_demo_data(db)
    assert removed["reservations"] == stats["reservations"]
    assert removed["closures"] == 1
    assert _count(db, StationMessage) == 1  # 只剩非演示用户的消息
    assert db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.user_id == outsider.id)
    ) == 1
    assert db.scalar(
        select(User.violation_count).where(User.id == outsider.id)
    ) == 0


def test_seed_after_closing_keeps_checkin_demo_without_user_conflict(
    db, monkeypatch
) -> None:
    """夜间重置时签到演示顺延到明天 13:00，不能撞上明天 09:00-11:00 的取消演示。"""
    from app.services import notification_service

    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)

    now = datetime(2026, 11, 26, 21, 30)
    stats = seed.seed_demo_data(db, now=now)
    assert stats["check_in_ready"] == 0

    soon = db.scalar(
        select(Reservation).where(
            Reservation.idempotency_key == "demo-seed-student-soon"
        )
    )
    tomorrow = db.scalar(
        select(Reservation).where(
            Reservation.idempotency_key == "demo-seed-student-tomorrow"
        )
    )
    assert soon is not None and tomorrow is not None
    assert soon.reserve_date == now.date() + timedelta(days=1)
    assert soon.start_time == time(13, 0)
    # 两个有效预约不能存在时间重叠（C4 / 槽位唯一约束）。
    assert not (
        soon.start_time < tomorrow.end_time and tomorrow.start_time < soon.end_time
    )
