"""Global exception handlers for AI Backend API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_backend.shared.exceptions import AiBackendException
from common.logging.logger import get_correlation_id, get_logger

logger = get_logger("ai_backend.api.exceptions")


def register_ai_exception_handlers(app: FastAPI) -> None:
    """Đăng ký các bộ xử lý ngoại lệ toàn cục cho AI Backend."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        cid = get_correlation_id()
        logger.warning(
            f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail} [cid={cid}]"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "status_code": exc.status_code,
                "service": "ai_backend",
                "correlation_id": cid,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        cid = get_correlation_id()
        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {exc.errors()} [cid={cid}]"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Dữ liệu đầu vào không hợp lệ",
                "status_code": 422,
                "service": "ai_backend",
                "details": exc.errors(),
                "correlation_id": cid,
            },
        )

    @app.exception_handler(AiBackendException)
    async def ai_backend_exception_handler(
        request: Request, exc: AiBackendException
    ) -> JSONResponse:
        cid = get_correlation_id()
        logger.warning(
            f"AiBackendException [{exc.__class__.__name__}] {exc.status_code} on {request.method} {request.url.path}: {exc.message} [cid={cid}]"
        )
        content: dict[str, Any] = {
            "error": exc.message,
            "status_code": exc.status_code,
            "exception_type": exc.__class__.__name__,
            "service": "ai_backend",
            "correlation_id": cid,
        }
        if hasattr(exc, "category"):
            content["category"] = getattr(exc, "category")
        if hasattr(exc, "detail") and exc.detail:
            content["detail"] = getattr(exc, "detail")
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        cid = get_correlation_id()
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc} [cid={cid}]",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Lỗi nội bộ AI Backend Microservice",
                "status_code": 500,
                "service": "ai_backend",
                "detail": str(exc),
                "correlation_id": cid,
            },
        )
