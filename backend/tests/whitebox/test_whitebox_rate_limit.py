"""白盒测试：固定窗口限流的窗口切换、超限与并发插入回退分支。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.rate_limit import RateLimitBucket
from app.services import rate_limit_service

NOW = datetime(2026, 11, 24, 10, 0, 30)


def test_window_start_aligns_to_whole_minute() -> None:
    assert rate_limit_service._window_start(NOW, 60) == datetime(2026, 11, 24, 10, 0)
    assert rate_limit_service._window_start(
        datetime(2026, 11, 24, 10, 0, 0), 60
    ) == datetime(2026, 11, 24, 10, 0)


def test_hit_counts_and_blocks_after_limit(db) -> None:
    assert rate_limit_service.hit(db, scope="login", key="1.1.1.1", limit=2, now=NOW) == 1
    assert rate_limit_service.hit(db, scope="login", key="1.1.1.1", limit=2, now=NOW) == 2

    with pytest.raises(BusinessError) as exc:
        rate_limit_service.hit(db, scope="login", key="1.1.1.1", limit=2, now=NOW)

    assert exc.value.code == "RATE_LIMITED"
    assert exc.value.status_code == 429
    # 窗口 10:00:00 ~ 10:01:00，当前 10:00:30 → 剩余 30 秒
    assert exc.value.headers == {"Retry-After": "30"}
    assert exc.value.details["scope"] == "login"


def test_hit_uses_new_window_after_minute_boundary(db) -> None:
    assert rate_limit_service.hit(db, scope="login", key="2.2.2.2", limit=1, now=NOW) == 1
    later = NOW + timedelta(seconds=31)  # 10:01:01，进入下一个窗口
    assert rate_limit_service.hit(db, scope="login", key="2.2.2.2", limit=1, now=later) == 1


def test_hit_cleans_buckets_older_than_one_day(db) -> None:
    db.add(
        RateLimitBucket(
            scope="login",
            key="3.3.3.3",
            window_start=NOW - timedelta(days=2),
            hits=99,
        )
    )
    db.commit()

    rate_limit_service.hit(db, scope="login", key="3.3.3.3", limit=10, now=NOW)

    old = db.scalar(
        select(RateLimitBucket).where(
            RateLimitBucket.key == "3.3.3.3",
            RateLimitBucket.window_start == NOW - timedelta(days=2),
        )
    )
    assert old is None


def test_hit_recovers_when_concurrent_insert_hits_unique_constraint(db, monkeypatch) -> None:
    """强行让第一次 UPDATE 返回 0 行，验证 INSERT 撞唯一约束后的回退自增。"""
    window_start = datetime(2026, 11, 24, 10, 0)
    db.add(
        RateLimitBucket(
            scope="login",
            key="4.4.4.4",
            window_start=window_start,
            hits=2,
        )
    )
    db.commit()

    real_execute = db.execute
    calls = {"n": 0}

    def fake_execute(statement, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:  # 模拟并发窗口内“尚未看到记录”的 UPDATE
            return type("Result", (), {"rowcount": 0})()
        return real_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", fake_execute)

    assert rate_limit_service.hit(db, scope="login", key="4.4.4.4", limit=10, now=NOW) == 3
