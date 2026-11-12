"""add user token version

Revision ID: e1f2a3b4c5d6
Revises: b860458bfa51
Create Date: 2026-11-06 20:00:00.000000

B1：用户自助修改密码后，旧的 JWT 必须立即失效。
``users.token_version`` 由登录签发的 ``ver`` 声明携带；改密时递增，
``get_current_user`` 校验不一致即返回 401。
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "b860458bfa51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="令牌版本；改密后递增",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
