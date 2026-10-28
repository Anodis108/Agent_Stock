"""State team chat — như scan/state.py: kế thừa AssistantState (graph gốc) + HierarchicalState (supervisor)."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from ai_backend.domain.agents.chat.draw_agent.state import DiagramAgentResult
from ai_backend.domain.agents.multi_agent.hierarchical import HierarchicalState
from ai_backend.domain.agents.scan.db_agent.state import DBAgentResult
from ai_backend.domain.agents.scan.eval_agent.state import EvalAgentResult
from ai_backend.domain.agents.scan.news_agent.state import NewAgentResult
from ai_backend.domain.agents.scan.price_agent.state import PriceAgentResult
from ai_backend.domain.agents.state import AssistantState
from common.domain.entities import RoutingDecision
from pydantic import BaseModel, Field


class AnswerComposeResult(BaseModel):
    """Kết quả guardrail đầu ra của câu trả lời (eval chấm groundedness theo evidence)."""

    evidence: list[str]
    guardrail_violations: list[str]
    draft_attempts: int


class RewrittenQuestion(BaseModel):
    original: str
    rewritten: str
    intent: str  # price_lookup | news_lookup | explain | chart | diagram
    symbols: list[str] = Field(default_factory=list)
    sub_questions: list[str] = Field(default_factory=list)

    @property
    def symbol(self) -> str | None:
        """Mã chính."""
        return self.symbols[0] if self.symbols else None


class AnswerQuestionResult(BaseModel):
    """Kết quả 1 lượt chat (run_graph mode=chat) → API / service / eval."""

    rewritten: RewrittenQuestion
    routing: RoutingDecision  # route = intent; agents_to_call = worker của chat đã chạy
    answer: str
    price: list[PriceAgentResult] = Field(default_factory=list)
    news: list[NewAgentResult] = Field(default_factory=list)
    eval_result: EvalAgentResult | None = None
    compose: AnswerComposeResult | None = None  # evidence + vi phạm guardrail (eval chấm)
    diagram_result: DiagramAgentResult | None = None
    chart_path: str | None = None
    source_file: str | None = None  # tài liệu concept_retrieval trích
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def question(self) -> str:
        return self.rewritten.original


class ChatTeamState(AssistantState, HierarchicalState, total=False):
    # AssistantState (graph gốc): messages, user_id, mode, request_id
    # HierarchicalState (supervisor): task, result, notes, next_agent, final_answer
    completed_workers: Annotated[list[str], operator.add]
    error: str | None

    # Đầu vào lượt chat (guardrail_input / rewrite_question ghi)
    question: str
    memories: list[str]  # memory dài hạn recall được (rewrite_question)
    guardrail_result: Any | None
    rewritten: RewrittenQuestion
    symbols: list[str]

    # Kết quả worker (trùng tên ScanHierarchicalState / DrawWorkerState → LangGraph truyền qua)
    prices: list[PriceAgentResult]
    news: list[NewAgentResult]
    eval_result: EvalAgentResult | None
    db_results: DBAgentResult | None
    chart_result: Any | None  # ChartResult (url khi success)
    diagram_result: DiagramAgentResult | None
    portfolio_watch_result: dict[str, Any] | None
    concept_answer: str | None
    source_file: str | None

    # Đầu ra (answer)
    answer: str
    answer_kind: str  # refusal | greeting | concept | diagram | portfolio | composed
    answer_evidence: list[str]  # dữ kiện được phép dùng (guardrail_output đối chiếu)
    answer_attempts: int  # số lượt answer đã soạn
    guardrail_violations: list[str]  # vi phạm lượt trước → answer soạn lại tránh
    last_grounded: str  # bản nháp gần nhất còn giữ số liệu evidence (viết lại an toàn)
