"""HTTP/in-process transport tới swarm. Không import OpenAI.

Process web chỉ cần module này. Factory OpenAI nằm ở client.py và chỉ process AI dùng.
"""

from __future__ import annotations

import json
import os
import queue
import random
import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
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
    transport = os.environ.get("AI_TRANSPORT", "").strip().lower()
    if transport == "http":
        return True
    if transport == "inprocess":
        return False
    return bool(os.environ.get("AI_BASE_URL", "").strip())


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


def _is_rate_limited(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def _retry_delay(attempt: int) -> float:
    return (2**attempt) + random.uniform(0, 1)


def _post_json_once(
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


def _post_json(
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
    request_id: str | None = None,
    max_retries: int | None = None,
) -> dict[str, Any]:
    """POST JSON với retry exponential backoff + jitter cho 429/timeout."""
    retries = max_retries
    if retries is None:
        raw = os.environ.get("AI_HTTP_MAX_RETRIES", "3")
        try:
            retries = max(1, int(raw))
        except ValueError:
            retries = 3

    last_exc: BaseException | None = None
    for attempt in range(retries):
        try:
            return _post_json_once(
                path,
                payload,
                timeout=timeout,
                request_id=request_id,
            )
        except AiClientError as exc:
            last_exc = exc
            if attempt >= retries - 1:
                raise
            if _is_rate_limited(exc) or _is_timeout(exc):
                time.sleep(_retry_delay(attempt))
                continue
            raise
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_exc = exc
            if attempt >= retries - 1:
                if isinstance(exc, urllib.error.HTTPError):
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise AiClientError(f"AI HTTP {exc.code}: {detail or exc.reason}") from exc
                if _is_timeout(exc):
                    raise AiClientError("AI timeout") from exc
                raise AiClientError(f"AI không kết nối được: {exc}") from exc
            if _is_rate_limited(exc) or _is_timeout(exc):
                time.sleep(_retry_delay(attempt))
                continue
            raise AiClientError(str(exc)) from exc
    if last_exc is not None:
        raise AiClientError(str(last_exc)) from last_exc
    raise AiClientError("AI HTTP retry exhausted")


def _chat_inprocess(
    *,
    question: str,
    user_id: str,
    request_id: str | None,
) -> dict[str, Any]:
    from backend.deps import get_app_deps
    from backend.answer_question import answer_question

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
        "source_file": getattr(result, "source_file", None),
    }


def _scan_inprocess(
    *,
    symbol: str,
    user_id: str,
    threshold_pct: float | None,
    request_id: str | None,
) -> dict[str, Any]:
    from backend.deps import get_app_deps
    from backend.scan_symbol import scan_symbol

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


def _stream_timeout() -> float:
    """Timeout từng lần đọc SSE. Tách khỏi AI_HTTP_TIMEOUT của JSON chat."""
    raw = os.environ.get("AI_HTTP_STREAM_TIMEOUT", "300")
    try:
        val = float(raw)
    except ValueError:
        return 300.0
    return val if val > 0 else 300.0


def _format_stream_error(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc.reason)
        return f"AI HTTP {exc.code}: {detail or exc.reason}"
    if _is_timeout(exc):
        return "AI timeout"
    if isinstance(exc, urllib.error.URLError):
        return f"AI không kết nối được: {exc.reason}"
    return f"AI không kết nối được: {exc}"


def _attach_account_lists(payload: dict[str, Any], user_id: str) -> None:
    from backend.infra.llm.account_snapshot import load_account_snapshot

    snapshot = load_account_snapshot(user_id)
    payload["watchlist"] = snapshot["watchlist"]
    payload["holdings"] = snapshot["holdings"]


def iter_remote_chat_events(
    *,
    question: str,
    user_id: str = "default",
    request_id: str | None = None,
    cancel_event: threading.Event | None = None,
    is_disconnected: Callable[[], bool] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Đọc SSE từ POST /v1/chat/stream. Yield (event, data). Lỗi kết nối thành event error."""
    from backend.infra.llm.account_snapshot import question_needs_account_lists

    payload: dict[str, Any] = {"question": question, "user_id": user_id}
    if request_id:
        payload["request_id"] = request_id
    if question_needs_account_lists(question):
        _attach_account_lists(payload, user_id)
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if request_id:
        headers["X-Request-Id"] = request_id
    req = urllib.request.Request(
        f"{_ai_base()}/v1/chat/stream",
        data=body,
        headers=headers,
        method="POST",
    )
    cancel = cancel_event or threading.Event()
    line_q: queue.Queue[str | BaseException | None] = queue.Queue()
    handle: dict[str, Any] = {}

    def _reader() -> None:
        resp = None
        try:
            resp = urllib.request.urlopen(req, timeout=_stream_timeout())
            handle["resp"] = resp
            if cancel.is_set():
                return
            while not cancel.is_set():
                raw = resp.readline()
                if not raw:
                    break
                line_q.put(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
        except Exception as exc:
            line_q.put(exc)
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass
            line_q.put(None)

    threading.Thread(target=_reader, daemon=True).start()

    event_name: str | None = None
    data_lines: list[str] = []

    def _flush() -> tuple[str, dict[str, Any]] | None:
        nonlocal event_name, data_lines
        name = event_name
        raw_data = "\n".join(data_lines).strip()
        event_name = None
        data_lines = []
        if not name or not raw_data:
            return None
        try:
            parsed = json.loads(raw_data)
        except json.JSONDecodeError:
            parsed = {"raw": raw_data}
        if not isinstance(parsed, dict):
            parsed = {"raw": parsed}
        return name, parsed

    try:
        while True:
            if is_disconnected and is_disconnected():
                cancel.set()
                resp = handle.get("resp")
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass
                break
            try:
                item = line_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                pending = _flush()
                if pending is not None:
                    yield pending
                break
            if isinstance(item, BaseException):
                yield ("error", {"error": _format_stream_error(item)})
                break
            if item.startswith(":"):
                continue
            if item == "":
                pending = _flush()
                if pending is not None:
                    yield pending
                continue
            if item.startswith("event:"):
                event_name = item.split(":", 1)[1].strip()
                continue
            if item.startswith("data:"):
                data_lines.append(item.split(":", 1)[1].strip())
    finally:
        cancel.set()
        resp = handle.get("resp")
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass


def ai_chat(
    *,
    question: str,
    user_id: str = "default",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Thực thi câu hỏi chat với AI Swarm (in-process hoặc qua HTTP proxy)."""
    if _use_http():
        from backend.infra.llm.account_snapshot import question_needs_account_lists

        payload: dict[str, Any] = {"question": question, "user_id": user_id}
        if request_id:
            payload["request_id"] = request_id
        if question_needs_account_lists(question):
            _attach_account_lists(payload, user_id)
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
        _attach_account_lists(payload, user_id)
        return _post_json("/v1/scan", payload, request_id=request_id)
    return _scan_inprocess(
        symbol=symbol,
        user_id=user_id,
        threshold_pct=threshold_pct,
        request_id=request_id,
    )
