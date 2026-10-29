from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ViolationType


class ViolationRecord(Base):
    """违约记录（DR-005）。

    自动违约与预约单一对一；手动违约允许一对多。
    自动违约的幂等由「预约单 + 违约类型」在持久层去重（ST-034 / BR-021）：
    数据库唯一约束 + 服务层先查后写，重复执行不会生成第二条记录。
    """

    __tablename__ = "violation_records"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id", "type", name="uq_violation_reservation_type"
        ),
        Index("ix_violation_user_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(20), default=ViolationType.AUTO.value)
    reason: Mapped[str] = mapped_column(String(255))
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, comment="手动登记的操作人"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
