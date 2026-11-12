from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils import time_utils


class LoginAttempt(Base):
    """登录失败计数与临时锁定（B5）。

    以学号为主键、**不关联 users**：不存在的学号也会一样计数与锁定，
    避免攻击者通过“该账号是否被锁定”判断账号是否存在。
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        CheckConstraint("failed_count >= 0", name="ck_login_attempt_failed_count"),
    )

    student_no: Mapped[str] = mapped_column(String(32), primary_key=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_failed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=time_utils.now, nullable=False
    )
