"""认证规则单元测试（不经过 HTTP，只验证函数级行为）。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.login_attempt import LoginAttempt
from app.services import auth_service
from app.services.auth_service import (
    _lock_remaining_minutes,
    _normalize_ip,
    _registration_whitelist,
)


def test_normalize_ip_handles_blank_short_and_long_values() -> None:
    assert _normalize_ip(None) == "unknown"
    assert _normalize_ip("   ") == "unknown"
    assert _normalize_ip("2001:db8::1") == "2001:db8::1"
    # 列宽 45：超长输入截断，且不影响其他 IP 的取值
    assert _normalize_ip("x" * 60) == "x" * 45


@pytest.mark.parametrize(
    ("delta_seconds", "expected"),
    [
        (-30, 1),  # 已过期仍至少提示 1 分钟，避免出现“请 0 分钟后重试”
        (0.5, 1),
        (59, 1),
        (60, 1),
        (61, 2),
        (120, 2),
    ],
)
def test_lock_remaining_minutes_rounds_up(delta_seconds: float, expected: int) -> None:
    now = datetime(2026, 11, 26, 10, 0)
    locked_until = now + timedelta(seconds=delta_seconds)
    assert _lock_remaining_minutes(locked_until, now) == expected


def test_registration_whitelist_accepts_mixed_separators(monkeypatch) -> None:
    monkeypatch.setattr(settings, "registration_whitelist", "")
    assert _registration_whitelist() == set()

    monkeypatch.setattr(settings, "registration_whitelist", " S1 , S2;S3\nS4,, S1 ")
    assert _registration_whitelist() == {"S1", "S2", "S3", "S4"}


def test_login_failure_outside_window_restarts_counter(
    db, freeze_now, make_login_attempt
) -> None:
    now = freeze_now
    attempt = make_login_attempt(
        "S90001",
        failed_count=4,
        first_failed_at=now - timedelta(minutes=settings.login_failure_window_minutes + 1),
    )

    locked = auth_service._register_login_failure(
        db, "S90001", "unknown", attempt, None, now
    )

    assert locked is None
    db.commit()
    db.refresh(attempt)
    assert attempt.failed_count == 1
    assert attempt.first_failed_at == now


def test_login_failure_reaching_threshold_locks_and_writes_audit(
    db, freeze_now, make_login_attempt
) -> None:
    now = freeze_now
    attempt = make_login_attempt(
        "S90002",
        failed_count=settings.login_max_failures - 1,
        first_failed_at=now - timedelta(minutes=1),
    )

    locked = auth_service._register_login_failure(
        db, "S90002", "unknown", attempt, None, now
    )

    expected = now + timedelta(minutes=settings.login_lock_minutes)
    assert locked == expected
    db.commit()
    db.refresh(attempt)
    assert attempt.locked_until == expected
    actions = set(db.scalars(select(AuditLog.action_type)).all())
    assert "LOGIN_LOCKED" in actions


def test_commit_login_failure_retries_after_unique_conflict(
    db, freeze_now, make_login_attempt
) -> None:
    """并发首写同一「学号 + IP」时，唯一键冲突应回滚重读后成功，而不是 500。"""
    now = freeze_now
    make_login_attempt("S90003", ip="unknown", failed_count=1, first_failed_at=now)

    locked = auth_service._commit_login_failure(
        db, "S90003", "unknown", None, None, now
    )

    assert locked is None
    row = db.get(LoginAttempt, ("S90003", "unknown"))
    assert row is not None
    assert row.failed_count == 2
