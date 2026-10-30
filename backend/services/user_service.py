from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.user import UserUpdate


def update_my_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """M5 / FR-040：学生仅可修改联系方式，身份字段只读。"""
    raise NotImplementedError("用户资料修改待实现")


def list_users(db: Session, page: int, page_size: int) -> PageResult[User]:
    """M5 / FR-040：管理员查询用户列表与账户状态。"""
    raise NotImplementedError("用户列表查询待实现")
