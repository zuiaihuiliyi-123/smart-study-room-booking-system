"""HTTP 层：登录失败计数与临时锁定（B5）。"""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.login_attempt import LoginAttempt
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 6, 10, 0)


def _login(api_client, student_no: str, password: str):
    return api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )


def test_login_locks_after_threshold_and_blocks_correct_password(
    api_client, db, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    make_user(
        student_no="S8301",
        name="锁定测试",
        password_hash=hash_password("student123"),
    )

    for _ in range(4):
        response = _login(api_client, "S8301", "wrongpass")
        assert response.status_code == 401, response.text

    fifth = _login(api_client, "S8301", "wrongpass")
    assert fifth.status_code == 429, fifth.text
    assert fifth.json()["code"] == "ACCOUNT_LOCKED"

    # 锁定期间即使密码正确也拒绝
    blocked = _login(api_client, "S8301", "student123")
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["code"] == "ACCOUNT_LOCKED"

    attempt = db.get(LoginAttempt, "S8301")
    assert attempt is not None
    assert attempt.failed_count == 5
    assert attempt.locked_until == FIXED_NOW + timedelta(minutes=15)

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action_type == "LOGIN_LOCKED")
    )
    assert audit is not None
    assert "S8301" in (audit.reason or "")


def test_successful_login_resets_failure_counter(
    api_client, db, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    make_user(
        student_no="S8302",
        name="重置测试",
        password_hash=hash_password("student123"),
    )

    for _ in range(4):
        assert _login(api_client, "S8302", "wrongpass").status_code == 401

    ok = _login(api_client, "S8302", "student123")
    assert ok.status_code == 200, ok.text
    assert db.get(LoginAttempt, "S8302") is None

    # 成功后重新计数，不应因为之前 4 次失败而立刻锁定
    again = _login(api_client, "S8302", "wrongpass")
    assert again.status_code == 401, again.text


def test_lock_expires_and_allows_login_again(
    api_client, db, make_user, monkeypatch
) -> None:
    current = {"now": FIXED_NOW}
    monkeypatch.setattr(time_utils, "now", lambda: current["now"])
    make_user(
        student_no="S8303",
        name="过期测试",
        password_hash=hash_password("student123"),
    )

    for _ in range(5):
        response = _login(api_client, "S8303", "wrongpass")
    assert response.status_code == 429, response.text

    current["now"] = FIXED_NOW + timedelta(minutes=16)
    ok = _login(api_client, "S8303", "student123")
    assert ok.status_code == 200, ok.text
    assert db.get(LoginAttempt, "S8303") is None


def test_unknown_student_no_is_locked_too(
    api_client, db, monkeypatch
) -> None:
    """不存在的学号同样计数，避免用“是否锁定”枚举账号。"""
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)

    for _ in range(5):
        response = _login(api_client, "NOT-EXIST-999", "wrongpass")
    assert response.status_code == 429, response.text

    attempt = db.get(LoginAttempt, "NOT-EXIST-999")
    assert attempt is not None
    assert attempt.locked_until is not None
