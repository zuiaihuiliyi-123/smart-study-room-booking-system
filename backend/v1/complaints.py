from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.complaint import Complaint
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.complaint import ComplaintCreate, ComplaintHandle, ComplaintRead
from app.services import complaint_service

router = APIRouter(prefix="/complaints", tags=["M5 投诉管理"])


@router.post(
    "",
    response_model=ComplaintRead,
    status_code=status.HTTP_201_CREATED,
    summary="提交投诉",
)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Complaint:
    return complaint_service.create_complaint(db, current_user.id, payload)


@router.get("/me", response_model=PageResult[ComplaintRead], summary="本人投诉")
def list_my_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResult[ComplaintRead]:
    return complaint_service.list_my_complaints(
        db, current_user.id, page, page_size
    )


@router.get("", response_model=PageResult[ComplaintRead], summary="投诉列表（管理员）")
def list_all_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[ComplaintRead]:
    return complaint_service.list_all_complaints(db, page, page_size)


@router.patch(
    "/{complaint_id}",
    response_model=ComplaintRead,
    summary="处理投诉（管理员）",
)
def handle_complaint(
    complaint_id: int,
    payload: ComplaintHandle,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Complaint:
    return complaint_service.handle_complaint(db, admin, complaint_id, payload)
