"""Shared graph state types — Phase 13."""

from __future__ import annotations

from typing import Any, TypedDict

from src.portfolio_watch.domain.agents.answer_composer import AnswerComposeResult
from src.portfolio_watch.domain.agents.eval_agent import EvalAgentResult
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.agents.supervisor import RewrittenQuestion
from src.portfolio_watch.domain.entities import FinalAlert, RoutingDecision, Severity


class ChatState(TypedDict, total=False):
    question: str
    user_id: str
    turn: str
    conversation: list[dict[str, Any]]
    rewritten: RewrittenQuestion
    routing: RoutingDecision
    symbol: str | None
    symbols: list[str]
    price: PriceAgentResult | None
    news: NewsAgentResult | None
    prices: list[PriceAgentResult]
    news_list: list[NewsAgentResult]
    eval_result: EvalAgentResult | None
    compose: AnswerComposeResult | None
    answer: str
    error: str | None
    steps: list[dict[str, Any]]


class ScanState(TypedDict, total=False):
    symbol: str
    user_id: str
    turn: str
    threshold_pct: float
    price: PriceAgentResult
    news: NewsAgentResult
    routing: RoutingDecision
    severity: Severity | None
    eval_result: EvalAgentResult | None
    alert: FinalAlert | None
    gate1_action: str | None
    gate2_pending: bool
    pending_events: list[dict[str, Any]]
    error: str | None
