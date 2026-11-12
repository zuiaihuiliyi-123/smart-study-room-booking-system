"""add room closures

Revision ID: a7d3e5f8b1c2
Revises: c3f1a2b4d5e6
Create Date: 2026-11-05 17:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a7d3e5f8b1c2"
down_revision: str | None = "c3f1a2b4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """场地临时关闭：按时间窗生效，过期自动失效。"""
    op.create_table(
        "room_closures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=True),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("start_at < end_at", name="ck_closure_time_order"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_room_closures_room_id", "room_closures", ["room_id"])
    op.create_index("ix_room_closures_area_id", "room_closures", ["area_id"])
    op.create_index("ix_room_closures_start_at", "room_closures", ["start_at"])
    op.create_index("ix_room_closures_end_at", "room_closures", ["end_at"])


def downgrade() -> None:
    op.drop_index("ix_room_closures_end_at", table_name="room_closures")
    op.drop_index("ix_room_closures_start_at", table_name="room_closures")
    op.drop_index("ix_room_closures_area_id", table_name="room_closures")
    op.drop_index("ix_room_closures_room_id", table_name="room_closures")
    op.drop_table("room_closures")
