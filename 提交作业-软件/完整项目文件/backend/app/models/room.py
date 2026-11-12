from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Room(Base):
    """自习室（DR-002）。"""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_room_capacity"),
        CheckConstraint("open_time < close_time", name="ck_room_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    location: Mapped[str] = mapped_column(String(100))
    open_time: Mapped[str] = mapped_column(String(5), default="08:00")
    close_time: Mapped[str] = mapped_column(String(5), default="22:00")
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Area(Base):
    """自习室内的区域（DR-002a）。"""

    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("room_id", "name", name="uq_area_room_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RoomClosure(Base):
    """场地临时关闭记录：只在 [start_at, end_at) 内生效，过期自动失效。

    座位资源状态不再因为关闭而被改写，座位状态只表示「可用 / 维修中 / 停用」。
    """

    __tablename__ = "room_closures"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="ck_closure_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    reason: Mapped[str] = mapped_column(String(255))
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
