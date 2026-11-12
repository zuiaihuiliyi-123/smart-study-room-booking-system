"""protect room history

Revision ID: 6856f6769461
Revises: a99b54ed5877
Create Date: 2026-10-29 16:33:59.652551
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '6856f6769461'
down_revision: str | None = 'a99b54ed5877'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 房间不提供物理删除；禁止删除房间时级联删除分区和座位，避免历史记录失去关联对象。
    op.drop_constraint("areas_ibfk_1", "areas", type_="foreignkey")
    op.create_foreign_key(
        "fk_area_room",
        "areas",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint("seats_ibfk_2", "seats", type_="foreignkey")
    op.create_foreign_key(
        "fk_seat_room",
        "seats",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_seat_room", "seats", type_="foreignkey")
    op.create_foreign_key(
        "seats_ibfk_2",
        "seats",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_area_room", "areas", type_="foreignkey")
    op.create_foreign_key(
        "areas_ibfk_1",
        "areas",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="CASCADE",
    )
