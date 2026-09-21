"""HTTP client tới AI service — chỉ dùng stdlib, không import domain.agents."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any


def _ai_base() -> str:
    return os.environ.get("AI_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def _default_timeout() -> float:
    raw = os.environ.get("AI_HTTP_TIMEOUT", "60")
    try:
        val = float(raw)
    except ValueError:
        return 60.0
    return val if val > 0 else 60.0


class AiClientError(RuntimeError):
    pass


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True
        return "timed out" in str(reason).lower()
    return "timed out" in str(exc).lower()


def _post_json(
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    url = f"{_ai_base()}{path}"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if request_id:
        headers["X-Request-Id"] = request_id
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    to = _default_timeout() if timeout is None else timeout
    try:
        with urllib.request.urlopen(req, timeout=to) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AiClientError(f"AI HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        if _is_timeout(exc):
            raise AiClientError("AI timeout") from exc
        raise AiClientError(f"AI không kết nối được: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AiClientError("AI timeout") from exc
    except socket.timeout as exc:
        raise AiClientError("AI timeout") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiClientError("AI trả JSON không hợp lệ") from exc
    if not isinstance(data, dict):
        raise AiClientError("AI response không phải object")
    return data


def ai_chat(
    *,
    question: str,
    user_id: str = "default",
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"question": question, "user_id": user_id}
    if request_id:
        payload["request_id"] = request_id
    return _post_json("/v1/chat", payload, request_id=request_id)


def ai_scan(
    *,
    symbol: str,
    user_id: str = "default",
    threshold_pct: float | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"symbol": symbol, "user_id": user_id}
    if threshold_pct is not None:
        payload["threshold_pct"] = threshold_pct
    if request_id:
        payload["request_id"] = request_id
    return _post_json("/v1/scan", payload, request_id=request_id)
