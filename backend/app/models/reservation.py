from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ReservationStatus


class Reservation(Base):
    """预约单（DR-004）。

    占用区间为左闭右开 [start_time, end_time)（BR-020）。
    同一座位同一时段最多一条有效预约（BR-006）——该约束不能只靠
    “先查后写”，需在事务/持久化层配合唯一约束、行锁或串行化实现（NFR-011）。
    """

    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_reservation_idempotency"
        ),
        Index("ix_reservation_seat_date", "seat_id", "reserve_date"),
        Index("ix_reservation_user_date", "user_id", "reserve_date"),
        Index("ix_reservation_status", "status"),
        CheckConstraint("start_time < end_time", name="ck_reservation_time_order"),
        CheckConstraint(
            "status IN ('待使用', '使用中', '已完成', '已取消', '已违约')",
            name="ck_reservation_status",
        ),
        CheckConstraint(
            "idempotency_key <> ''", name="ck_reservation_idempotency_nonempty"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), index=True)
    reserve_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(
        String(20), default=ReservationStatus.PENDING.value
    )
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, comment="取消操作人（管理员强制取消时必填）"
    )
    auto_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="ST-025 系统自动结束标记"
    )
    idempotency_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
