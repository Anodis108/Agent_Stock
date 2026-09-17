"""POST /chat — hỏi-đáp (không qua HITL)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.portfolio_watch.api.deps import AppDeps, get_app_deps
from src.portfolio_watch.api.helpers.validation import normalize_question
from src.portfolio_watch.application.answer_question import answer_question

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(description="Câu hỏi tự do")
    user_id: str = "default"


class ChatResponse(BaseModel):
    question: str
    rewritten: str
    symbol: str | None = None
    intent: str = ""
    agents_to_call: list[str] = Field(default_factory=list)
    route: str = ""
    reason: str = ""
    answer: str
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None


@router.post("/chat", response_model=ChatResponse)
def post_chat(
    body: ChatRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> ChatResponse:
    question = normalize_question(body.question)

    result = answer_question(
        question,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        user_id=body.user_id,
    )

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

    return ChatResponse(
        question=result.question,
        rewritten=result.rewritten.rewritten,
        symbol=result.rewritten.symbol,
        intent=result.rewritten.intent,
        agents_to_call=list(result.routing.agents_to_call or []),
        route=str(getattr(result.routing.route, "value", result.routing.route)),
        reason=result.routing.reason or "",
        answer=result.answer,
        hitl_used=result.hitl_used,
        pending_approvals_created=result.pending_approvals_created,
        error=result.error,
        price=price_payload,
        news_count=len(news_items),
        news=news_items,
        news_error=news_error,
        severity=severity,
    )
