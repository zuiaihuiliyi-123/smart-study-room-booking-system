from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogRead
from app.schemas.common import PageResult


def record(
    db: Session,
    *,
    operator_id: int | None,
    action_type: str,
    target_type: str,
    target_id: int | None = None,
    reason: str | None = None,
    before_value: str | None = None,
    after_value: str | None = None,
) -> AuditLog:
    """NFR-009：记录管理员关键操作与越权尝试（只追加）。"""
    log = AuditLog(
        operator_id=operator_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        before_value=before_value,
        after_value=after_value,
    )
    db.add(log)
    return log


def list_logs(
    db: Session,
    *,
    action_type: str | None,
    operator_id: int | None,
    page: int,
    page_size: int,
) -> PageResult[AuditLogRead]:
    """NFR-009：管理员查询审计日志（只读）。"""
    conditions = []
    if action_type:
        conditions.append(AuditLog.action_type == action_type)
    if operator_id is not None:
        conditions.append(AuditLog.operator_id == operator_id)

    total = (
        db.scalar(
            select(func.count()).select_from(AuditLog).where(*conditions)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PageResult[AuditLogRead](
        items=[AuditLogRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
