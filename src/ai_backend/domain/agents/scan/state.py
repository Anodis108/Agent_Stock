"""State team scan + ScanSymbolResult. Artifact từng worker → `<agent>/state.py`."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field

from ai_backend.domain.agents.multi_agent.hierarchical import HierarchicalState
from ai_backend.domain.agents.scan.db_agent.state import DBAgentResult
from ai_backend.domain.agents.scan.eval_agent.state import EvalAgentResult
from ai_backend.domain.agents.scan.news_agent.state import NewsAgentResult
from ai_backend.domain.agents.scan.price_agent.state import PriceAgentResult
from ai_backend.domain.agents.state import AssistantState
from common.domain.entities import FinalAlert, RoutingDecision

__all__ = [
    "DBAgentResult",
    "EvalAgentResult",
    "NewsAgentResult",
    "PriceAgentResult",
    "ScanHierarchicalState",
    "ScanSymbolResult",
    "main_item",
]


class ScanSymbolResult(BaseModel):
    """Kết quả 1 lần quét (run_graph / resume_graph) → ScanService / API."""

    symbol: list[str]
    price: list[PriceAgentResult] = Field(default_factory=list)
    news: list[NewsAgentResult] = Field(default_factory=list)
    routing: Any
    threshold_pct: float
    severity: Any | None = None
    alert: Any | None = None
    status: str = "done"  # done | pending_approval (graph dừng trước scan_tools)
    thread_id: str = ""  # checkpointer thread — dùng để resume
    tool_call: dict | None = None  # hành động chờ duyệt {id, name, args}
    error: str | None = None
    steps: list[dict] = Field(default_factory=list)


def main_item(items: list, state: dict[str, Any]) -> Any:
    """Phần tử (PriceAgentResult / NewsAgentResult) của mã chính symbols[0]; không có thì phần tử đầu."""
    main = (state.get("symbols") or [""])[0].upper()
    return next((x for x in items if (x.symbol or "").upper() == main), items[0] if items else None)


# ── State ────────────────────────────────────────────────────────────────────


class ScanHierarchicalState(AssistantState, HierarchicalState, total=False):
    # AssistantState (graph gốc): messages, user_id, mode, request_id — trùng tên nên LangGraph truyền qua lại
    #   khi nhúng subgraph. messages: HumanMessage đầu vào (mã cần quét) + HITL (như llm-engineer-demo):
    #   AIMessage(tool_calls) = hành động đề xuất chờ duyệt, ToolMessage = kết quả scan_tools hoặc lời từ chối.
    # HierarchicalState (hierarchical.py): task, result, notes, next_agent (+ final_answer, scan không dùng).

    completed_workers: Annotated[list[str], operator.add]  # worker đã chạy xong (đồng bộ ngược sang chat)
    symbols: list[str]  # cả danh sách mã của lượt, nhận từ ScanService
    event_routings: list[RoutingDecision]  # cùng thứ tự với symbols
    alerts: list[FinalAlert]
    eval_results: list[EvalAgentResult]
    threshold_pct: float  # optional trong lượt quét — ngưỡng nằm trong ``task``; API fill lúc kết thúc
    prices: list[PriceAgentResult]
    news: list[NewsAgentResult]
    eval_result: EvalAgentResult | None
    db_results: DBAgentResult | None  # holdings + watchlist (chat → portfolio_report)
    
    event_routing: RoutingDecision  # kết quả event_classifier (normal / abnormal)
    alert: FinalAlert | None
