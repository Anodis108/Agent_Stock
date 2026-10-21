"""Shared graph state types — Phase 13."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from ai_backend.infra.agents.chat.answer_composer import AnswerComposeResult
from ai_backend.infra.agents.chat.diagram_agent.nodes import DiagramAgentResult
from ai_backend.infra.agents.scan.eval_agent import EvalAgentResult
from ai_backend.infra.agents.scan.news_agent import NewsAgentResult
from ai_backend.infra.agents.scan.price_agent import PriceAgentResult
from ai_backend.infra.agents.chat.supervisor_agent import RewrittenQuestion
from common.domain.entities import FinalAlert, RoutingDecision, Severity


class SwarmState(TypedDict, total=False):
    """State chung của Hierarchical Swarm Graph (cả team chat lẫn team scan)."""

    # --- Điều phối phân cấp ---
    mode: Literal["chat", "scan"]  # top_supervisor giao việc cho team nào
    next: list[str]  # team supervisor quyết định (các) worker kế tiếp
    completed: Annotated[list[str], operator.add]  # worker đã chạy xong (worker song song cùng ghi)
    gather_request: list[str]  # chat_supervisor nhờ scan_supervisor lấy dữ liệu (price_agent / news_agent)

    # --- Dùng chung ---
    user_id: str
    turn: str
    symbol: str | None
    symbols: list[str]
    price: PriceAgentResult | None
    news: NewsAgentResult | None
    prices: list[PriceAgentResult]
    news_list: list[NewsAgentResult]
    eval_result: EvalAgentResult | None
    error: str | None

    # --- Team chat ---
    question: str
    conversation: list[dict[str, Any]]
    memories: list[str]
    guardrail_result: Any | None
    rewritten: RewrittenQuestion
    routing: RoutingDecision  # kế hoạch gọi worker do chat_supervisor lập
    diagram_result: DiagramAgentResult | None
    chart_result: Any | None
    chart_path: str | None
    portfolio_summary: Any | None
    portfolio_watch_result: Any | None
    watchlist_items: list[Any] | None
    compose: AnswerComposeResult | None
    answer: str
    source_file: str | None
    concept_answer: str | None  # đoạn khái niệm concept_retrieval tìm được
    answer_kind: str  # refusal | greeting | concept | diagram | portfolio | composed
    answer_model: str
    answer_evidence: list[str]
    answer_attempts: int  # số lượt answer đã soạn (guardrail_output có thể yêu cầu soạn lại)
    guardrail_violations: list[str]
    last_grounded: str  # bản nháp gần nhất còn giữ số liệu evidence (dùng khi viết lại an toàn)
    steps: list[dict[str, Any]]

    # --- Team scan ---
    threshold_pct: float
    event_routing: RoutingDecision  # kết quả event_classifier (normal / abnormal)
    severity: Severity | None
    alert: FinalAlert | None
    gate1_action: str | None
    gate2_pending: bool
    pending_events: list[dict[str, Any]]


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

