"""Pytest 基座：接口客户端 + 独立的 SQLite 内存库与数据工厂。"""

from collections.abc import Callable, Iterator
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  确保全部 ORM 模型注册到 Base.metadata
from app.core.database import Base
from app.main import app
from app.models.enums import AccountStatus, ReservationStatus, Role, SeatStatus
from app.models.reservation import Reservation
from app.models.room import Area, Room
from app.models.seat import Seat
from app.models.user import User


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db() -> Iterator[Session]:
    """每个用例一套独立的内存库（不依赖本机 MySQL）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def make_user(db: Session) -> Callable[..., User]:
    def _make(**kwargs: object) -> User:
        defaults: dict[str, object] = {
            "name": "张三",
            "student_no": "S0001",
            "password_hash": "hash",
            "role": Role.STUDENT.value,
            "account_status": AccountStatus.NORMAL.value,
        }
        defaults.update(kwargs)
        user = User(**defaults)  # type: ignore[arg-type]
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_room(db: Session) -> Callable[..., Room]:
    counter = {"n": 0}

    def _make(**kwargs: object) -> Room:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "name": f"自习室{counter['n']}",
            "location": "图书馆 3 楼",
        }
        defaults.update(kwargs)
        room = Room(**defaults)  # type: ignore[arg-type]
        db.add(room)
        db.commit()
        db.refresh(room)
        return room

    return _make


@pytest.fixture()
def make_area(db: Session) -> Callable[..., Area]:
    def _make(room_id: int, name: str = "A 区") -> Area:
        area = Area(room_id=room_id, name=name)
        db.add(area)
        db.commit()
        db.refresh(area)
        return area

    return _make


@pytest.fixture()
def make_seat(db: Session) -> Callable[..., Seat]:
    counter = {"n": 0}

    def _make(room_id: int, **kwargs: object) -> Seat:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "room_id": room_id,
            "seat_no": f"A-{counter['n']:02d}",
            "status": SeatStatus.AVAILABLE.value,
        }
        defaults.update(kwargs)
        seat = Seat(**defaults)  # type: ignore[arg-type]
        db.add(seat)
        db.commit()
        db.refresh(seat)
        return seat

    return _make


@pytest.fixture()
def make_reservation(db: Session) -> Callable[..., Reservation]:
    counter = {"n": 0}

    def _make(user_id: int, seat_id: int, **kwargs: object) -> Reservation:
        counter["n"] += 1
        defaults: dict[str, object] = {
            "user_id": user_id,
            "seat_id": seat_id,
            "reserve_date": date(2099, 1, 1),
            "start_time": time(14, 0),
            "end_time": time(16, 0),
            "status": ReservationStatus.PENDING.value,
            "idempotency_key": f"key-{counter['n']}",
        }
        defaults.update(kwargs)
        reservation = Reservation(**defaults)  # type: ignore[arg-type]
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation

    return _make
