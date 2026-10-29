from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ComplaintStatus


class Complaint(Base):
    """投诉（DR-007）。"""

    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaint_user_status", "user_id", "status"),
        CheckConstraint(
            "target_type IN ('座位', '自习室', '预约单', '用户')",
            name="ck_complaint_target_type",
        ),
        CheckConstraint(
            "status IN ('待处理', '处理中', '已处理', '已驳回', '已关闭')",
            name="ck_complaint_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, comment="提交人"
    )
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(
        String(20), default=ComplaintStatus.PENDING.value, index=True
    )
    handler_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    handle_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
