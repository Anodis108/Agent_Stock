"""State worker price_agent = WorkerState + artifact PriceAgentResult."""

from __future__ import annotations

from pydantic import BaseModel

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState


class PriceAgentResult(BaseModel):
    symbol: str
    latest_close: float | None
    prev_close: float | None
    change_pct: float | None
    error: str | None = None


class PriceWorkerState(WorkerState, total=False):
    symbols: list[str]
    prices: list[PriceAgentResult]
