"""后端数据层加固回归：冲突映射、死锁重试、缓存与统一时间口径。"""

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.cache import dashboard_cache
from app.core.exceptions import BusinessError, register_exception_handlers
from app.core.security import hash_password
from app.core.transactions import transaction
from app.models.task_execution import TaskExecution
from app.schemas.dashboard import StatOverview
from app.services import dashboard_service
from app.tasks import runtime
from app.utils import time_utils


def test_integrity_error_is_mapped_to_409() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise IntegrityError("INSERT ...", {}, Exception("duplicate"))

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 409
    assert response.json()["code"] == "DATA_CONFLICT"
    assert "duplicate" not in response.text


class _FakeSession:
    def __init__(self) -> None:
        self.rollbacks = 0

    def rollback(self) -> None:
        self.rollbacks += 1


def test_db_retry_retries_deadlock_and_rolls_back(monkeypatch) -> None:
    from app.core.db_retry import run_with_db_retry

    monkeypatch.setattr("app.core.db_retry.time.sleep", lambda _: None)
    db = _FakeSession()
    calls = {"n": 0}

    def operation() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("UPDATE ...", {}, Exception(1213))
        return "ok"

    assert run_with_db_retry(db, operation, attempts=3) == "ok"
    assert calls["n"] == 3
    assert db.rollbacks == 2


def test_db_retry_does_not_retry_sql_syntax_error(monkeypatch) -> None:
    from app.core.db_retry import run_with_db_retry

    monkeypatch.setattr("app.core.db_retry.time.sleep", lambda _: None)
    db = _FakeSession()
    calls = {"n": 0}

    def operation() -> None:
        calls["n"] += 1
        raise OperationalError("SELECT ...", {}, Exception(1064))

    with pytest.raises(OperationalError):
        run_with_db_retry(db, operation, attempts=3)
    assert calls["n"] == 1
    assert db.rollbacks == 1


def test_dashboard_overview_uses_short_cache(
    api_client, make_user, monkeypatch
) -> None:
    dashboard_cache.clear()
    make_user(
        student_no="A9001",
        name="看板缓存管理员",
        role="自习室管理员",
        password_hash=hash_password("admin123"),
    )
    login = api_client.post(
        "/api/v1/auth/login",
        json={"student_no": "A9001", "password": "admin123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    calls = {"n": 0}

    def fake_overview(db, room_id=None):
        calls["n"] += 1
        return StatOverview(
            seat_total=10,
            in_use=2,
            today_reservations=3,
            today_violations=0,
            restricted_accounts=0,
        )

    monkeypatch.setattr(dashboard_service, "get_overview", fake_overview)
    first = api_client.get("/api/v1/dashboard/overview", headers=headers)
    second = api_client.get("/api/v1/dashboard/overview", headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert calls["n"] == 1
    dashboard_cache.clear()


def test_time_utils_uses_naive_shanghai_time() -> None:
    current = time_utils.now()
    assert isinstance(current, datetime)
    assert current.tzinfo is None


def test_transaction_helper_rolls_back_on_business_error(db, make_user) -> None:
    user = make_user(student_no="S9101", name="事务测试")
    with pytest.raises(BusinessError):
        with transaction(db):
            user.name = "不应提交"
            raise BusinessError("失败", code="TEST_FAILURE")

    db.refresh(user)
    assert user.name == "事务测试"


def test_scheduled_task_retries_and_records_execution(db, monkeypatch) -> None:
    testing_session = sessionmaker(
        bind=db.get_bind(), autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr(runtime, "SessionLocal", testing_session)
    monkeypatch.setattr(runtime.settings, "scheduler_retry_delay_seconds", 0)

    calls = {"n": 0}

    def operation() -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary")
        return 7

    result = runtime.run_scheduled_task("__test_retry__", operation, retries=2)

    record = db.scalar(
        select(TaskExecution).where(TaskExecution.task_name == "__test_retry__")
    )
    assert result == 7
    assert calls["n"] == 2
    assert record is not None
    assert record.status == "成功"
    assert record.attempts == 2
    assert record.message == "7"


