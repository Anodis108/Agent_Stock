"""AI service internal API — /v1/chat, /v1/scan (+ health trên ai_main)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from src.portfolio_watch.api.deps import AppDeps, get_app_deps
from src.portfolio_watch.api.helpers.validation import (
    normalize_question,
    normalize_symbol,
    validate_threshold_pct,
)
from src.portfolio_watch.api.routers.chat import ChatStep
from src.portfolio_watch.application.answer_question import answer_question
from src.portfolio_watch.application.scan_symbol import ScanSymbolResult, scan_symbol

router = APIRouter(prefix="/v1", tags=["ai-v1"])


class V1ChatRequest(BaseModel):
    question: str
    user_id: str = "default"
    request_id: str | None = None


class V1ChatResponse(BaseModel):
    answer: str
    steps: list[ChatStep] = Field(default_factory=list)
    question: str = ""
    symbol: str | None = None
    route: str = ""
    error: str | None = None
    request_id: str | None = None
    # extras hữu ích cho Backend proxy
    rewritten: str = ""
    agents_to_call: list[str] = Field(default_factory=list)
    price: dict[str, Any] | None = None
    news_count: int = 0
    severity: dict[str, Any] | None = None


class V1ScanRequest(BaseModel):
    symbol: str
    user_id: str = "default"
    threshold_pct: float | None = None
    request_id: str | None = None


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


def build_scan_steps(result: ScanSymbolResult) -> list[dict]:
    """Timeline tối thiểu cho luồng scan (id/name/status/detail)."""
    steps: list[dict] = []
    n = 1

    def add(name: str, status: str, detail: str | None = None) -> None:
        nonlocal n
        steps.append(
            {"id": str(n), "name": name, "status": status, "detail": detail}
        )
        n += 1

    p = result.price
    add(
        "price_agent",
        "error" if p.error else "done",
        f"{p.symbol} close={p.latest_close} chg={p.change_pct}"
        + (f" err={p.error}" if p.error else ""),
    )
    news = result.news
    add(
        "news_agent",
        "error" if news.error else "done",
        f"items={len(news.items or [])}"
        + (f" err={news.error}" if news.error else ""),
    )
    route = str(getattr(result.routing.route, "value", result.routing.route))
    add(
        "event_classifier",
        "done",
        f"{route}"
        + (f" — {result.routing.reason}" if result.routing.reason else ""),
    )
    if result.severity is not None:
        add("eval_agent", "done", str(result.severity))
    if result.alert is not None:
        add("synthesis_agent", "done", "alert composed")
    if result.gate1_action:
        add("confidence_gate", "done", f"action={result.gate1_action}")
    if result.error:
        add("scan", "error", result.error)
    return steps


@router.post("/chat", response_model=V1ChatResponse)
def v1_chat(
    body: V1ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> V1ChatResponse:
    question = normalize_question(body.question)
    request_id = (body.request_id or x_request_id or "").strip() or None
    result = answer_question(
        question,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        user_id=body.user_id,
        request_id=request_id,
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
    result = scan_symbol(
        symbol,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        notifier=deps.notifier,
        watchlist_store=deps.watchlist_store,
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
        steps=[ChatStep.model_validate(s) for s in build_scan_steps(result)],
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
