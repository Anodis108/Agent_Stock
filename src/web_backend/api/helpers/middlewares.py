"""FastAPI middlewares for Web Backend — Correlation ID injection and Request Logging."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from common.logging.logger import correlation_id_ctx, get_logger

logger = get_logger("web_backend.api.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware tự động trích xuất hoặc sinh mới Correlation ID cho mỗi request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex[:16]
        )
        token = correlation_id_ctx.set(corr_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware ghi log thời gian xử lý và mã trạng thái của mỗi request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"{method} {path} - {response.status_code} ({duration_ms:.1f}ms)"
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"{method} {path} failed after {duration_ms:.1f}ms: {exc}"
            )
            raise


def register_middlewares(app: FastAPI) -> None:
    """Đăng ký toàn bộ middleware cần thiết vào FastAPI app."""
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
