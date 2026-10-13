"""SSE của swarm chat — không ghi session SQLite.

Process AI phát các event này qua POST /v1/chat/stream.
Process web, khi AI_TRANSPORT=http, chỉ proxy và tự lưu hội thoại.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from backend.application.answer_question import answer_question


def swarm_public_payload(result: Any, *, started: float) -> dict[str, Any]:
    """Payload final_answer / complete. Không có session_id hay message_id."""
    price_payload: dict[str, Any] | None = None
    if result.price is not None:
        p = result.price
        price_payload = {
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        }

    news_items: list[dict[str, Any]] = []
    news_error: str | None = None
    if result.news is not None:
        news_error = result.news.error
        news_items = [
            {
                "title": i.title,
                "url": i.url,
                "published_at": i.published_at,
                "snippet": i.snippet,
            }
            for i in (result.news.items or [])
        ]

    severity = None
    if result.eval_result is not None:
        severity = result.eval_result.severity.model_dump(mode="json")

    chart_path = getattr(result, "chart_path", None)
    raw_steps = [
        s.model_dump() if hasattr(s, "model_dump") else s
        for s in (result.steps or [])
    ]
    rewritten = result.rewritten if hasattr(result, "rewritten") else None
    routing = getattr(result, "routing", None)
    return {
        "question": result.question,
        "rewritten": rewritten.rewritten if rewritten else "",
        "symbol": rewritten.symbol if rewritten else None,
        "intent": rewritten.intent if rewritten else "",
        "agents_to_call": list(routing.agents_to_call or []) if routing else [],
        "route": str(getattr(routing.route, "value", routing.route)) if routing else "",
        "reason": (routing.reason or "") if routing else "",
        "answer": result.answer or "",
        "steps": raw_steps,
        "hitl_used": result.hitl_used,
        "pending_approvals_created": result.pending_approvals_created,
        "error": result.error,
        "price": price_payload,
        "news_count": len(news_items),
        "news": news_items,
        "news_error": news_error,
        "severity": severity,
        "chart_path": chart_path,
        "source_file": getattr(result, "source_file", None),
        "total_duration_s": round(time.perf_counter() - started, 3),
    }


def iter_swarm_events(
    question: str,
    deps: Any,
    *,
    user_id: str = "default",
    request_id: str | None = None,
    cancel_event: threading.Event | None = None,
    is_disconnected: Callable[[], bool] | None = None,
    watchlist_store: Any | None = None,
    account_holdings: list | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Chạy answer_question và yield (event, data). Không mở SQLite session."""
    started = time.perf_counter()
    cancel = cancel_event or threading.Event()
    event_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def _event_cb(event: str, data: dict[str, Any]) -> None:
        event_queue.put((event, data))

    def _worker() -> None:
        from backend.graph.chat import StreamCancelledError, set_stream_cancel_event

        set_stream_cancel_event(cancel)
        try:
            result = answer_question(
                question,
                price_source=deps.price_source,
                news_source=deps.news_source,
                history_store=deps.history_store,
                memory_store=deps.memory_store,
                user_id=user_id,
                request_id=request_id,
                event_callback=_event_cb,
                watchlist_store=watchlist_store,
                account_holdings=account_holdings,
            )
            payload = swarm_public_payload(result, started=started)
            event_queue.put(("final_answer", payload))
            event_queue.put(("complete", dict(payload)))
        except StreamCancelledError:
            event_queue.put(("error", {"error": "client disconnected"}))
        except Exception as exc:
            event_queue.put(("error", {"error": str(exc)}))
        finally:
            set_stream_cancel_event(None)
            event_queue.put(None)

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    try:
        while True:
            if is_disconnected and is_disconnected():
                cancel.set()
                break
            try:
                item = event_queue.get(timeout=0.2)
            except queue.Empty:
                if not worker.is_alive():
                    break
                continue
            if item is None:
                break
            yield item
    finally:
        cancel.set()
