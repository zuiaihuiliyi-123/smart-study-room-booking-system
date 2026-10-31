from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(UserRead):
    """当前登录用户；字段与用户列表/资料响应保持一致。"""
