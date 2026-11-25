"""HTTP 层：登录失败计数与临时锁定（B5）。"""

from datetime import datetime, timedelta

from sqlalchemy import select
from starlette.testclient import TestClient

from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.login_attempt import LoginAttempt
from app.services import auth_service
from app.utils import time_utils

FIXED_NOW = datetime(2026, 11, 6, 10, 0)


def _login(api_client, student_no: str, password: str):
    return api_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )


def _attempts(db, student_no: str) -> list[LoginAttempt]:
    return list(
        db.scalars(
            select(LoginAttempt).where(LoginAttempt.student_no == student_no)
        )
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

    attempts = _attempts(db, "S8301")
    assert len(attempts) == 1
    attempt = attempts[0]
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
    assert _attempts(db, "S8302") == []

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
    assert _attempts(db, "S8303") == []


def test_unknown_student_no_is_locked_too(
    api_client, db, monkeypatch
) -> None:
    """不存在的学号同样计数，避免用“是否锁定”枚举账号。"""
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)

    for _ in range(5):
        response = _login(api_client, "NOT-EXIST-999", "wrongpass")
    assert response.status_code == 429, response.text

    attempts = _attempts(db, "NOT-EXIST-999")
    assert len(attempts) == 1
    assert attempts[0].locked_until is not None


def test_lockout_is_isolated_by_client_ip(
    api_client, db, make_user, monkeypatch
) -> None:
    """Q4-02(A)：他人从其他 IP 连续失败，不能锁死受害者账号。"""
    monkeypatch.setattr(time_utils, "now", lambda: FIXED_NOW)
    make_user(
        student_no="S8304",
        name="IP 隔离测试",
        password_hash=hash_password("student123"),
    )

    # 攻击者从默认测试 IP 连续失败 5 次，该 IP 被锁定
    for _ in range(5):
        _login(api_client, "S8304", "wrongpass")
    blocked = _login(api_client, "S8304", "student123")
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["code"] == "ACCOUNT_LOCKED"

    # 受害者从另一个 IP 使用正确密码仍可登录
    victim = TestClient(app, client=("203.0.113.9", 51000))
    ok = victim.post(
        "/api/v1/auth/login",
        json={"student_no": "S8304", "password": "student123"},
    )
    assert ok.status_code == 200, ok.text
    # 成功登录清空该学号在所有来源的失败计数
    assert _attempts(db, "S8304") == []


def test_cleanup_removes_only_expired_login_attempts(db) -> None:
    """Q4-02(E)：超过保留期的计数被清理，未过期记录保留。"""
    db.add_all(
        [
            LoginAttempt(
                student_no="OLD-1",
                ip="198.51.100.1",
                failed_count=2,
                updated_at=FIXED_NOW - timedelta(days=31),
            ),
            LoginAttempt(
                student_no="RECENT-1",
                ip="198.51.100.1",
                failed_count=1,
                updated_at=FIXED_NOW - timedelta(days=1),
            ),
        ]
    )
    db.commit()

    removed = auth_service.cleanup_login_attempts(db, now=FIXED_NOW)

    assert removed == 1
    remaining = db.scalars(select(LoginAttempt.student_no)).all()
    assert remaining == ["RECENT-1"]
