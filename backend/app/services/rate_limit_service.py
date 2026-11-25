"""接口限流（固定窗口，跨进程共享）。

用途：登录 / 注册按「IP + 窗口」限制请求次数，超限返回 429 并带 ``Retry-After``。
计数落在数据库而非进程内存，多 worker 部署下仍按同一口径生效。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.rate_limit import RateLimitBucket
from app.utils import time_utils


def _window_start(now: datetime, window_seconds: int) -> datetime:
    """把时间向下对齐到固定窗口起点（60 秒窗口即整分钟）。"""
    remainder = now.second % window_seconds
    return now.replace(second=now.second - remainder, microsecond=0)


def _cleanup(db: Session, before: datetime) -> None:
    """顺手清理过期窗口，避免表无限增长。"""
    db.execute(delete(RateLimitBucket).where(RateLimitBucket.window_start < before))


def hit(
    db: Session,
    *,
    scope: str,
    key: str,
    limit: int,
    window_seconds: int = 60,
    now: datetime | None = None,
) -> int:
    """记录一次请求并返回当前窗口命中次数；超限抛 429。

    计数自增使用 UPDATE ... SET hits = hits + 1，并发下不会丢计数；
    首次命中用嵌套事务插入，唯一约束冲突时回退为自增。
    """
    current = now or time_utils.now()
    window_start = _window_start(current, window_seconds)

    updated = db.execute(
        update(RateLimitBucket)
        .where(
            RateLimitBucket.scope == scope,
            RateLimitBucket.key == key,
            RateLimitBucket.window_start == window_start,
        )
        .values(hits=RateLimitBucket.hits + 1)
    )
    if not updated.rowcount:
        try:
            # 嵌套事务：并发插入撞唯一约束时只回滚这一小段，不污染外层事务
            with db.begin_nested():
                db.add(
                    RateLimitBucket(
                        scope=scope,
                        key=key,
                        window_start=window_start,
                        hits=1,
                    )
                )
        except IntegrityError:
            db.execute(
                update(RateLimitBucket)
                .where(
                    RateLimitBucket.scope == scope,
                    RateLimitBucket.key == key,
                    RateLimitBucket.window_start == window_start,
                )
                .values(hits=RateLimitBucket.hits + 1)
            )

    _cleanup(db, window_start - timedelta(days=1))
    db.commit()

    hits = (
        db.scalar(
            select(RateLimitBucket.hits).where(
                RateLimitBucket.scope == scope,
                RateLimitBucket.key == key,
                RateLimitBucket.window_start == window_start,
            )
        )
        or 0
    )
    if hits > limit:
        retry_after = max(
            1,
            int(
                (
                    window_start + timedelta(seconds=window_seconds) - current
                ).total_seconds()
            ),
        )
        raise BusinessError(
            "请求过于频繁，请稍后重试",
            code="RATE_LIMITED",
            status_code=429,
            details={"scope": scope, "limit": limit, "window_seconds": window_seconds},
            headers={"Retry-After": str(retry_after)},
        )
    return hits
