"""Middlewares for AI Backend API (Correlation ID & Request Logging)."""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from common.logging.logger import get_logger, set_correlation_id

logger = get_logger("ai_backend.api.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware đảm bảo mỗi request đến AI Backend đều có Correlation ID duy nhất."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_cid = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or ""
        ).strip()
        cid = incoming_cid if incoming_cid else uuid4().hex[:16]

        set_correlation_id(cid)
        request.state.correlation_id = cid

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware ghi log thời gian xử lý và mã phản hồi HTTP của AI Backend."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        cid = getattr(request.state, "correlation_id", "no-cid")
        logger.info(
            f"{request.method} {request.url.path} -> HTTP {response.status_code} "
            f"({duration_ms:.1f}ms) [cid={cid}]"
        )
        return response
