"""Hợp đồng HTTP của image AI. Không import router web."""

from __future__ import annotations

import json
import threading
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.deps import AppDeps, get_app_deps
from backend.api.helpers.validation import (
    normalize_question,
    normalize_symbol,
    validate_threshold_pct,
)
from backend.application.answer_question import answer_question
from backend.application.scan_symbol import scan_symbol
from backend.domain.entities import WatchlistItem
from backend.infra.llm.account_snapshot import SnapshotWatchlistStore

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


def _dispatch_answer_question(*args: Any, **kwargs: Any) -> Any:
    import sys

    routes_mod = sys.modules.get("backend.api.routers.ai.v1") or sys.modules.get("backend.routes")
    fn = getattr(routes_mod, "answer_question", answer_question) if routes_mod else answer_question
    return fn(*args, **kwargs)


def _dispatch_scan_symbol(*args: Any, **kwargs: Any) -> Any:
    import sys

    routes_mod = sys.modules.get("backend.api.routers.ai.v1") or sys.modules.get("backend.routes")
    fn = getattr(routes_mod, "scan_symbol", scan_symbol) if routes_mod else scan_symbol
    return fn(*args, **kwargs)


@router.post("/chat", response_model=V1ChatResponse)
def v1_chat(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ChatResponse:
    question = normalize_question(body.question)
    request_id = (body.request_id or x_request_id or "").strip() or None
    watchlist_store, account_holdings = _lists_from_body(body)
    result = _dispatch_answer_question(
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
        from backend.infra.llm.chat_stream import iter_swarm_events

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
    symbol = normalize_symbol(body.symbol)
    thr = validate_threshold_pct(body.threshold_pct)
    request_id = (body.request_id or x_request_id or "").strip() or None
    watchlist_store, _holdings = _lists_from_body(body)
    result = _dispatch_scan_symbol(
        symbol,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        notifier=deps.notifier,
        watchlist_store=watchlist_store
        if watchlist_store is not None
        else deps.watchlist_store,
        user_id=body.user_id,
        threshold_pct=thr,
        request_id=request_id,
    )
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
    return V1ScanResponse(
        symbol=result.symbol,
        route=str(getattr(result.routing.route, "value", result.routing.route)),
        steps=[ChatStep.model_validate(s) for s in result.steps],
        reason=result.routing.reason or "",
        threshold_pct=result.threshold_pct,
        gate1_action=result.gate1_action,
        gate2_pending=result.gate2_pending,
        error=result.error,
        request_id=request_id,
        price={
            "symbol": p.symbol,
            "latest_close": p.latest_close,
            "prev_close": p.prev_close,
            "change_pct": p.change_pct,
            "error": p.error,
        },
        news_count=len(news_items),
        news=news_items,
        news_error=result.news.error,
        severity=(
            result.severity.model_dump(mode="json") if result.severity else None
        ),
        alert=(result.alert.model_dump(mode="json") if result.alert else None),
        pending_events=list(result.pending_events),
    )
