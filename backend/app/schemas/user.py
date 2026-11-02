from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccountStatus
from app.schemas.common import ORMModel


class UserUpdate(BaseModel):
    """学生仅可修改联系方式，身份字段不可改（FR-040）。"""

    contact: str | None = Field(default=None, max_length=100)


class AccountStatusUpdate(BaseModel):
    """管理员调整账户状态（ST-044 / ST-045 / ST-046），须填写原因（NFR-009）。"""

    account_status: AccountStatus
    reason: str = Field(min_length=1, max_length=255)


class UserRead(ORMModel):
    id: int
    name: str
    student_no: str
    role: str
    account_status: str
    violation_count: int
    contact: str | None = None
    #: 受限账户的预计解除时间（FR-044 / ST-040）。
    #: 只有“自动限制”有自动解除时间；管理员手动限制须由管理员解除，因此为 None。
    restrict_until: datetime | None = None
