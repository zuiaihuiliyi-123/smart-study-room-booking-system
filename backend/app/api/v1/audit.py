from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import PageResult
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["M5 审计日志"])


@router.get(
    "",
    response_model=PageResult[AuditLogRead],
    summary="审计日志（管理员，只读）",
)
def list_audit_logs(
    action_type: str | None = None,
    operator_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PageResult[AuditLogRead]:
    """NFR-009：查询关键操作与越权尝试的审计记录（只追加、不提供修改/导出）。"""
    return audit_service.list_logs(
        db,
        action_type=action_type,
        operator_id=operator_id,
        page=page,
        page_size=page_size,
    )
