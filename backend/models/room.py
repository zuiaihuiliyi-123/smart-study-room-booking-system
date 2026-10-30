from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Room(Base):
    """自习室（DR-002）。"""

    __tablename__ = "rooms"

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
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
