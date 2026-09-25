"""AI runtime client — mặc định gọi LangGraph Swarm nội bộ (in-process).

Hỗ trợ chế độ HTTP proxy khi cấu hình AI_TRANSPORT=http (dùng cho kiến trúc phân tán microservices hoặc testing).
"""

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


def _use_http() -> bool:
    return os.environ.get("AI_TRANSPORT", "inprocess").strip().lower() == "http"


class AiClientError(RuntimeError):
    """Ngoại lệ khi gọi AI Swarm qua HTTP hoặc in-process."""


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


def _chat_inprocess(
    *,
    question: str,
    user_id: str,
    request_id: str | None,
) -> dict[str, Any]:
    from backend.api.deps import get_app_deps
    from backend.application.answer_question import answer_question

    deps = get_app_deps()
    try:
        result = answer_question(
            question,
            price_source=deps.price_source,
            news_source=deps.news_source,
            history_store=deps.history_store,
            memory_store=deps.memory_store,
            user_id=user_id,
            request_id=request_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise AiClientError(f"AI in-process chat lỗi: {exc}") from exc

    price_payload = None
    if result.price is not None:
        p = result.price
        price_payload = {
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        }
    severity = None
    if result.eval_result is not None:
        severity = result.eval_result.severity.model_dump(mode="json")

    diag = None
    if getattr(result, "diagram_result", None) is not None:
        diag = {
            "mermaid": getattr(result.diagram_result, "mermaid", None),
            "graph_json": getattr(result.diagram_result, "graph_json", None),
            "format": getattr(result.diagram_result, "format", "mermaid"),
        }

    return {
        "answer": result.answer,
        "steps": list(result.steps or []),
        "question": result.question,
        "symbol": result.rewritten.symbol,
        "route": str(getattr(result.routing.route, "value", result.routing.route)),
        "error": result.error,
        "request_id": request_id,
        "rewritten": result.rewritten.rewritten,
        "agents_to_call": list(result.routing.agents_to_call or []),
        "price": price_payload,
        "news_count": len(result.news.items) if result.news else 0,
        "severity": severity,
        "diagram": diag,
        "chart_path": getattr(result, "chart_path", None),
        "chart_result": getattr(result, "chart_result", None),
    }


def _scan_inprocess(
    *,
    symbol: str,
    user_id: str,
    threshold_pct: float | None,
    request_id: str | None,
) -> dict[str, Any]:
    from backend.api.deps import get_app_deps
    from backend.application.scan_symbol import scan_symbol

    deps = get_app_deps()
    try:
        result = scan_symbol(
            symbol,
            price_source=deps.price_source,
            news_source=deps.news_source,
            history_store=deps.history_store,
            memory_store=deps.memory_store,
            notifier=deps.notifier,
            watchlist_store=deps.watchlist_store,
            user_id=user_id,
            threshold_pct=threshold_pct,
            request_id=request_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise AiClientError(f"AI in-process scan lỗi: {exc}") from exc

    news_items = [
        {
            "title": i.title,
            "url": i.url,
            "published_at": i.published_at,
            "snippet": i.snippet,
        }
        for i in (result.news.items or [])
    ]
    p = result.price
    return {
        "symbol": result.symbol,
        "route": str(getattr(result.routing.route, "value", result.routing.route)),
        "steps": list(result.steps or []),
        "reason": result.routing.reason or "",
        "threshold_pct": result.threshold_pct,
        "gate1_action": result.gate1_action,
        "gate2_pending": result.gate2_pending,
        "error": result.error,
        "request_id": request_id,
        "price": {
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        },
        "news_count": len(news_items),
        "news": news_items,
        "news_error": result.news.error,
        "severity": (
            result.severity.model_dump(mode="json") if result.severity else None
        ),
        "alert": (result.alert.model_dump(mode="json") if result.alert else None),
        "pending_events": list(result.pending_events),
    }


def ai_chat(
    *,
    question: str,
    user_id: str = "default",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Thực thi câu hỏi chat với AI Swarm (in-process hoặc qua HTTP proxy)."""
    if _use_http():
        payload: dict[str, Any] = {"question": question, "user_id": user_id}
        if request_id:
            payload["request_id"] = request_id
        return _post_json("/v1/chat", payload, request_id=request_id)
    return _chat_inprocess(
        question=question, user_id=user_id, request_id=request_id
    )


def ai_scan(
    *,
    symbol: str,
    user_id: str = "default",
    threshold_pct: float | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Thực thi quét giám sát mã cổ phiếu với AI Swarm."""
    if _use_http():
        payload: dict[str, Any] = {"symbol": symbol, "user_id": user_id}
        if threshold_pct is not None:
            payload["threshold_pct"] = threshold_pct
        if request_id:
            payload["request_id"] = request_id
        return _post_json("/v1/scan", payload, request_id=request_id)
    return _scan_inprocess(
        symbol=symbol,
        user_id=user_id,
        threshold_pct=threshold_pct,
        request_id=request_id,
    )
