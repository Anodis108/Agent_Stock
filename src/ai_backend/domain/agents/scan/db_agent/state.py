"""State worker db_agent = WorkerState + artifact DBAgentResult."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState


class DBAgentResult(BaseModel):
    user_id: str = "default"
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    watchlist: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class DBWorkerState(WorkerState, total=False):
    user_id: str  # read_user_portfolio đọc qua InjectedState
    db_results: DBAgentResult | None
