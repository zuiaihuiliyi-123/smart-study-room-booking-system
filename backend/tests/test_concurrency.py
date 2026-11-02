"""VS-01 并发场景回归：同一座位同一时段并发预约恰好一条成功（Never-cut）。

行锁 + reservation_slots 唯一约束 + 幂等键共同保证并发不突破预约限制。
真实 MySQL 用独立连接 + with_for_update 行锁串行化校验；SQLite 的
with_for_update 是空操作，但 ``reservation_slots`` 的唯一约束 ``(seat_id, slot_start)``
仍在数据库层兜底——并发请求中只有第一条能成功插入槽位，其余触发 IntegrityError
后回退为 409 冲突。

为真实模拟并发（多 HTTP 请求 = 多独立 DB 连接），本文件使用**文件型 SQLite** +
``busy_timeout``，让并发写排队而非互相破坏（内存 SQLite + StaticPool 共享单连接
会在多线程下报 InterfaceError）。这与 conftest 的内存库 fixture 隔离。
"""

from __future__ import annotations

import tempfile
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  确保全部 ORM 模型注册
from app.core.database import Base
from app.core.security import hash_password
from app.models.enums import AccountStatus, ReservationStatus, Role, SeatStatus
from app.models.reservation import Reservation
from app.models.reservation_slot import ReservationSlot
from app.models.room import Room
from app.models.seat import Seat
from app.models.user import User
from app.services import notification_service, reservation_service
from app.schemas.reservation import ReservationCreate
from app.utils import time_utils


@pytest.fixture()
def concurrent_db():
    """文件型 SQLite：每个 session 独立连接到同一文件，busy_timeout 让并发写排队。"""
    tmp = Path(tempfile.gettempdir()) / f"ssr_concurrency_{threading.get_ident()}.db"
    if tmp.exists():
        tmp.unlink()
    engine = create_engine(
        f"sqlite:///{tmp}",
        connect_args={"check_same_thread": False},
    )

    # 让 SQLite 在写锁竞争时等待而非立即报 locked（模拟 MySQL 行锁排队）
    @event.listens_for(engine, "connect")
    def _set_busy_timeout(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
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
def _fixed_now_and_silent_notifications(monkeypatch):
    monkeypatch.setattr(time_utils, "now", lambda: datetime(2026, 11, 2, 10, 0))
    monkeypatch.setattr(notification_service, "notify_safe", lambda **kwargs: None)


def _payload(seat_id: int, day: date, key: str) -> ReservationCreate:
    return ReservationCreate(
        seat_id=seat_id,
        reserve_date=day,
        start_time=time(14, 0),
        end_time=time(16, 0),
        idempotency_key=key,
    )


def _setup_seat_and_users(session) -> tuple[int, list[int]]:
    room = Room(name="并发测试自习室", location="测试", capacity=1)
    session.add(room)
    session.flush()
    seat = Seat(
        room_id=room.id,
        seat_no="C-01",
        seat_type="普通",
        status=SeatStatus.AVAILABLE.value,
    )
    session.add(seat)
    session.flush()
    user_ids: list[int] = []
    for i in range(8):
        user = User(
            name=f"学生{i}",
            student_no=f"C{i:03d}",
            password_hash=hash_password("student123"),
            role=Role.STUDENT.value,
            account_status=AccountStatus.NORMAL.value,
        )
        session.add(user)
        session.flush()
        user_ids.append(user.id)
    session.commit()
    return seat.id, user_ids


def test_concurrent_same_seat_same_slot_only_one_succeeds(concurrent_db) -> None:
    """VS-01：8 个用户并发抢同一座位同一时段，恰好 1 条成功，其余被拒。"""
    session, factory = concurrent_db
    seat_id, user_ids = _setup_seat_and_users(session)
    day = datetime(2026, 11, 2, 10, 0).date() + timedelta(days=1)

    results: dict[int, str] = {}
    lock = threading.Lock()

    def attempt(user_id: int) -> tuple[int, str]:
        status = "error"
        # 每个线程独立 session（共享同一内存连接），模拟并发 HTTP 请求
        with factory() as s:
            user = s.get(User, user_id)
            try:
                reservation_service.create_reservation(
                    s, user, _payload(seat_id, day, f"conc-key-{user_id}")
                )
                status = "success"
            except Exception:  # BusinessError 409 或 OperationalError 重试耗尽
                status = "conflict"
        return user_id, status

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(attempt, uid) for uid in user_ids]
        # 轻微错开提交以加剧竞争
        for f in futures:
            _time.sleep(0.001)
        for fut in as_completed(futures):
            uid, status = fut.result()
            with lock:
                results[uid] = status

    successes = [uid for uid, s in results.items() if s == "success"]
    conflicts = [uid for uid, s in results.items() if s == "conflict"]

    # 核心断言：恰好一条成功
    assert len(successes) == 1, f"期望恰好 1 条成功，实际 {len(successes)} 条：{successes}"
    # 其余全部被拒
    assert len(conflicts) == len(user_ids) - 1

    # 数据层：该座位该日只有 1 条有效预约，槽位恰好 4 条（14:00-16:00，每 30 分钟）
    active = session.query(Reservation).filter(
        Reservation.seat_id == seat_id,
        Reservation.reserve_date == day,
        Reservation.status.in_([ReservationStatus.PENDING.value, ReservationStatus.IN_USE.value]),
    ).all()
    assert len(active) == 1
    slots = session.query(ReservationSlot).filter(
        ReservationSlot.seat_id == seat_id
    ).all()
    assert len(slots) == 4


def test_concurrent_same_user_same_slot_idempotent(concurrent_db) -> None:
    """VS-02 强化：同一用户并发提交相同幂等键，返回同一预约单（不产生多笔）。"""
    session, factory = concurrent_db
    seat_id, user_ids = _setup_seat_and_users(session)
    day = datetime(2026, 11, 2, 10, 0).date() + timedelta(days=1)
    user_id = user_ids[0]

    reservation_ids: set[int] = set()
    lock = threading.Lock()

    def attempt() -> int | None:
        with factory() as s:
            user = s.get(User, user_id)
            try:
                record = reservation_service.create_reservation(
                    s, user, _payload(seat_id, day, "same-key-concurrent")
                )
                return record.id
            except Exception:
                return None

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(attempt) for _ in range(5)]
        for fut in as_completed(futures):
            rid = fut.result()
            if rid is not None:
                with lock:
                    reservation_ids.add(rid)

    # 同一幂等键只产生一条预约单
    assert len(reservation_ids) == 1
