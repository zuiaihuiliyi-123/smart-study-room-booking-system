from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.tasks.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "智慧自习室预约与管理系统后端。\n\n"
        "已实现：预约（C1～C6、幂等、并发控制、取消）、签到/签退、"
        "自动与手动违约、黑名单、审计日志、站内通知。\n\n"
        "调试方式：先调用 `POST /api/v1/auth/login` 获取 `access_token`，"
        "再点击右上角 Authorize 粘贴 token（无需 Bearer 前缀）。"
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
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
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["系统"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}
