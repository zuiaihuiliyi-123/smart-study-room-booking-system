from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class RegisterRequest(BaseModel):
    """学生自助注册。

    只开放「学生用户」角色：管理员账号由信息中心统一开通（R-03 教师角色已于 V2.1 取消），
    注册接口不接受 role 字段，避免自助提权。
    """

    name: str = Field(min_length=2, max_length=50)
    student_no: str = Field(
        min_length=4, max_length=32, pattern=r"^[A-Za-z0-9_-]+$"
    )
    password: str = Field(min_length=8, max_length=64)
    contact: str | None = Field(default=None, max_length=100)

    @field_validator("name", "student_no", mode="before")
    @classmethod
    def _strip_identity(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def _password_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("密码不能全为空白字符")
        return value

    @field_validator("contact", mode="before")
    @classmethod
    def _blank_contact_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(UserRead):
    """当前登录用户；字段与用户列表/资料响应保持一致。"""
