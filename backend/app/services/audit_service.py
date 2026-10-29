from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


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
