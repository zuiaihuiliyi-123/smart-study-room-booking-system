from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.review import Review
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["M5 评价管理"])


@router.post(
    "",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="提交评价",
)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Review:
    return review_service.create_review(db, current_user.id, payload)


@router.get("/me", response_model=PageResult[ReviewRead], summary="本人评价")
def list_my_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResult[ReviewRead]:
    return review_service.list_my_reviews(db, current_user.id, page, page_size)


@router.get("", response_model=PageResult[ReviewRead], summary="评价列表（管理员）")
def list_all_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[ReviewRead]:
    return review_service.list_all_reviews(db, page, page_size)
