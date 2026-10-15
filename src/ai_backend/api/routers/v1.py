"""Hợp đồng HTTP v1 của AI Backend Microservice (/v1/chat, /v1/chat/stream, /v1/scan)."""

from __future__ import annotations

import json
import threading
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_backend.infra.llm.account_snapshot import SnapshotWatchlistStore
from ai_backend.infra.market_data.price_source import VnstockPriceSource
from ai_backend.infra.market_data.news_source import CafefNewsSource
from ai_backend.infra.storage.memory_store import SqliteMemoryStore
from ai_backend.infra.storage.price_history_store import SqlitePriceHistoryStore
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
    user_id: str = "default"


class HoldingSnapshot(BaseModel):
    symbol: str
    quantity: float
    avg_buy_price: float
    user_id: str = "default"


class V1ChatRequest(BaseModel):
    question: str
    user_id: str = "default"
    request_id: str | None = None
    watchlist: list[WatchlistSnapshot] | None = None
    holdings: list[HoldingSnapshot] | None = None


class V1ChatResponse(BaseModel):
    answer: str
    steps: list[ChatStep] = Field(default_factory=list)
    question: str = ""
    symbol: str | None = None
    route: str = ""
    error: str | None = None
    request_id: str | None = None
    rewritten: str = ""
    agents_to_call: list[str] = Field(default_factory=list)
    price: dict[str, Any] | None = None
    news_count: int = 0
    severity: dict[str, Any] | None = None
    source_file: str | None = None


class V1ScanRequest(BaseModel):
    symbol: str
    user_id: str = "default"
    threshold_pct: float | None = None
    request_id: str | None = None
    watchlist: list[WatchlistSnapshot] | None = None
    holdings: list[HoldingSnapshot] | None = None


def _lists_from_body(body: V1ChatRequest | V1ScanRequest):
    """Payload có mặt thì dùng snapshot. Không có thì AI giữ đường cũ."""
    sent = body.model_fields_set
    if "watchlist" not in sent and "holdings" not in sent:
        return None, None
    items = [
        WatchlistItem(
            symbol=row.symbol.strip().upper(),
            threshold_pct=float(row.threshold_pct),
            user_id=(row.user_id or body.user_id or "default").strip() or "default",
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
    gate1_action: str | None = None
    gate2_pending: bool = False
    error: str | None = None
    request_id: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    pending_events: list[dict[str, Any]] = Field(default_factory=list)


try:
    from ai_backend.infra.graph.chat import answer_question
except ImportError:
    answer_question = None

try:
    from ai_backend.infra.graph.scan import scan_symbol
except ImportError:
    scan_symbol = None


@router.post("/chat", response_model=V1ChatResponse)
def v1_chat(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ChatResponse:
    question = normalize_question(body.question)
    request_id = (body.request_id or x_request_id or "").strip() or None
    watchlist_store, account_holdings = _lists_from_body(body)
    result = answer_question(
        question,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        user_id=body.user_id,
        request_id=request_id,
        watchlist_store=watchlist_store,
        account_holdings=account_holdings,
    )
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
    return V1ChatResponse(
        answer=result.answer,
        steps=[ChatStep.model_validate(s) for s in (result.steps or [])],
        question=result.question,
        symbol=result.rewritten.symbol,
        route=str(getattr(result.routing.route, "value", result.routing.route)),
        error=result.error,
        request_id=request_id,
        rewritten=result.rewritten.rewritten,
        agents_to_call=list(result.routing.agents_to_call or []),
        price=price_payload,
        news_count=len(result.news.items) if result.news else 0,
        severity=severity,
        source_file=getattr(result, "source_file", None),
    )


@router.post("/chat/stream")
def v1_chat_stream(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> StreamingResponse:
    """SSE token và tiến trình agent. Không ghi session — web tự lưu."""
    question = normalize_question(body.question)
    request_id = (body.request_id or x_request_id or "").strip() or None
    watchlist_store, account_holdings = _lists_from_body(body)
    cancel = threading.Event()

    def _gen():
        from ai_backend.infra.llm.chat_stream import iter_swarm_events

        events = iter_swarm_events(
            question,
            deps,
            user_id=body.user_id,
            request_id=request_id,
            cancel_event=cancel,
            watchlist_store=watchlist_store,
            account_holdings=account_holdings,
        )
        try:
            for event, data in events:
                if request_id and event in ("final_answer", "complete"):
                    data = {**data, "request_id": request_id}
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            cancel.set()
            if hasattr(events, "close"):
                events.close()

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/scan", response_model=V1ScanResponse)
def v1_scan(
    body: V1ScanRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ScanResponse:
    sym = normalize_symbol(body.symbol)
    threshold = validate_threshold_pct(body.threshold_pct)
    request_id = (body.request_id or x_request_id or "").strip() or None
    watchlist_store, account_holdings = _lists_from_body(body)
    result = scan_symbol(
        sym,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        user_id=body.user_id,
        threshold_pct=threshold,
        request_id=request_id,
        watchlist_store=watchlist_store,
        account_holdings=account_holdings,
    )

    news_items = (
        [
            {
                "title": i.title,
                "url": i.url,
                "published_at": i.published_at,
                "snippet": i.snippet,
            }
            for i in result.news.items
        ]
        if result.news and getattr(result.news, "items", None)
        else []
    )
    p = result.price
    price_payload = (
        {
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        }
        if p
        else None
    )
    routing = getattr(result, "routing", None)
    route_val = getattr(routing, "route", getattr(result, "route", "")) if routing else getattr(result, "route", "")
    reason_val = getattr(routing, "reason", getattr(result, "reason", "")) if routing else getattr(result, "reason", "")
    severity = getattr(result, "severity", None)
    if severity is None and hasattr(result, "eval_result") and result.eval_result is not None:
        severity = getattr(result.eval_result, "severity", None)
    if severity is not None and hasattr(severity, "model_dump"):
        severity = severity.model_dump(mode="json")
    alert = getattr(result, "alert", None)
    if alert is None and hasattr(result, "synthesis_alert") and result.synthesis_alert is not None:
        alert = result.synthesis_alert
    if alert is not None and hasattr(alert, "model_dump"):
        alert = alert.model_dump(mode="json")
    pending_events = [
        e.model_dump(mode="json") if hasattr(e, "model_dump") else e
        for e in (getattr(result, "pending_events", []) or [])
    ]
    return V1ScanResponse(
        symbol=result.symbol,
        route=str(getattr(route_val, "value", route_val)),
        steps=[ChatStep.model_validate(s) for s in (result.steps or [])],
        reason=reason_val or "",
        threshold_pct=result.threshold_pct,
        gate1_action=str(getattr(result.gate1_action, "value", result.gate1_action)) if result.gate1_action else None,
        gate2_pending=getattr(result, "gate2_pending", False),
        error=result.error,
        request_id=getattr(result, "request_id", None) or request_id,
        price=price_payload,
        news_count=len(news_items),
        news=news_items,
        news_error=getattr(result.news, "error", None) if result.news else None,
        severity=severity,
        alert=alert,
        pending_events=pending_events,
    )
