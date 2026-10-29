import os
import tempfile
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace

_TMP_DIR = Path(tempfile.mkdtemp(prefix="smart_study_room_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "120"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import AccountStatus, Role, SeatStatus  # noqa: E402
from app.models.room import Room  # noqa: E402
from app.models.seat import Seat  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils import time_utils  # noqa: E402

API = "/api/v1"
NOW = datetime(2026, 10, 29, 10, 0)
DAY = date(2026, 10, 30)
PASSWORD = "student123"
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_db():
    with SessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    yield


@pytest.fixture(autouse=True)
def freeze(monkeypatch):
    """所有测试默认冻结在 2026-10-29 10:00，可调用返回值修改。"""
    monkeypatch.setattr(time_utils, "now", lambda: NOW)

    def _set(value: datetime) -> None:
        monkeypatch.setattr(time_utils, "now", lambda: value)

    return _set


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def make_user(
    db,
    student_no: str,
    role: str = Role.STUDENT.value,
    name: str | None = None,
    status: str = AccountStatus.NORMAL.value,
) -> User:
    user = User(
        name=name or student_no,
        student_no=student_no,
        password_hash=PASSWORD_HASH,
        role=role,
        account_status=status,
        contact="13800000000",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def base(db):
    admin = make_user(db, "admin", Role.ADMIN.value, "系统管理员")
    students = [
        make_user(db, f"student{i}", Role.STUDENT.value, f"学生{i}")
        for i in range(1, 7)
    ]
    room = Room(
        name="测试自习室",
        location="测试楼",
        open_time="08:00",
        close_time="22:00",
        capacity=20,
        enabled=True,
    )
    db.add(room)
    db.flush()
    seats = [
        Seat(
            room_id=room.id,
            seat_no=f"A-{index:02d}",
            seat_type="普通",
            has_power=index % 2 == 1,
            status=SeatStatus.AVAILABLE.value,
        )
        for index in range(1, 9)
    ]
    db.add_all(seats)
    db.commit()
    return SimpleNamespace(
        admin=admin,
        students=students,
        student1=students[0],
        student2=students[1],
        room=room,
        seats=seats,
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client):
    cache: dict[str, dict[str, str]] = {}

    def _auth(student_no: str, password: str = PASSWORD) -> dict[str, str]:
        if student_no not in cache:
            response = client.post(
                f"{API}/auth/login",
                json={"student_no": student_no, "password": password},
            )
            assert response.status_code == 200, response.text
            cache[student_no] = {
                "Authorization": f"Bearer {response.json()['access_token']}"
            }
        return cache[student_no]

    return _auth


@pytest.fixture
def student1(auth):
    return auth("student1")


@pytest.fixture
def student2(auth):
    return auth("student2")


@pytest.fixture
def admin(auth):
    return auth("admin")


def booking_payload(
    seat_id: int,
    day: date = DAY,
    start: str = "14:00",
    end: str = "16:00",
    key: str | None = "idem-key-0001",
) -> dict:
    value = key or "idem-key-0001"
    # 幂等键契约要求 8~64 字符；测试用短标签时统一补齐，避免与业务断言混淆
    if len(value) < 8:
        value = value.ljust(8, "0")
    return {
        "seat_id": seat_id,
        "reserve_date": day.isoformat(),
        "start_time": start,
        "end_time": end,
        "idempotency_key": value,
    }


def at(day: date, hhmm: str) -> datetime:
    hour, minute = (int(part) for part in hhmm.split(":"))
    return datetime.combine(day, time(hour, minute))


def fresh(db) -> None:
    """结束测试会话的读事务，确保看到其它会话刚提交的数据（SQLite WAL）。"""
    db.rollback()
    db.expire_all()
