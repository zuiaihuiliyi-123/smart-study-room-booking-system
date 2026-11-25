from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service, rate_limit_service, user_service

router = APIRouter(prefix="/auth", tags=["认证"])


def _client_ip(request: Request) -> str:
    """取客户端 IP（反向代理场景由 uvicorn --proxy-headers 还原真实地址）。"""
    return request.client.host if request.client is not None else "unknown"


def _register_rate_limit(
    request: Request, db: Session = Depends(get_db)
) -> None:
    rate_limit_service.hit(
        db,
        scope="register",
        key=_client_ip(request),
        limit=settings.register_rate_limit_per_minute,
    )


def _login_rate_limit(request: Request, db: Session = Depends(get_db)) -> None:
    rate_limit_service.hit(
        db,
        scope="login",
        key=_client_ip(request),
        limit=settings.login_rate_limit_per_minute,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册（学生用户）",
    dependencies=[Depends(_register_rate_limit)],
)
def register(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """学生自助注册，成功后直接返回令牌（前端可免去二次登录）。"""
    return auth_service.register(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="登录",
    dependencies=[Depends(_login_rate_limit)],
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    # 锁定按「学号 + 客户端 IP」隔离，避免他人从其他地址锁死受害者账号
    return auth_service.login(db, payload, client_ip=_client_ip(request))


@router.post("/logout", summary="登出（当前令牌立即失效）")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    auth_service.logout(db, current_user)
    return {"message": "已退出登录"}


@router.get("/me", response_model=CurrentUser, summary="当前登录用户")
def me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUser:
    profile = user_service.to_user_read(db, current_user)
    return CurrentUser.model_validate(profile)
