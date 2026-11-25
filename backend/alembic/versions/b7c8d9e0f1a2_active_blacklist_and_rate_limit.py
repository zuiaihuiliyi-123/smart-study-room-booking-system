"""add active blacklist key and rate limit buckets

Revision ID: b7c8d9e0f1a2
Revises: c9d0e1f2a3b4
Create Date: 2026-11-24

- `blacklist_entries.active_user_id`：同一用户最多一条并行有效限制的数据库闸门；
  生效期间等于 user_id，解除/到期后置空（唯一索引允许多个 NULL）。
- `rate_limit_buckets`：按 IP 的固定窗口限流计数，供多 worker 共享。
- 迁移时对历史重复有效限制做去重：保留最早生效的一条，其余标记为已解除，
  不删除任何业务数据。
"""
from collections.abc import Sequence
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEDUPE_REASON = "升级迁移去重：同一用户仅保留一条有效限制（保留最早生效记录）"


def _backfill_active_user_id() -> None:
    """为历史有效限制补 active_user_id，并解除重复记录。"""
    bind = op.get_bind()
    now = datetime.now()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, user_id
            FROM blacklist_entries
            WHERE released_at IS NULL
              AND (mode = '手动' OR expire_at IS NULL OR expire_at > :now)
            ORDER BY user_id, start_at, id
            """
        ),
        {"now": now},
    ).fetchall()

    seen: set[int] = set()
    keep: list[tuple[int, int]] = []
    duplicates: list[int] = []
    for entry_id, user_id in rows:
        if user_id in seen:
            duplicates.append(entry_id)
        else:
            seen.add(user_id)
            keep.append((entry_id, user_id))

    if duplicates:
        bind.execute(
            sa.text(
                """
                UPDATE blacklist_entries
                SET released_at = :now, release_reason = :reason
                WHERE id IN :ids
                """
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"now": now, "reason": DEDUPE_REASON, "ids": duplicates},
        )

    for entry_id, user_id in keep:
        bind.execute(
            sa.text(
                "UPDATE blacklist_entries SET active_user_id = :user_id "
                "WHERE id = :entry_id"
            ),
            {"user_id": user_id, "entry_id": entry_id},
        )


def upgrade() -> None:
    op.add_column(
        "blacklist_entries",
        sa.Column(
            "active_user_id",
            sa.Integer(),
            nullable=True,
            comment="有效限制唯一标记；解除后置空",
        ),
    )
    op.create_foreign_key(
        "fk_blacklist_active_user",
        "blacklist_entries",
        "users",
        ["active_user_id"],
        ["id"],
    )
    _backfill_active_user_id()
    op.create_unique_constraint(
        "uq_blacklist_active_user", "blacklist_entries", ["active_user_id"]
    )

    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope",
            "key",
            "window_start",
            name="uq_rate_limit_scope_key_window",
        ),
    )
    op.create_index(
        "ix_rate_limit_window_start",
        "rate_limit_buckets",
        ["window_start"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_window_start", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
    op.drop_constraint(
        "uq_blacklist_active_user", "blacklist_entries", type_="unique"
    )
    op.drop_constraint(
        "fk_blacklist_active_user", "blacklist_entries", type_="foreignkey"
    )
    op.drop_column("blacklist_entries", "active_user_id")
