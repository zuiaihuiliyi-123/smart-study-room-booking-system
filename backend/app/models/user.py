from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AccountStatus, Role


class User(Base):
    """用户（DR-001）：学生、教师、自习室管理员、系统管理员。"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('学生用户', '自习室管理员', '教师用户', '系统管理员')",
            name="ck_user_role",
        ),
        CheckConstraint(
            "account_status IN ('正常', '受限', '停用')",
            name="ck_user_account_status",
        ),
        CheckConstraint("violation_count >= 0", name="ck_user_violation_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), comment="姓名")
    student_no: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, comment="学号/工号"
    )
    password_hash: Mapped[str] = mapped_column(String(255), comment="密码哈希")
    role: Mapped[str] = mapped_column(
        String(20), default=Role.STUDENT.value, index=True
    )
    account_status: Mapped[str] = mapped_column(
        String(20), default=AccountStatus.NORMAL.value, index=True
    )
    violation_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="有效违约次数，须与违约记录一致"
    )
    contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
