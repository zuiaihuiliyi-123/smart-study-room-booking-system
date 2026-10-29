from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.blacklist import BlacklistEntry
from app.models.user import User
from app.schemas.blacklist import BlacklistCreate
from app.schemas.common import PageResult


def list_entries(
    db: Session, page: int, page_size: int
) -> PageResult[BlacklistEntry]:
    """M5 / FR-044：管理员查询黑名单记录（含历史记录）。"""
    raise NotImplementedError("黑名单查询待实现")


def add_entry(
    db: Session, admin: User, payload: BlacklistCreate
) -> BlacklistEntry:
    """M5 / FR-044：管理员手动加入黑名单，必须记录原因与期限。"""
    raise NotImplementedError("手动加入黑名单待实现")


def release_entry(
    db: Session, admin: User, entry_id: int, reason: str
) -> BlacklistEntry:
    """M5 / FR-044：管理员手动解除黑名单，须填写解除原因。"""
    raise NotImplementedError("解除黑名单待实现")


def restrict_if_threshold(db: Session, user_id: int) -> BlacklistEntry | None:
    """BR-009：有效违约次数达到阈值时自动限制 7 天。"""
    raise NotImplementedError("违约阈值自动限制待实现")
