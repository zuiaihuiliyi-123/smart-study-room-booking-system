"""M5 评价管理（FR-041，BR-013：仅本人已完成的预约可评价一次）。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models.enums import ReservationStatus
from app.models.reservation import Reservation
from app.models.review import Review
from app.schemas.common import PageResult
from app.schemas.review import ReviewCreate, ReviewRead
from app.utils.pagination import to_offset


def create_review(db: Session, user_id: int, payload: ReviewCreate) -> Review:
    """M5 / FR-041：提交评价。

    校验顺序：预约单存在 → 属于本人 → 状态为“已完成” → 该预约单未被评价过。
    """
    reservation = db.get(Reservation, payload.reservation_id)
    if reservation is None:
        raise BusinessError("预约单不存在", code="RESERVATION_NOT_FOUND", status_code=404)

    if reservation.user_id != user_id:
        raise BusinessError(
            "只能评价本人的预约", code="REVIEW_NOT_OWNER", status_code=403
        )

    if reservation.status != ReservationStatus.COMPLETED.value:
        raise BusinessError(
            "仅状态为“已完成”的预约可以评价",
            code="REVIEW_NOT_ALLOWED",
            status_code=409,
        )

    duplicated = db.scalar(
        select(Review).where(Review.reservation_id == payload.reservation_id)
    )
    if duplicated is not None:
        raise BusinessError(
            "该预约单已评价过，不能重复评价", code="REVIEW_ALREADY_EXISTS", status_code=409
        )

    review = Review(
        user_id=user_id,
        reservation_id=payload.reservation_id,
        score=payload.score,
        content=payload.content,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_my_reviews(
    db: Session, user_id: int, page: int, page_size: int
) -> PageResult[ReviewRead]:
    """M5 / FR-041：查询本人评价（按提交时间倒序）。"""
    total = (
        db.scalar(select(func.count()).select_from(Review).where(Review.user_id == user_id))
        or 0
    )
    rows = db.scalars(
        select(Review)
        .where(Review.user_id == user_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[ReviewRead](
        items=[ReviewRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_all_reviews(
    db: Session, page: int, page_size: int
) -> PageResult[ReviewRead]:
    """M5 / FR-041：管理员查询评价（按提交时间倒序）。"""
    total = db.scalar(select(func.count()).select_from(Review)) or 0
    rows = db.scalars(
        select(Review)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(to_offset(page, page_size))
        .limit(page_size)
    )
    return PageResult[ReviewRead](
        items=[ReviewRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
