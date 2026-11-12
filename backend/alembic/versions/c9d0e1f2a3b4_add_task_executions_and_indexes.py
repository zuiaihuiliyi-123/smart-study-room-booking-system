"""add task execution records and dashboard query indexes

Revision ID: c9d0e1f2a3b4
Revises: f4b2d8c6a1e0
Create Date: 2026-11-12

- `reservations.created_at`：看板「今日预约 / 趋势」的日期范围查询；
- `reservation_slots.slot_start`：可预约性与冲突查询的时间范围过滤；
- `task_executions`：APScheduler 每次运行的执行记录（成功/失败、耗时、重试次数）。
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "f4b2d8c6a1e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_reservation_created_at", "reservations", ["created_at"], unique=False
    )
    op.create_index(
        "ix_reservation_slots_slot_start",
        "reservation_slots",
        ["slot_start"],
        unique=False,
    )
    op.create_table(
        "task_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_execution_name_started",
        "task_executions",
        ["task_name", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_execution_name_started", table_name="task_executions")
    op.drop_table("task_executions")
    op.drop_index(
        "ix_reservation_slots_slot_start", table_name="reservation_slots"
    )
    op.drop_index("ix_reservation_created_at", table_name="reservations")
