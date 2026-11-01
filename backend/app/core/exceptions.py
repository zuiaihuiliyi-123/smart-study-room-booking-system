from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    """业务异常：统一返回 code + message + 可选 details。

    ``code`` 建议直接使用需求编号（如 C3_BR-006、ST-029），便于前端提示与测试断言。
    ``details`` 用于携带未通过的判定项、参数值与冲突明细（FR-012 / IC-04）。
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "BUSINESS_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_: Request, exc: BusinessError) -> JSONResponse:
        content: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.details:
            content["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        _: Request, exc: HTTPException
    ) -> JSONResponse:
        """把 FastAPI/依赖层异常也统一成 code + message 结构。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "details": {
                    "errors": [
                        {
                            "loc": list(item.get("loc", [])),
                            "msg": item.get("msg", ""),
                            "type": item.get("type", ""),
                        }
                        for item in exc.errors()
                    ]
                },
            },
        )

    @app.exception_handler(NotImplementedError)
    async def handle_not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "code": "NOT_IMPLEMENTED",
                "message": str(exc) or "该功能尚未实现",
            },
        )
