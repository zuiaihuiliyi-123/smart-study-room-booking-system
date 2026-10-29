from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import PageResult
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


@router.get(
    "",
    response_model=PageResult[AuditLogRead],
    summary="审计日志查询（管理员，NFR-009）",
)
def list_logs(
    action_type: str | None = None,
    operator_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[AuditLogRead]:
    return audit_service.list_logs(
        db,
        action_type=action_type,
        operator_id=operator_id,
        page=page,
        page_size=page_size,
    )
