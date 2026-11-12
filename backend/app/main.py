from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.cache import clear_dashboard_cache
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.tasks.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动期安全校验：JWT 密钥不得为公开占位符（§2.1 不得绕过身份认证）
    settings.validate_security()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="智慧自习室预约与管理系统 API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.middleware("http")
async def clear_dashboard_cache_after_writes(request, call_next):
    """写请求成功后清掉看板短缓存，避免管理操作后仍返回旧统计。"""
    response = await call_next(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and response.status_code < 500:
        clear_dashboard_cache()
    return response


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["系统"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}
