"""rebuild reservation slots for 5-minute granularity

Revision ID: f4b2d8c6a1e0
Revises: b860458bfa51
Create Date: 2026-11-07 20:40:00.000000

业务变更：BR-001 预约粒度由 30 分钟调整为 5 分钟。
`reservation_slots` 是占用区间的物化表，存量有效预约仍只有 30 分钟边界上的行，
若不重建，新 5 分钟预约可能落在两个旧行之间而绕过唯一约束。

本迁移只重建「待使用 / 使用中」预约的槽位；终态预约原本已释放，不需要行。
"""
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from alembic import op
import sqlalchemy as sa

revision: str = "f4b2d8c6a1e0"
down_revision: str | None = "b860458bfa51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANULARITY_MINUTES = 5
LEGACY_GRANULARITY_MINUTES = 30
ACTIVE_STATUSES = ("待使用", "使用中")


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_time(value: object) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value)[:8])


def _rebuild_slots(granularity: int) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, seat_id, user_id, reserve_date, start_time, end_time "
            "FROM reservations WHERE status IN (:pending, :in_use)"
        ),
        {"pending": ACTIVE_STATUSES[0], "in_use": ACTIVE_STATUSES[1]},
    ).mappings().all()

    bind.execute(sa.text("DELETE FROM reservation_slots"))
    for row in rows:
        day = _as_date(row["reserve_date"])
        cursor = datetime.combine(day, _as_time(row["start_time"]))
        end_at = datetime.combine(day, _as_time(row["end_time"]))
        slot_rows = []
        while cursor < end_at:
            slot_rows.append(
                {
                    "reservation_id": row["id"],
                    "seat_id": row["seat_id"],
                    "user_id": row["user_id"],
                    "slot_start": cursor,
                }
            )
            cursor += timedelta(minutes=granularity)
        if slot_rows:
            bind.execute(
                sa.text(
                    "INSERT INTO reservation_slots "
                    "(reservation_id, seat_id, user_id, slot_start) "
                    "VALUES (:reservation_id, :seat_id, :user_id, :slot_start)"
                ),
                slot_rows,
            )


def upgrade() -> None:
    _rebuild_slots(GRANULARITY_MINUTES)


def downgrade() -> None:
    _rebuild_slots(LEGACY_GRANULARITY_MINUTES)
