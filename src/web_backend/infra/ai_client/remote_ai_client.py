"""Remote AI Client for Web Backend to interact with AI microservice (Port 8001)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

from common.logging.logger import get_logger
from common.transport.transport import (
    AiClientError,
    ai_chat,
    ai_scan,
    post_json,
    stream_remote_sse,
)

logger = get_logger("web_backend.infra.ai_client")


class RemoteAiClient:
    """Client giao tiếp HTTP với AI Backend Microservice."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("AI_BASE_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.timeout = timeout

    def check_health(self) -> dict[str, Any]:
        """Kiểm tra sức khỏe dịch vụ AI (GET /health)."""
        url = f"{self.base_url}/health"
        req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as exc:
            logger.warning(f"AI Backend health check failed: {exc}")
            return {"status": "unreachable", "error": str(exc)}

    def is_alive(self) -> bool:
        """Kiểm tra AI Backend có đang phản hồi không."""
        res = self.check_health()
        return res.get("status") in ("ok", "healthy")

    def stream_chat(
        self,
        *,
        question: str,
        session_id: str | None = None,
        user_id: str = "default",
        request_id: str | None = None,
        is_disconnected: Callable[[], bool] | None = None,
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        """Stream SSE các sự kiện từ AI Backend (/v1/chat/stream)."""
        payload: dict[str, Any] = {
            "question": question,
            "user_id": user_id,
        }
        if session_id:
            payload["session_id"] = session_id

        return stream_remote_sse(
            path="/v1/chat/stream",
            payload=payload,
            request_id=request_id,
            is_disconnected=is_disconnected,
        )

    def chat(
        self,
        *,
        question: str,
        user_id: str = "default",
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Gửi yêu cầu hỏi đáp trực tiếp (POST /v1/chat)."""
        payload: dict[str, Any] = {
            "question": question,
            "user_id": user_id,
        }
        if session_id:
            payload["session_id"] = session_id
        if request_id:
            payload["request_id"] = request_id

        return post_json("/v1/chat", payload, request_id=request_id)

    def scan(
        self,
        *,
        symbol: str,
        user_id: str = "default",
        threshold_pct: float | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Kích hoạt quét tín hiệu kỹ thuật từ AI Backend (POST /v1/scan)."""
        return ai_scan(
            symbol=symbol,
            user_id=user_id,
            threshold_pct=threshold_pct,
            request_id=request_id,
        )
