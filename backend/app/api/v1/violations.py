from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.violation import ViolationRecord
from app.schemas.common import PageResult
from app.schemas.violation import ManualViolationCreate, ViolationRead
from app.services import violation_service

router = APIRouter(prefix="/violations", tags=["M3 违约管理"])


@router.get("/me", response_model=PageResult[ViolationRead], summary="本人违约记录")
def list_my_violations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PageResult[ViolationRead]:
    return violation_service.list_my_violations(
        db, current_user.id, page, page_size
    )


@router.get("", response_model=PageResult[ViolationRead], summary="违约记录（管理员）")
def list_all_violations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[ViolationRead]:
    return violation_service.list_all_violations(db, page, page_size)


@router.post(
    "/manual",
    response_model=ViolationRead,
    summary="手动违约登记（管理员）",
)
def register_manual(
    payload: ManualViolationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ViolationRecord:
    return violation_service.register_manual(db, admin, payload)
