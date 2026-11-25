from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RateLimitBucket(Base):
    """固定窗口限流计数（跨 worker 共享，存数据库）。

    每个 (scope, key, window_start) 一行；窗口内命中次数超过阈值即返回 429。
    过期窗口由定时任务清理。
    """

    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "key",
            "window_start",
            name="uq_rate_limit_scope_key_window",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(32))
    key: Mapped[str] = mapped_column(String(64))
    window_start: Mapped[datetime] = mapped_column(DateTime)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
