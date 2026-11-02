from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.user import AccountStatusUpdate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/me", response_model=UserRead, summary="查看本人资料")
def my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return user_service.to_user_read(db, current_user)


@router.patch("/me", response_model=UserRead, summary="修改本人联系方式")
def update_my_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    updated = user_service.update_my_profile(db, current_user, payload)
    return user_service.to_user_read(db, updated)


@router.get("", response_model=PageResult[UserRead], summary="用户列表（管理员）")
def list_users(
    keyword: str | None = None,
    role: str | None = None,
    account_status: str | None = None,
    violation_min: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[UserRead]:
    return user_service.list_users(
        db,
        page,
        page_size,
        keyword=keyword,
        role=role,
        account_status=account_status,
        violation_min=violation_min,
    )


@router.patch(
    "/{user_id}/account-status",
    response_model=UserRead,
    summary="调整账户状态：停用 / 恢复（管理员）",
)
def update_account_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    """FR-044 / ST-044 / ST-045 / ST-046：管理员停用或恢复账户，须填写原因。"""
    user = user_service.set_account_status(db, user_id, payload, admin.id)
    return user_service.to_user_read(db, user, mask_contact=True)
