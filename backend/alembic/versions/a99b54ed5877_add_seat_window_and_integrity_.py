"""add seat window and integrity constraints

Revision ID: a99b54ed5877
Revises: b12719e4dd71
Create Date: 2026-10-29 16:32:09.233585
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a99b54ed5877'
down_revision: str | None = 'b12719e4dd71'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "blacklist_entries",
        sa.Column(
            "release_reason",
            sa.String(length=255),
            nullable=True,
            comment="手动解除原因",
        ),
    )
    op.add_column(
        "seats",
        sa.Column(
            "near_window",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="是否靠窗",
        ),
    )

    op.create_check_constraint(
        "ck_user_role",
        "users",
        "role IN ('学生用户', '自习室管理员', '教师用户', '系统管理员')",
    )
    op.create_check_constraint(
        "ck_user_account_status",
        "users",
        "account_status IN ('正常', '受限', '停用')",
    )
    op.create_check_constraint(
        "ck_user_violation_count", "users", "violation_count >= 0"
    )
    op.create_check_constraint(
        "ck_room_capacity", "rooms", "capacity >= 0"
    )
    op.create_check_constraint(
        "ck_room_time_order", "rooms", "open_time < close_time"
    )
    op.create_check_constraint(
        "ck_seat_status", "seats", "status IN ('可用', '维修中', '停用')"
    )
    op.create_check_constraint(
        "ck_reservation_time_order",
        "reservations",
        "start_time < end_time",
    )
    op.create_check_constraint(
        "ck_reservation_status",
        "reservations",
        "status IN ('待使用', '使用中', '已完成', '已取消', '已违约')",
    )
    op.create_check_constraint(
        "ck_reservation_idempotency_nonempty",
        "reservations",
        "idempotency_key <> ''",
    )
    op.create_check_constraint(
        "ck_violation_type",
        "violation_records",
        "type IN ('自动违约', '手动违约')",
    )
    op.create_check_constraint(
        "ck_review_score", "reviews", "score BETWEEN 1 AND 5"
    )
    op.create_check_constraint(
        "ck_complaint_target_type",
        "complaints",
        "target_type IN ('座位', '自习室', '预约单', '用户')",
    )
    op.create_check_constraint(
        "ck_complaint_status",
        "complaints",
        "status IN ('待处理', '处理中', '已处理', '已驳回', '已关闭')",
    )
    op.create_check_constraint(
        "ck_blacklist_mode",
        "blacklist_entries",
        "mode IN ('自动', '手动')",
    )
    op.create_check_constraint(
        "ck_blacklist_expire",
        "blacklist_entries",
        "expire_at IS NULL OR expire_at > start_at",
    )
    op.create_check_constraint(
        "ck_blacklist_release_reason",
        "blacklist_entries",
        "released_at IS NULL OR release_reason IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_message_type",
        "station_messages",
        "type IN ('预约通知', '违约通知', '投诉反馈', '系统通知')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_message_type", "station_messages", type_="check")
    op.drop_constraint(
        "ck_blacklist_release_reason", "blacklist_entries", type_="check"
    )
    op.drop_constraint(
        "ck_blacklist_expire", "blacklist_entries", type_="check"
    )
    op.drop_constraint(
        "ck_blacklist_mode", "blacklist_entries", type_="check"
    )
    op.drop_constraint("ck_complaint_status", "complaints", type_="check")
    op.drop_constraint(
        "ck_complaint_target_type", "complaints", type_="check"
    )
    op.drop_constraint("ck_review_score", "reviews", type_="check")
    op.drop_constraint(
        "ck_violation_type", "violation_records", type_="check"
    )
    op.drop_constraint(
        "ck_reservation_idempotency_nonempty",
        "reservations",
        type_="check",
    )
    op.drop_constraint(
        "ck_reservation_status", "reservations", type_="check"
    )
    op.drop_constraint(
        "ck_reservation_time_order", "reservations", type_="check"
    )
    op.drop_constraint("ck_seat_status", "seats", type_="check")
    op.drop_constraint("ck_room_time_order", "rooms", type_="check")
    op.drop_constraint("ck_room_capacity", "rooms", type_="check")
    op.drop_constraint(
        "ck_user_violation_count", "users", type_="check"
    )
    op.drop_constraint(
        "ck_user_account_status", "users", type_="check"
    )
    op.drop_constraint("ck_user_role", "users", type_="check")

    op.drop_column("seats", "near_window")
    op.drop_column("blacklist_entries", "release_reason")
