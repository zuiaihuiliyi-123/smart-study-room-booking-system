"""add reservation slots and automatic completion fields

Revision ID: c3f1a2b4d5e6
Revises: 6856f6769461
Create Date: 2026-10-31 13:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c3f1a2b4d5e6"
down_revision: str | None = "6856f6769461"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 预约单：管理员强制取消的操作人（ST-022）与自动结束标记（ST-025）
    op.add_column(
        "reservations",
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_reservation_cancelled_by",
        "reservations",
        "users",
        ["cancelled_by_id"],
        ["id"],
    )
    op.add_column(
        "reservations",
        sa.Column(
            "auto_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # 占用槽位表：以数据库唯一约束保证 BR-005 / BR-006 的并发正确性
    op.create_table(
        "reservation_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("seat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slot_start", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["seat_id"], ["seats.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seat_id", "slot_start", name="uq_slot_seat_start"),
        sa.UniqueConstraint("user_id", "slot_start", name="uq_slot_user_start"),
    )
    op.create_index(
        op.f("ix_reservation_slots_reservation_id"),
        "reservation_slots",
        ["reservation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservation_slots_seat_id"),
        "reservation_slots",
        ["seat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservation_slots_user_id"),
        "reservation_slots",
        ["user_id"],
        unique=False,
    )

    # 自动/手动违约按「预约单 + 类型」去重（ST-034）
    op.create_unique_constraint(
        "uq_violation_reservation_type",
        "violation_records",
        ["reservation_id", "type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_violation_reservation_type",
        "violation_records",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_reservation_slots_user_id"), table_name="reservation_slots"
    )
    op.drop_index(
        op.f("ix_reservation_slots_seat_id"), table_name="reservation_slots"
    )
    op.drop_index(
        op.f("ix_reservation_slots_reservation_id"), table_name="reservation_slots"
    )
    op.drop_table("reservation_slots")
    op.drop_column("reservations", "auto_completed")
    op.drop_constraint(
        "fk_reservation_cancelled_by", "reservations", type_="foreignkey"
    )
    op.drop_column("reservations", "cancelled_by_id")
