from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils import time_utils


class TaskExecution(Base):
    """调度任务执行记录（运维可观测性）。

    每次定时任务运行写一条记录；失败重试只更新同一行的 attempts/status/error，
    避免刷屏。该表只追加、不参与业务规则。
    """

    __tablename__ = "task_executions"
    __table_args__ = (
        Index("ix_task_execution_name_started", "task_name", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=time_utils.now)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=time_utils.now
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=time_utils.now)