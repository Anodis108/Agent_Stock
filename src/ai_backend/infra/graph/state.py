"""Shared graph state types — Phase 13."""

from __future__ import annotations

from typing import Any, TypedDict

from ai_backend.infra.agents.answer_composer import AnswerComposeResult
from ai_backend.infra.agents.diagram_agent.nodes import DiagramAgentResult
from ai_backend.infra.agents.eval_agent import EvalAgentResult
from ai_backend.infra.agents.news_agent import NewsAgentResult
from ai_backend.infra.agents.price_agent import PriceAgentResult
from ai_backend.infra.agents.supervisor_agent import RewrittenQuestion
from common.domain.entities import FinalAlert, RoutingDecision, Severity


class ChatState(TypedDict, total=False):
    question: str
    user_id: str
    turn: str
    conversation: list[dict[str, Any]]
    memories: list[str]
    guardrail_result: Any | None
    rewritten: RewrittenQuestion
    routing: RoutingDecision
    symbol: str | None
    symbols: list[str]
    price: PriceAgentResult | None
    news: NewsAgentResult | None
    prices: list[PriceAgentResult]
    news_list: list[NewsAgentResult]
    eval_result: EvalAgentResult | None
    diagram_result: DiagramAgentResult | None
    chart_result: Any | None
    chart_path: str | None
    portfolio_summary: Any | None
    portfolio_watch_result: Any | None
    watchlist_items: list[Any] | None
    compose: AnswerComposeResult | None
    answer: str
    error: str | None
    source_file: str | None
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


from dataclasses import dataclass, field


@dataclass(slots=True)
class AnswerQuestionResult:
    question: str
    rewritten: RewrittenQuestion
    routing: RoutingDecision
    answer: str
    price: PriceAgentResult | None = None
    news: NewsAgentResult | None = None
    eval_result: EvalAgentResult | None = None
    compose: AnswerComposeResult | None = None
    diagram_result: Any | None = None
    chart_result: Any | None = None
    chart_path: str | None = None
    hitl_used: bool = False
    pending_approvals_created: int = 0
    error: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    portfolio_watch_result: Any | None = None
    source_file: str | None = None

