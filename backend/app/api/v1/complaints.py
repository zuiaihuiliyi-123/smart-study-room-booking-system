from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_student
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
    current_user: User = Depends(require_student),
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
    status: str | None = None,
    target_type: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[ComplaintRead]:
    return complaint_service.list_all_complaints(
        db,
        page,
        page_size,
        status=status,
        target_type=target_type,
        created_from=created_from,
        created_to=created_to,
    )


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


@router.post(
    "/{complaint_id}/confirm",
    response_model=ComplaintRead,
    summary="投诉人确认并关闭投诉",
)
def confirm_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> Complaint:
    """ST-063：仅投诉人本人可在「已处理」状态下确认关闭。"""
    return complaint_service.confirm_close(db, current_user.id, complaint_id)
