from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import SeatStatus


class Seat(Base):
    """座位（DR-003）。

    只在库中保存资源状态；不存储“是否被预约”，
    可预约性由可用性服务根据预约单实时计算（§10.4.2）。
    """

    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("room_id", "seat_no", name="uq_seat_room_no"),
        Index("ix_seat_room_status", "room_id", "status"),
        CheckConstraint(
            "status IN ('可用', '维修中', '停用')", name="ck_seat_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), index=True
    )
    area_id: Mapped[int | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    seat_no: Mapped[str] = mapped_column(String(20), comment="自习室内唯一编号")
    seat_type: Mapped[str] = mapped_column(String(20), default="普通")
    has_power: Mapped[bool] = mapped_column(Boolean, default=False)
    near_window: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否靠窗"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SeatStatus.AVAILABLE.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
