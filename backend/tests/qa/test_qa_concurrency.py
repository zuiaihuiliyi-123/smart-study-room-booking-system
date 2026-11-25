"""阶段 3 · 并发与竞态复现用例（文件型 SQLite + 独立 session）。"""

from __future__ import annotations

import tempfile
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.core.security import hash_password
from app.models.blacklist import BlacklistEntry
from app.models.enums import AccountStatus, ReservationStatus, Role, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Room, RoomClosure
from app.models.seat import Seat
from app.models.user import User
from app.schemas.blacklist import BlacklistCreate
from app.schemas.reservation import ReservationCreate
from app.schemas.room import RoomCloseRequest
from app.services import (
    attendance_service,
    blacklist_service,
    notification_service,
    reservation_command_service,
    reservation_service,
    room_service,
)
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 24, 10, 0)
D1 = date(2026, 11, 25)
BARRIER_TIMEOUT = 5


@pytest.fixture()
def file_db():
    tmp = Path(tempfile.gettempdir()) / f"ssr_qa_{threading.get_ident()}_{_time.time_ns()}.db"
    engine = create_engine(f"sqlite:///{tmp}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _busy_timeout(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session, factory
    finally:
        session.close()
        engine.dispose()
        if tmp.exists():
            tmp.unlink()


@pytest.fixture(autouse=True)
def _freeze_and_silence(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _seed(session, users: int = 1):
    room = Room(name="QA 并发自习室", location="测试", capacity=10)
    session.add(room)
    session.flush()
    seat = Seat(
        room_id=room.id,
        seat_no="QA-01",
        seat_type="普通",
        status=SeatStatus.AVAILABLE.value,
    )
    session.add(seat)
    session.flush()
    created: list[User] = []
    for index in range(users):
        user = User(
            name=f"并发学生{index}",
            student_no=f"QAC{index:03d}",
            password_hash=hash_password("Ss123456"),
            role=Role.STUDENT.value,
            account_status=AccountStatus.NORMAL.value,
        )
        session.add(user)
        session.flush()
        created.append(user)
    admin = User(
        name="并发管理员",
        student_no="QAA000",
        password_hash=hash_password("Aa123456"),
        role=Role.ADMIN.value,
        account_status=AccountStatus.NORMAL.value,
    )
    session.add(admin)
    session.commit()
    return room.id, seat.id, [item.id for item in created], admin.id


def _payload(seat_id: int, key: str, start: time = time(14, 0), end: time = time(16, 0)):
    return ReservationCreate(
        seat_id=seat_id,
        reserve_date=D1,
        start_time=start,
        end_time=end,
        idempotency_key=key,
    )


def test_same_idempotency_key_concurrently_sends_one_success_message(
    file_db, monkeypatch
):
    session, factory = file_db
    _, seat_id, user_ids, _ = _seed(session)
    messages: list[str] = []
    lock = threading.Lock()

    def _count(**kwargs):
        with lock:
            messages.append(kwargs.get("title", ""))

    monkeypatch.setattr(notification_service, "notify_safe", _count)

    original_find = reservation_command_service._find_by_idempotency_key
    barrier = threading.Barrier(5, timeout=BARRIER_TIMEOUT)
    counter = {"n": 0}
    counter_lock = threading.Lock()

    def _find_with_barrier(db, user_id, key):
        with counter_lock:
            counter["n"] += 1
            index = counter["n"]
        if index <= 5:
            barrier.wait()
        return original_find(db, user_id, key)

    monkeypatch.setattr(
        reservation_command_service, "_find_by_idempotency_key", _find_with_barrier
    )

    def attempt() -> int | None:
        with factory() as db:
            user = db.get(User, user_ids[0])
            try:
                return reservation_service.create_reservation(
                    db, user, _payload(seat_id, "qa-conc-key-01")
                ).id
            except Exception:
                return None

    with ThreadPoolExecutor(max_workers=5) as pool:
        ids = [future.result() for future in [pool.submit(attempt) for _ in range(5)]]

    with factory() as verify:
        reservations = verify.query(Reservation).all()
        assert len(reservations) == 1
    assert len({item for item in ids if item is not None}) == 1
    assert len([title for title in messages if title == "预约成功"]) == 1, (
        f"同一幂等键并发提交产生了 {len(messages)} 条预约成功消息"
    )


def test_checkin_vs_force_cancel_race(file_db, monkeypatch):
    session, factory = file_db
    _, seat_id, user_ids, admin_id = _seed(session)
    reservation = Reservation(
        user_id=user_ids[0],
        seat_id=seat_id,
        reserve_date=FIXED_NOW.date(),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status=ReservationStatus.PENDING.value,
        idempotency_key="qa-race-checkin-01",
    )
    session.add(reservation)
    session.commit()
    reservation_id = reservation.id

    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)
    original_attendance_get = attendance_service._get_reservation
    original_command_get = reservation_command_service.get_reservation

    def _attendance_get(db, rid):
        record = original_attendance_get(db, rid)
        barrier.wait()
        _time.sleep(0.3)  # 让强制取消先提交，签到随后覆盖状态
        return record

    def _command_get(db, rid):
        record = original_command_get(db, rid)
        barrier.wait()
        return record

    monkeypatch.setattr(attendance_service, "_get_reservation", _attendance_get)
    monkeypatch.setattr(reservation_command_service, "get_reservation", _command_get)

    errors: list[Exception] = []

    def do_checkin():
        with factory() as db:
            try:
                attendance_service.check_in(db, user_ids[0], reservation_id)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    def do_force_cancel():
        with factory() as db:
            try:
                reservation_command_service.force_cancel(
                    db, admin_id, reservation_id, type("P", (), {"reason": "测试取消"})()
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(do_checkin)
        pool.submit(do_force_cancel).result(timeout=10)

    with factory() as verify:
        final = verify.get(Reservation, reservation_id)
        contradiction = (
            final.status == ReservationStatus.IN_USE.value
            and final.cancel_time is not None
        ) or (
            final.status == ReservationStatus.CANCELLED.value
            and final.check_in_time is not None
        )
        assert not contradiction, (
            "并发后出现矛盾终态："
            f"status={final.status}, check_in={final.check_in_time}, "
            f"cancel={final.cancel_time}, cancelled_by={final.cancelled_by_id}; "
            f"errors={[type(exc).__name__ + ': ' + str(exc) for exc in errors]}"
        )
        # 记录两个线程各自的异常，用于判断是“业务正确拒绝”还是“数据库快照冲突”
        print(f"\nRACE errors={[type(exc).__name__ for exc in errors]} final={final.status}")


def test_close_room_vs_new_reservation_race(file_db, monkeypatch):
    session, factory = file_db
    room_id, seat_id, user_ids, admin_id = _seed(session)
    start_at = datetime.combine(D1, time(14, 0))
    end_at = datetime.combine(D1, time(16, 0))

    read_done = threading.Event()
    create_done = threading.Event()
    original_affected = room_service._affected

    def _affected_then_wait(db, room, area, start, end, **kwargs):
        result = original_affected(db, room, area, start, end, **kwargs)
        read_done.set()
        create_done.wait(timeout=BARRIER_TIMEOUT)
        return result

    monkeypatch.setattr(room_service, "_affected", _affected_then_wait)

    result: dict[str, object] = {}

    def do_close():
        with factory() as db:
            try:
                closed = room_service.close_room(
                    db,
                    room_id,
                    RoomCloseRequest(
                        start_at=start_at,
                        end_at=end_at,
                        reason="临时维修",
                        cancel_affected=False,
                        expected_reservation_ids=[],
                    ),
                    admin_id,
                )
                result["closed_seats"] = closed.closed_seats
            except Exception as exc:  # noqa: BLE001
                result["error"] = type(exc).__name__
                result["code"] = getattr(exc, "code", None)

    def do_create():
        with factory() as db:
            user = db.get(User, user_ids[0])
            reservation_service.create_reservation(
                db, user, _payload(seat_id, "qa-close-race-01")
            )
            result["reservation_id"] = 1

    with ThreadPoolExecutor(max_workers=2) as pool:
        close_future = pool.submit(do_close)
        assert read_done.wait(timeout=BARRIER_TIMEOUT)
        create_future = pool.submit(do_create)
        create_future.result(timeout=10)
        create_done.set()
        close_future.result(timeout=10)

    with factory() as verify:
        closure_exists = (
            verify.query(RoomClosure)
            .filter(
                RoomClosure.room_id == room_id,
                RoomClosure.start_at < end_at,
                RoomClosure.end_at > start_at,
            )
            .count()
        )
        inside = (
            verify.query(Reservation)
            .filter(
                Reservation.seat_id == seat_id,
                Reservation.reserve_date == D1,
                Reservation.start_time < time(16, 0),
                Reservation.end_time > time(14, 0),
                Reservation.status.in_(
                    (ReservationStatus.PENDING.value, ReservationStatus.IN_USE.value)
                ),
            )
            .count()
        )
        assert not (closure_exists and inside > 0), (
            f"关闭生效后仍有 {inside} 条有效预约落在关闭窗口内；result={result}"
        )
        # 新预约已插入时，正确行为是 409 要求重新预览，而不是静默关闭
        assert closure_exists or result.get("code") == "CONFLICT_LIST_CHANGED", (
            f"关闭既未成功也未按冲突拒绝：result={result}"
        )


def test_concurrent_manual_blacklist_only_one_active(file_db, monkeypatch):
    session, factory = file_db
    _, _, user_ids, admin_id = _seed(session)
    target_id = user_ids[0]

    original_active = blacklist_service._active_entries
    barrier = threading.Barrier(2, timeout=BARRIER_TIMEOUT)
    counter = {"n": 0}
    counter_lock = threading.Lock()

    def _active_with_barrier(db, user_id, now):
        with counter_lock:
            counter["n"] += 1
            index = counter["n"]
        if index <= 2:
            barrier.wait()
        return original_active(db, user_id, now)

    monkeypatch.setattr(blacklist_service, "_active_entries", _active_with_barrier)

    results: list[str] = []
    result_lock = threading.Lock()

    def add():
        with factory() as db:
            admin = db.get(User, admin_id)
            try:
                blacklist_service.add_entry(
                    db,
                    admin,
                    BlacklistCreate(
                        user_id=target_id,
                        reason="并发加入测试",
                        expire_at=FIXED_NOW + timedelta(days=7),
                    ),
                )
                outcome = "success"
            except Exception as exc:  # noqa: BLE001
                outcome = type(exc).__name__
            with result_lock:
                results.append(outcome)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(add) for _ in range(2)]
        for future in futures:
            future.result(timeout=10)

    with factory() as verify:
        active = (
            verify.query(BlacklistEntry)
            .filter(
                BlacklistEntry.user_id == target_id,
                BlacklistEntry.released_at.is_(None),
            )
            .count()
        )
    assert active == 1, f"并发加入黑名单产生了 {active} 条生效记录：{results}"
