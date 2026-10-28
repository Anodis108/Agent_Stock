"""State worker eval_agent = WorkerState + artifact EvalAgentResult."""

from __future__ import annotations

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState
from common.domain.entities import Severity


class EvalAgentResult(BaseModel):
    severity: Severity


class EvalWorkerState(WorkerState, total=False):
    user_id: str  # propose_watchlist_update đọc qua InjectedState
    eval_result: EvalAgentResult | None
    messages: Annotated[list, add_messages]  # trùng `messages` team: đề xuất HITL update_watchlist (chờ duyệt ở scan_tools)
