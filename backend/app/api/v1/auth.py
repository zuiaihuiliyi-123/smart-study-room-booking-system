from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册（学生用户）",
)
def register(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """学生自助注册，成功后直接返回令牌（前端可免去二次登录）。"""
    return auth_service.register(db, payload)


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.login(db, payload)


@router.get("/me", response_model=CurrentUser, summary="当前登录用户")
def me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUser:
    profile = user_service.to_user_read(db, current_user)
    return CurrentUser.model_validate(profile)
