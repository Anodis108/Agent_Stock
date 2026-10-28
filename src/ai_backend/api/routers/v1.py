"""Hợp đồng HTTP v1 của AI Backend Microservice (/v1/chat, /v1/chat/stream, /v1/scan)."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_backend.infra.llm.account_snapshot import SnapshotWatchlistStore
from common.domain.entities import WatchlistItem
from web_backend.api.deps import AppDeps, get_app_deps
from web_backend.api.helpers.validation import normalize_question, normalize_symbol, validate_threshold_pct

router = APIRouter(prefix="/v1", tags=["ai-v1"])


class ChatStep(BaseModel):
    id: str = ""
    name: str = ""
    status: str = "done"
    detail: str | None = None
    input: Any = None
    output: Any = None
    static_info: Any = None
    system_prompt: Any = None
    prompt_template: Any = None
    duration_s: float | None = None
    duration_ms: int | None = None


class WatchlistSnapshot(BaseModel):
    symbol: str
    threshold_pct: float = 3.0
    user_id: str = Field(min_length=1)


class HoldingSnapshot(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    user_id: str = Field(min_length=1)


class V1ChatRequest(BaseModel):
    question: str
    user_id: str = Field(min_length=1)
    request_id: str | None = None


class V1ChatResponse(BaseModel):
    answer: str
    steps: list[ChatStep] = Field(default_factory=list)
    question: str = ""
    request_id: str | None = None
    drawed_paths: list[str] = Field(default_factory=list)


class V1ScanRequest(BaseModel):
    symbol: str
    user_id: str = Field(min_length=1)
    threshold_pct: float | None = None
    request_id: str | None = None
    watchlist: list[WatchlistSnapshot] | None = None
    holdings: list[HoldingSnapshot] | None = None


def _lists_from_body(body: V1ScanRequest):
    """Payload có mặt thì dùng snapshot. Không có thì AI giữ đường cũ."""
    sent = body.model_fields_set
    if "watchlist" not in sent and "holdings" not in sent:
        return None, None
    items = [
        WatchlistItem(
            symbol=row.symbol.strip().upper(),
            threshold_pct=float(row.threshold_pct),
            user_id=row.user_id.strip(),
        )
        for row in (body.watchlist or [])
    ]
    holdings = [row.model_dump() for row in (body.holdings or [])]
    return SnapshotWatchlistStore(items), holdings


class V1ScanResponse(BaseModel):
    symbol: str
    route: str
    steps: list[ChatStep] = Field(default_factory=list)
    reason: str = ""
    threshold_pct: float = 0.0
    status: str = "done"  # done | pending_approval
    thread_id: str = ""
    tool_call: dict[str, Any] | None = None
    request_id: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None


import asyncio

from ai_backend.domain.agents.graph import start_graph


@router.post("/chat", response_model=V1ChatResponse)
def v1_chat(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ChatResponse:
    question = normalize_question(body.question)
    request_id = (body.request_id or x_request_id or "").strip()
    if not request_id:  # không tự tạo: web backend sinh ở biên và truyền xuống
        raise HTTPException(status_code=400, detail="Thiếu request_id (body hoặc header X-Request-Id)")
    chat_deps = {
        "price_source": deps.price_source,
        "news_source": deps.news_source,
        "history_store": deps.history_store,
        "memory_store": deps.memory_store,
        "watchlist_store": deps.watchlist_store,
    }

    async def _chat_result() -> Any:
        result = None
        async for kind, payload in start_graph(
            "chat", question, chat_deps, user_id=body.user_id, request_id=request_id
        ):
            if kind == "result":
                result = payload  # đọc hết generator: save_long_term_memory chạy sau result
        if result is None:
            raise RuntimeError("start_graph không yield result")
        return result

    final = asyncio.run(_chat_result())["final_answer"]
    return V1ChatResponse(
        answer=final.answer,
        question=final.question,
        request_id=request_id,
        drawed_paths=final.drawed_paths,
    )


@router.post("/chat/stream")
def v1_chat_stream(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> StreamingResponse:
    """SSE token của câu trả lời + payload cuối. Không ghi session — web tự lưu."""
    from ai_backend.infra.llm.chat_stream import swarm_sse

    request_deps = {
        "price_source": deps.price_source,
        "news_source": deps.news_source,
        "history_store": deps.history_store,
        "memory_store": deps.memory_store,
        "watchlist_store": deps.watchlist_store,
    }
    request_id = (body.request_id or x_request_id or "").strip()
    if not request_id:  # không tự tạo: web backend sinh ở biên và truyền xuống
        raise HTTPException(status_code=400, detail="Thiếu request_id (body hoặc header X-Request-Id)")
    return StreamingResponse(
        swarm_sse(normalize_question(body.question), request_deps, user_id=body.user_id, request_id=request_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/scan", response_model=V1ScanResponse)
def v1_scan(
    body: V1ScanRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ScanResponse:
    sym = normalize_symbol(body.symbol)
    threshold = validate_threshold_pct(body.threshold_pct)
    request_id = (body.request_id or x_request_id or "").strip()
    if not request_id:  # không tự tạo: web backend sinh ở biên và truyền xuống
        raise HTTPException(status_code=400, detail="Thiếu request_id (body hoặc header X-Request-Id)")
    watchlist_store, _account_holdings = _lists_from_body(body)
    scan_deps = {
        "price_source": deps.price_source,
        "news_source": deps.news_source,
        "history_store": deps.history_store,
        "memory_store": deps.memory_store,
        "notifier": deps.notifier,
        "threshold_pct": threshold,
        "watchlist_store": watchlist_store,
    }

    async def _scan_result() -> Any:
        async for kind, payload in start_graph(
            "scan", sym, scan_deps, user_id=body.user_id, request_id=request_id
        ):
            if kind == "result":
                return payload
        raise RuntimeError("start_graph không yield result")

    from ai_backend.domain.agents.scan.nodes import DEFAULT_THRESHOLD_PCT
    from ai_backend.domain.agents.scan.state import main_item

    state = asyncio.run(_scan_result())
    routing = state["event_routing"]
    route_val = routing.route if routing is not None else ""
    reason_val = routing.reason if routing is not None else ""
    symbols = state["symbols"]
    sym_out = symbols[0] if symbols else sym
    pct = state["threshold_pct"]
    threshold_out = pct if pct is not None else DEFAULT_THRESHOLD_PCT
    status = "pending_approval" if state["pending_tool_call"] else "done"
    prices = state["prices"] or []
    p = main_item(prices, state) if prices else None
    price_payload = (
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
    news_rows = list(news.items) if news and news.items else []
    news_items = [
        {
            "title": i.title,
            "url": i.url,
            "published_at": i.published_at,
            "snippet": i.snippet,
        }
        for i in news_rows
    ]
    ev = state["eval_result"]
    alert = state["alert"]
    return V1ScanResponse(
        symbol=sym_out,
        route=str(getattr(route_val, "value", route_val)),
        reason=reason_val or "",
        threshold_pct=threshold_out,
        status=status,
        thread_id=state["thread_id"] or "",
        tool_call=state["pending_tool_call"],
        request_id=request_id,
        price=price_payload,
        news_count=len(news_items),
        news=news_items,
        news_error=news.error if news is not None else None,
        severity=ev.severity.model_dump(mode="json") if ev is not None else None,
        alert=alert.model_dump(mode="json") if alert is not None else None,
    )
