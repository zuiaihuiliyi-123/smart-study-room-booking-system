from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class UserUpdate(BaseModel):
    """学生仅可修改联系方式，身份字段不可改（FR-040）。"""

    contact: str | None = Field(default=None, max_length=100)


class PasswordChangeRequest(BaseModel):
    """本人自助修改密码（B1）。

    旧密码用于二次确认身份；新密码长度与注册口径一致（8～64 位）。
    """

    old_password: str = Field(min_length=6, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("old_password", "new_password")
    @classmethod
    def _password_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("密码不能全为空白字符")
        return value


class AccountStatusUpdate(BaseModel):
    """管理员调整账户状态（ST-044 / ST-045 / ST-046），须填写原因（NFR-009）。

    本接口只负责「停用 / 恢复学生账户」；「受限」只能由黑名单/自动违约流程产生，
    因此这里不接受 `受限`，避免绕过 FR-044 的黑名单审计与期限规则。
    """

    account_status: Literal["正常", "停用"]
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
