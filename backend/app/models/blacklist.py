from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import BlacklistMode


class BlacklistEntry(Base):
    """黑名单记录（DR-008）。

    一个用户可有多条历史记录；任一未解除且未到期的记录使账户受限。
    手动加入的限制到期后不得由系统自动解除（BR-010）。
    """

    __tablename__ = "blacklist_entries"
    __table_args__ = (Index("ix_blacklist_user_expire", "user_id", "expire_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(20), default=BlacklistMode.AUTO.value)
    start_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
