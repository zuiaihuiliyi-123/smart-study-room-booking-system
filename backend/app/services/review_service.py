from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.review import Review
from app.schemas.common import PageResult
from app.schemas.review import ReviewCreate


def create_review(db: Session, user_id: int, payload: ReviewCreate) -> Review:
    """M5 / FR-041：仅本人“已完成”预约可评价一次，评分 1～5。"""
    raise NotImplementedError("评价提交待实现")


def list_my_reviews(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[Review]:
    """M5 / FR-041：查询本人评价。"""
    raise NotImplementedError("个人评价查询待实现")


def list_all_reviews(
    db: Session, page: int, page_size: int
) -> PageResult[Review]:
    """M5 / FR-041：管理员查询评价。"""
    raise NotImplementedError("评价管理查询待实现")
