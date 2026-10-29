from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ViolationType


class ViolationRecord(Base):
    """违约记录（DR-005）。

    自动违约与预约单一对一；手动违约允许一对多。
    自动违约的幂等由“预约单 + 违约类型”在服务层去重（FR-022）。
    """

    __tablename__ = "violation_records"
    __table_args__ = (
        Index("ix_violation_user_time", "user_id", "created_at"),
        Index("ix_violation_reservation_type", "reservation_id", "type"),
        CheckConstraint(
            "type IN ('自动违约', '手动违约')", name="ck_violation_type"
        ),
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
