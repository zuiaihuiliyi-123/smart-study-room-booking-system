"""M5 用户管理：本人资料与管理员用户查询（FR-040）。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.user import UserRead, UserUpdate
from app.utils.pagination import to_offset


def update_my_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """M5 / FR-040：学生仅可修改联系方式。

    姓名、学号、角色、账户状态等身份字段在 schema 层已不可提交（BR-018：
    管理员亦不可修改用户身份信息，账户状态统一走 FR-044 黑名单）。
    """
    if "contact" in payload.model_fields_set:
        user.contact = payload.contact
        db.commit()
        db.refresh(user)
    return user


def list_users(db: Session, page: int, page_size: int) -> PageResult[UserRead]:
    """M5 / FR-040：管理员查询用户列表与账户状态（分页，按 id 升序）。"""
    total = db.scalar(select(func.count()).select_from(User)) or 0
    rows = db.scalars(
        select(User).order_by(User.id).offset(to_offset(page, page_size)).limit(page_size)
    )
    return PageResult[UserRead](
        items=[UserRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
