"""add login attempts

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-06 21:00:00.000000

B5：登录失败计数与临时锁定。
以学号为主键、不关联 users，确保不存在的学号也会被同样计数与锁定，
避免通过“是否锁定”判断账号是否存在。
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("student_no", sa.String(length=32), nullable=False),
        sa.Column(
            "failed_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="窗口内连续失败次数",
        ),
        sa.Column("first_failed_at", sa.DateTime(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("student_no"),
        sa.CheckConstraint(
            "failed_count >= 0", name="ck_login_attempt_failed_count"
        ),
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
