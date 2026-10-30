from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class UserUpdate(BaseModel):
    """学生仅可修改联系方式，身份字段不可改（FR-040）。"""

    contact: str | None = Field(default=None, max_length=100)


class UserRead(ORMModel):
    id: int
    name: str
    student_no: str
    role: str
    account_status: str
    violation_count: int
    contact: str | None = None
