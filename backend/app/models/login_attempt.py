from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils import time_utils


class LoginAttempt(Base):
    """登录失败计数与临时锁定（B5）。

    以「学号 + 客户端 IP」为主键、**不关联 users**：不存在的学号也会一样计数与锁定，
    避免攻击者通过“该账号是否被锁定”判断账号是否存在。
    按 IP 隔离可防止他从其他地址用错误口令把受害者账号锁死（Q4-02）。
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        CheckConstraint("failed_count >= 0", name="ck_login_attempt_failed_count"),
        # 定时清理按 updated_at 扫描（Q4-02）
        Index("ix_login_attempts_updated_at", "updated_at"),
    )

    student_no: Mapped[str] = mapped_column(String(32), primary_key=True)
    #: 发起登录的客户端 IP（IPv6 最长 45 字符）；取不到时为 "unknown"。
    ip: Mapped[str] = mapped_column(
        String(45), primary_key=True, comment="发起登录的客户端 IP"
    )
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_failed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=time_utils.now, nullable=False
    )
