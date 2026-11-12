"""进程内短 TTL 缓存（单实例部署；多实例可替换为 Redis）。

用于看板 10 秒轮询：同一查询在 TTL 内直接复用响应，降低考试周数据库 QPS。
缓存值必须是只读的 Pydantic/简单对象；调用方不要原地修改。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

from app.core.config import settings

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[K, V]):
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = max(0.0, ttl_seconds)
        self._lock = Lock()
        self._entries: dict[K, _Entry[V]] = {}

    def get(self, key: K) -> V | None:
        if self._ttl <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: K, value: V) -> None:
        if self._ttl <= 0:
            return
        with self._lock:
            self._entries[key] = _Entry(value, time.monotonic() + self._ttl)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


#: 看板概览缓存；key 由 API 层构造（engine id + room_id + 业务日期）。
dashboard_cache: TTLCache[tuple[object, ...], object] = TTLCache(
    settings.dashboard_cache_seconds
)


def clear_dashboard_cache() -> None:
    dashboard_cache.clear()
