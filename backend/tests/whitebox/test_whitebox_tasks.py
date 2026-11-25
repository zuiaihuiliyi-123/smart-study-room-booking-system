"""白盒测试：定时任务的扫描条件、幂等、异常隔离与调度注册。"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base
from app.models.enums import (
    AccountStatus,
    ReservationStatus,
    Role,
    SeatStatus,
    ViolationType,
)
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.room import Room
from app.models.seat import Seat
from app.models.task_execution import TaskExecution
from app.models.user import User
from app.models.violation import ViolationRecord
from app.services import notification_service, reservation_service
from app.tasks import (
    auto_end_reservation,
    auto_violation,
    blacklist_expiry,
    complaint_auto_close,
    login_attempt_cleanup,
    runtime,
    scheduler as scheduler_module,
)

D = date(2026, 11, 24)
NOW = datetime(2026, 11, 24, 15, 0)


@pytest.fixture()
def factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'whitebox_tasks.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture(autouse=True)
def _silence_notifications(monkeypatch):
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _seed(
    factory,
    *,
    student_no: str = "WB001",
    role: str = Role.STUDENT.value,
    status: str = ReservationStatus.PENDING.value,
    reserve_date: date = D,
    start: time = time(10, 0),
    end: time = time(12, 0),
) -> tuple[int, int, int]:
    with factory() as db:
        user = User(
            name="白盒学生",
            student_no=student_no,
            password_hash="hash",
            role=role,
            account_status=AccountStatus.NORMAL.value,
        )
        room = Room(
            name=f"白盒自习室{student_no}",
            location="测试",
            open_time="08:00",
            close_time="23:59",
        )
        db.add_all([user, room])
        db.flush()
        seat = Seat(
            room_id=room.id,
            seat_no="WB-01",
            status=SeatStatus.AVAILABLE.value,
        )
        db.add(seat)
        db.flush()
        reservation = Reservation(
            user_id=user.id,
            seat_id=seat.id,
            reserve_date=reserve_date,
            start_time=start,
            end_time=end,
            status=status,
            idempotency_key=f"wb-{student_no}-{status}-{start.hour}",
        )
        db.add(reservation)
        db.commit()
        return user.id, seat.id, reservation.id


def test_auto_violation_scans_due_pending_once(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_violation, "SessionLocal", factory)
    _, _, reservation_id = _seed(factory)

    assert auto_violation.scan_auto_violations(now=NOW) == 1
    assert auto_violation.scan_auto_violations(now=NOW) == 0  # 幂等

    with factory() as db:
        records = db.scalars(select(ViolationRecord)).all()
        assert len(records) == 1
        assert records[0].reservation_id == reservation_id
        assert records[0].type == ViolationType.AUTO.value
        reservation = db.get(Reservation, reservation_id)
        assert reservation.status == ReservationStatus.VIOLATED.value


def test_auto_violation_skips_not_due_cancelled_and_admin(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_violation, "SessionLocal", factory)
    _seed(factory, student_no="WB101", start=time(23, 0), end=time(23, 55))
    _seed(
        factory,
        student_no="WB102",
        status=ReservationStatus.CANCELLED.value,
    )
    _seed(factory, student_no="WB103", role=Role.ADMIN.value)

    assert auto_violation.scan_auto_violations(now=NOW) == 0


def test_auto_violation_continues_after_single_failure(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_violation, "SessionLocal", factory)
    _seed(factory, student_no="WB201")
    _seed(factory, student_no="WB202")
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("模拟单条处理失败")
        return None

    monkeypatch.setattr(auto_violation.violation_service, "apply_auto_violation", flaky)

    assert auto_violation.scan_auto_violations(now=NOW) == 0
    assert calls["n"] == 2  # 单条失败不阻断后续候选


def test_auto_end_completes_and_releases_slots(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_end_reservation, "SessionLocal", factory)
    _, seat_id, reservation_id = _seed(
        factory,
        status=ReservationStatus.IN_USE.value,
        end=time(12, 0),
    )
    with factory() as db:
        reservation = db.get(Reservation, reservation_id)
        db.add(
            ReservationSlot(
                reservation_id=reservation.id,
                seat_id=seat_id,
                user_id=reservation.user_id,
                slot_start=datetime.combine(D, time(11, 55)),
            )
        )
        db.commit()

    assert auto_end_reservation.finish_expired_reservations(now=NOW) == 1

    with factory() as db:
        reservation = db.get(Reservation, reservation_id)
        assert reservation.status == ReservationStatus.COMPLETED.value
        assert reservation.auto_completed is True
        assert reservation.check_out_time == datetime.combine(D, time(12, 0))
        assert db.scalars(select(ReservationSlot)).all() == []


def test_auto_end_skips_future_and_non_in_use(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_end_reservation, "SessionLocal", factory)
    _seed(
        factory,
        student_no="WB301",
        status=ReservationStatus.IN_USE.value,
        start=time(16, 0),
        end=time(18, 0),
    )
    _seed(factory, student_no="WB302", status=ReservationStatus.PENDING.value)
    _seed(factory, student_no="WB303", status=ReservationStatus.COMPLETED.value)

    assert auto_end_reservation.finish_expired_reservations(now=NOW) == 0


def test_auto_end_continues_after_release_failure(factory, monkeypatch) -> None:
    monkeypatch.setattr(auto_end_reservation, "SessionLocal", factory)
    _, _, first_id = _seed(factory, student_no="WB401", status=ReservationStatus.IN_USE.value)
    _, _, second_id = _seed(factory, student_no="WB402", status=ReservationStatus.IN_USE.value)
    original = reservation_service.release_slots

    def flaky(db, reservation_id):
        if reservation_id == first_id:
            raise RuntimeError("模拟释放槽位失败")
        return original(db, reservation_id)

    monkeypatch.setattr(auto_end_reservation.reservation_service, "release_slots", flaky)

    assert auto_end_reservation.finish_expired_reservations(now=NOW) == 1

    with factory() as db:
        assert db.get(Reservation, first_id).status == ReservationStatus.IN_USE.value
        assert db.get(Reservation, second_id).status == ReservationStatus.COMPLETED.value


def test_task_wrappers_delegate_to_services(factory, monkeypatch) -> None:
    monkeypatch.setattr(blacklist_expiry, "SessionLocal", factory)
    monkeypatch.setattr(blacklist_expiry.blacklist_service, "release_expired", lambda db: 2)
    blacklist_expiry.release_expired_restrictions()

    monkeypatch.setattr(complaint_auto_close, "SessionLocal", factory)
    monkeypatch.setattr(
        complaint_auto_close.complaint_service, "close_stale", lambda db: 3
    )
    complaint_auto_close.close_stale_complaints()

    monkeypatch.setattr(login_attempt_cleanup, "SessionLocal", factory)
    monkeypatch.setattr(
        login_attempt_cleanup.auth_service, "cleanup_login_attempts", lambda db: 4
    )
    assert login_attempt_cleanup.cleanup_login_attempts() == 4


def test_scheduler_registers_jobs_and_is_idempotent(monkeypatch) -> None:
    class FakeScheduler:
        def __init__(self) -> None:
            self.running = False
            self.jobs: dict[str, dict] = {}
            self.shutdown_called = False

        def add_job(self, func, trigger, **kwargs):
            self.jobs[kwargs["id"]] = {"trigger": trigger, **kwargs}

        def start(self) -> None:
            self.running = True

        def shutdown(self, wait=False) -> None:
            self.shutdown_called = True
            self.running = False

    fake = FakeScheduler()
    monkeypatch.setattr(scheduler_module, "scheduler", fake)
    monkeypatch.setattr(settings, "scheduler_enabled", True)

    scheduler_module.start_scheduler()
    assert fake.running is True
    assert set(fake.jobs) == {
        "auto_violation",
        "auto_end_reservation",
        "blacklist_expiry",
        "complaint_auto_close",
        "login_attempt_cleanup",
    }
    assert fake.jobs["login_attempt_cleanup"]["trigger"] == "cron"

    # 已在运行时再次启动不应重复注册
    scheduler_module.start_scheduler()
    assert len(fake.jobs) == 5

    scheduler_module.shutdown_scheduler()
    assert fake.shutdown_called is True


def test_scheduler_disabled_does_not_start(monkeypatch) -> None:
    class FakeScheduler:
        running = False

        def start(self) -> None:
            raise AssertionError("不应启动")

    monkeypatch.setattr(scheduler_module, "scheduler", FakeScheduler())
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    scheduler_module.start_scheduler()


def test_shutdown_when_not_running_is_noop(monkeypatch) -> None:
    class FakeScheduler:
        running = False

        def shutdown(self, wait=False) -> None:
            raise AssertionError("不应关闭")

    monkeypatch.setattr(scheduler_module, "scheduler", FakeScheduler())
    scheduler_module.shutdown_scheduler()


def test_run_scheduled_task_retries_and_records_failure(factory, monkeypatch) -> None:
    monkeypatch.setattr(runtime, "SessionLocal", factory)
    monkeypatch.setattr(settings, "scheduler_task_retries", 2)
    monkeypatch.setattr(settings, "scheduler_retry_delay_seconds", 0)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError("模拟任务失败")

    with pytest.raises(ValueError):
        runtime.run_scheduled_task("whitebox_failing_task", always_fails)

    assert calls["n"] == 2
    with factory() as db:
        execution = db.scalar(select(TaskExecution))
        assert execution is not None
        assert execution.task_name == "whitebox_failing_task"
        assert execution.status == "失败"
        assert execution.attempts == 2
        assert "ValueError" in (execution.error or "")
