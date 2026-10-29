from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.complaint import ComplaintCreate, ComplaintHandle


def create_complaint(
    db: Session, user_id: int, payload: ComplaintCreate
) -> Complaint:
    """M5 / FR-042：提交投诉，初始状态“待处理”。"""
    raise NotImplementedError("投诉提交待实现")


def list_my_complaints(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[Complaint]:
    """M5 / FR-042：查询本人投诉进度与反馈。"""
    raise NotImplementedError("个人投诉查询待实现")


def list_all_complaints(
    db: Session, page: int, page_size: int
) -> PageResult[Complaint]:
    """M5 / FR-043：管理员查询投诉列表。"""
    raise NotImplementedError("投诉管理查询待实现")


def handle_complaint(
    db: Session, admin: User, complaint_id: int, payload: ComplaintHandle
) -> Complaint:
    """M5 / FR-043：受理、处理或驳回投诉，记录处理说明与时间。"""
    raise NotImplementedError("投诉处理待实现")
