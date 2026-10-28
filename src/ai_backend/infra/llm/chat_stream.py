"""SSE của swarm chat — không ghi session vào database.

Wire format (giống llm-engineer-demo `/chat/stream-sse`):
  ``data: {"token": "..."}`` từng chunk, payload cuối ``data: {"complete": true, ...}``,
  kết thúc ``data: [DONE]``. Lỗi: ``data: {"error": "..."}``.

Process web (AI_TRANSPORT=http) parse qua ``stream_remote_sse`` rồi có thể bọc lại ``event:``.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from ai_backend.domain.agents.graph import start_graph
from ai_backend.domain.agents.scan.state import main_item


def swarm_public_payload(state: dict[str, Any], *, started: float) -> dict[str, Any]:
    """Payload final SSE từ state checkpoint (``start_graph`` yield ``result``)."""
    rewritten = state["rewritten"]
    guard = state["guardrail_result"]
    if rewritten is not None:
        route = str(rewritten.intent)
    elif guard is None:
        route = "empty"
    elif guard.category == "greeting":
        route = "greeting"
    else:
        route = "guardrail"

    notes = state["notes"]
    agents_to_call = list(notes.keys()) if notes else []

    prices = state["prices"] or []
    p = main_item(prices, state) if prices else None
    price = (
        None
        if p is None
        else {
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        }
    )

    news = main_item(state["news"] or [], state) if state["news"] else None
    news_n = len(news.items) if news and news.items else 0

    ev = state["eval_result"]
    severity = ev.severity.model_dump(mode="json") if ev is not None else None

    chart = state["chart_result"]
    chart_path = chart.url if chart is not None and chart.success else None

    return {
        "question": state["question"] or "",
        "rewritten": rewritten.rewritten if rewritten is not None else "",
        "symbol": rewritten.symbol if rewritten is not None else None,
        "intent": rewritten.intent if rewritten is not None else "",
        "agents_to_call": agents_to_call,
        "route": route,
        "reason": "",
        "answer": state["answer"] or "",
        "error": state["error"],
        "price": price,
        "news_count": news_n,
        "news": (
            [
                {"title": i.title, "url": i.url, "published_at": i.published_at, "snippet": i.snippet}
                for i in (news.items or [])
            ]
            if news
            else []
        ),
        "news_error": news.error if news else None,
        "severity": severity,
        "chart_path": chart_path,
        "source_file": state["source_file"],
        "total_duration_s": round(time.perf_counter() - started, 3),
    }


def _sse_data(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _token_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, dict) and "delta" in chunk:
        return str(chunk["delta"])
    return str(chunk)


async def swarm_sse(
    question: str,
    request_deps: dict[str, Any],
    *,
    user_id: str = "default",
    request_id: str | None = None,
) -> AsyncIterator[str]:
    """Chạy start_graph (mode=chat) và yield SSE demo-format. Client đóng → generator huỷ, graph dừng theo."""
    started = time.perf_counter()

    try:
        async for kind, payload in start_graph(
            "chat", question, request_deps, user_id=user_id, request_id=request_id
        ):
            if kind == "token":
                yield _sse_data({"token": _token_text(payload)})
            elif kind == "result":
                yield _sse_data(
                    {
                        **swarm_public_payload(payload, started=started),
                        "request_id": request_id,
                        "complete": True,
                    }
                )
        yield _sse_data("[DONE]")
    except Exception as exc:  # noqa: BLE001 — báo lỗi cho client thay vì cắt stream
        yield _sse_data({"error": str(exc)})
