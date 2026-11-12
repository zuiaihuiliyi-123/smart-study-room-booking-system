"""调度任务运行包装：失败重试、执行记录与日志。"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.task_execution import TaskExecution
from app.utils import time_utils

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _record(
    *,
    task_name: str,
    status: str,
    attempts: int,
    started_at,
    finished_at,
    duration_ms: int,
    message: str | None,
    error: str | None,
) -> None:
    try:
        with SessionLocal() as db:
            db.add(
                TaskExecution(
                    task_name=task_name,
                    status=status,
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    message=message,
                    error=error,
                )
            )
            db.commit()
    except Exception:  # pragma: no cover - 记录失败不能影响业务任务
        logger.exception("调度任务执行记录写入失败：task=%s", task_name)


def run_scheduled_task(
    task_name: str,
    operation: Callable[[], T],
    *,
    retries: int | None = None,
) -> T:
    """执行定时任务；失败按配置重试，并把最终执行结果写入 task_executions。"""
    max_attempts = max(1, retries or settings.scheduler_task_retries)
    started_at = time_utils.now()
    started_monotonic = time.monotonic()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = operation()
            finished_at = time_utils.now()
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            _record(
                task_name=task_name,
                status="成功",
                attempts=attempt,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                message=None if result is None else str(result)[:255],
                error=None,
            )
            return result
        except Exception as exc:  # noqa: BLE001 - 定时任务需要记录所有失败
            last_error = exc
            logger.exception(
                "调度任务失败：task=%s attempt=%s/%s", task_name, attempt, max_attempts
            )
            if attempt < max_attempts:
                time.sleep(settings.scheduler_retry_delay_seconds)

    finished_at = time_utils.now()
    duration_ms = int((time.monotonic() - started_monotonic) * 1000)
    _record(
        task_name=task_name,
        status="失败",
        attempts=max_attempts,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        message=None,
        error=(
            None
            if last_error is None
            else f"{type(last_error).__name__}: {last_error}"[:2000]
        ),
    )
    assert last_error is not None
    raise last_error
