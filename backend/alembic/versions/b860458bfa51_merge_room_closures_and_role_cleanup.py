"""merge room closures and role cleanup

Revision ID: b860458bfa51
Revises: a7d3e5f8b1c2, d4e7b1c9f2a3
Create Date: 2026-11-06 18:49:48.698805
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b860458bfa51'
down_revision: str | None = ('a7d3e5f8b1c2', 'd4e7b1c9f2a3')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
