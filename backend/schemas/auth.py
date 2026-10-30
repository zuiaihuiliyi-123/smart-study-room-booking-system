from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(ORMModel):
    id: int
    name: str
    student_no: str
    role: str
    account_status: str
    violation_count: int
    contact: str | None = None
