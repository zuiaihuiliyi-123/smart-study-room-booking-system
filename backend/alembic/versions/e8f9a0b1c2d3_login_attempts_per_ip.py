"""login attempts keyed by student_no + ip, with updated_at index

Revision ID: e8f9a0b1c2d3
Revises: b7c8d9e0f1a2
Create Date: 2026-11-25

Q4-02(A)：登录失败锁定从「学号」改为「学号 + 客户端 IP」，
防止他人从其他地址用错误口令锁定受害者账号。

沿用表格重建方式修改主键，保留全部历史计数（旧记录 IP 记为 "unknown"，
会在保留期到期后由清理任务删除）。同时新增 updated_at 索引，供
Q4-02(E) 的定期清理扫描。
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e8f9a0b1c2d3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECK_SQL = "failed_count >= 0"
_CHECK_NAME = "ck_login_attempt_failed_count"


def _create_attempts_table(table_name: str, with_ip: bool) -> None:
    """建临时表；先不带 CHECK，避免 MySQL 同 schema 约束名冲突。"""
    columns = [
        sa.Column("student_no", sa.String(length=32), nullable=False),
    ]
    if with_ip:
        columns.append(
            sa.Column(
                "ip",
                sa.String(length=45),
                nullable=False,
                comment="发起登录的客户端 IP",
            )
        )
    columns.extend(
        [
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
        ]
    )
    primary_key = ["student_no", "ip"] if with_ip else ["student_no"]
    op.create_table(
        table_name,
        *columns,
        sa.PrimaryKeyConstraint(*primary_key),
    )


def _add_check(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.create_check_constraint(_CHECK_NAME, _CHECK_SQL)


def upgrade() -> None:
    _create_attempts_table("login_attempts_new", with_ip=True)
    op.execute(
        sa.text(
            """
            INSERT INTO login_attempts_new
                (student_no, ip, failed_count, first_failed_at, locked_until, updated_at)
            SELECT student_no, 'unknown', failed_count, first_failed_at,
                   locked_until, updated_at
            FROM login_attempts
            """
        )
    )
    op.drop_table("login_attempts")
    op.rename_table("login_attempts_new", "login_attempts")
    _add_check("login_attempts")
    op.create_index(
        "ix_login_attempts_updated_at",
        "login_attempts",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    _create_attempts_table("login_attempts_old", with_ip=False)
    # 同一学号可能有多条（不同 IP）：降级时只保留最近更新的一条。
    # 用相关子查询而非窗口函数，兼容 MySQL 5.7 与 SQLite。
    op.execute(
        sa.text(
            """
            INSERT INTO login_attempts_old
                (student_no, failed_count, first_failed_at, locked_until, updated_at)
            SELECT la.student_no, la.failed_count, la.first_failed_at,
                   la.locked_until, la.updated_at
            FROM login_attempts la
            WHERE la.ip = (
                SELECT la2.ip
                FROM login_attempts la2
                WHERE la2.student_no = la.student_no
                ORDER BY la2.updated_at DESC, la2.ip
                LIMIT 1
            )
            """
        )
    )
    op.drop_table("login_attempts")
    op.rename_table("login_attempts_old", "login_attempts")
    _add_check("login_attempts")
