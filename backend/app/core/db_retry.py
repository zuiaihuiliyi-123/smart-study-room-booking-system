"""数据库写入重试：MySQL 死锁 / 锁等待超时，以及 SQLite 测试库的 locked。

Service 命令方法在事务外层调用本工具。每次失败先 rollback，再按退避重试；
业务异常（BusinessError）不会被重试。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: MySQL: 1213 deadlock, 1205 lock wait timeout
_MYSQL_RETRYABLE_CODES = {1213, 1205}


def _mysql_error_code(exc: OperationalError) -> int | None:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    if not args:
        return None
    try:
        return int(args[0])
    except (TypeError, ValueError):
        return None


def is_retryable_db_error(exc: OperationalError) -> bool:
    """只重试可恢复的并发错误，不重试连接配置或 SQL 语法错误。"""
    code = _mysql_error_code(exc)
    if code in _MYSQL_RETRYABLE_CODES:
        return True
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message


def run_with_db_retry(
    db: Session,
    operation: Callable[[], T],
    *,
    attempts: int | None = None,
    base_delay_ms: int | None = None,
) -> T:
    """执行一次数据库命令；死锁 / 锁等待时 rollback 后重试。"""
    max_attempts = max(1, attempts or settings.db_retry_attempts)
    delay = max(0, base_delay_ms if base_delay_ms is not None else settings.db_retry_base_delay_ms)

    last_error: OperationalError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except OperationalError as exc:
            last_error = exc
            db.rollback()
            if not is_retryable_db_error(exc) or attempt >= max_attempts:
                raise
            wait_seconds = (delay * attempt) / 1000
            logger.warning(
                "数据库并发冲突，准备第 %s/%s 次重试（%.3fs）：%s",
                attempt,
                max_attempts,
                wait_seconds,
                exc,
            )
            time.sleep(wait_seconds)

    # 理论上不可达；保留显式异常便于类型检查与排障
    assert last_error is not None
    raise last_error
