from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils import time_utils
from app.models.enums import BlacklistMode


class BlacklistEntry(Base):
    """黑名单记录（DR-008）。

    一个用户可有多条历史记录；任一未解除且未到期的记录使账户受限。
    手动加入的限制到期后不得由系统自动解除（BR-010）。
    """

    __tablename__ = "blacklist_entries"
    __table_args__ = (
        Index("ix_blacklist_user_expire", "user_id", "expire_at"),
        UniqueConstraint("active_user_id", name="uq_blacklist_active_user"),
        CheckConstraint("mode IN ('自动', '手动')", name="ck_blacklist_mode"),
        CheckConstraint(
            "expire_at IS NULL OR expire_at > start_at",
            name="ck_blacklist_expire",
        ),
        CheckConstraint(
            "released_at IS NULL OR release_reason IS NOT NULL",
            name="ck_blacklist_release_reason",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(20), default=BlacklistMode.AUTO.value)
    start_at: Mapped[datetime] = mapped_column(DateTime, default=time_utils.now)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    release_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="手动解除原因"
    )
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # 有效限制的并发闸门：生效期间等于 user_id，解除后置空。
    # 唯一索引（MySQL/SQLite 允许多个 NULL）保证同一用户最多一条并行有效限制。
    active_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="有效限制唯一标记；解除后置空",
    )
