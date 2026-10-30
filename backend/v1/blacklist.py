from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.blacklist import BlacklistEntry
from app.models.user import User
from app.schemas.blacklist import BlacklistCreate, BlacklistRead, BlacklistRelease
from app.schemas.common import PageResult
from app.services import blacklist_service

router = APIRouter(prefix="/blacklist", tags=["M5 黑名单"])


@router.get("", response_model=PageResult[BlacklistRead], summary="黑名单记录（管理员）")
def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[BlacklistRead]:
    return blacklist_service.list_entries(db, page, page_size)


@router.post(
    "",
    response_model=BlacklistRead,
    status_code=status.HTTP_201_CREATED,
    summary="手动加入黑名单（管理员）",
)
def add_entry(
    payload: BlacklistCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BlacklistEntry:
    return blacklist_service.add_entry(db, admin, payload)


@router.post(
    "/{entry_id}/release",
    response_model=BlacklistRead,
    summary="解除黑名单（管理员）",
)
def release_entry(
    entry_id: int,
    payload: BlacklistRelease,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BlacklistEntry:
    return blacklist_service.release_entry(db, admin, entry_id, payload.reason)
