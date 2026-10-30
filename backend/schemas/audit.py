from datetime import datetime

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: int
    operator_id: int | None = None
    action_type: str
    target_type: str
    target_id: int | None = None
    reason: str | None = None
    before_value: str | None = None
    after_value: str | None = None
    created_at: datetime
