"""cancel teacher role

Revision ID: d4e7b1c9f2a3
Revises: c3f1a2b4d5e6
Create Date: 2026-11-05 16:50:00.000000

需求规格说明书 V2.1（2026-11-05）：按业务方决策取消教师用户（R-03）角色。
本迁移做两件事：

1. **数据迁移**：把存量 ``role = '教师用户'`` 的账号统一映射为 ``'学生用户'``，
   使其在新约束下合法（该映射不改变账号的预约与查询能力，仅收敛角色取值）；
2. **约束迁移**：重建 ``ck_user_role``，取值收敛为
   ``学生用户 / 自习室管理员 / 系统管理员``。

注意：
- 数据映射是**单向**的；``downgrade`` 只恢复旧约束，不还原被映射账号的原角色
  （原值已在 upgrade 中丢失，无法判定哪些账号原本是教师）。
- SQLite 不支持通过 ALTER 增删 CHECK 约束；测试与开发环境由
  ``Base.metadata.create_all`` 直接按新模型建表，故 SQLite 下只做数据映射。
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e7b1c9f2a3'
down_revision: str | None = 'c3f1a2b4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_ROLE_CHECK = "role IN ('学生用户', '自习室管理员', '教师用户', '系统管理员')"
_NEW_ROLE_CHECK = "role IN ('学生用户', '自习室管理员', '系统管理员')"


def upgrade() -> None:
    bind = op.get_bind()

    # 1) 存量「教师用户」→「学生用户」（先迁移数据，再收紧约束）
    bind.execute(
        sa.text("UPDATE users SET role = '学生用户' WHERE role = '教师用户'")
    )

    # 2) 重建角色约束
    if bind.dialect.name == "sqlite":
        # SQLite 无法 ALTER 已有 CHECK 约束；其表结构由 Base.metadata 直接创建，
        # 已按新模型生成，因此这里跳过约束重建（仅完成数据映射）。
        return
    op.drop_constraint("ck_user_role", "users", type_="check")
    op.create_check_constraint("ck_user_role", "users", _NEW_ROLE_CHECK)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.drop_constraint("ck_user_role", "users", type_="check")
    op.create_check_constraint("ck_user_role", "users", _OLD_ROLE_CHECK)
    # 说明：不再把「学生用户」恢复为「教师用户」——原角色值已不可判定。
