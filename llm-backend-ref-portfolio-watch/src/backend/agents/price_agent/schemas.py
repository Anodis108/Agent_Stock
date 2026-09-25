"""I/O price_agent — không LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PriceAgentResult:
    symbol: str
    latest_close: float | None
    prev_close: float | None
    change_pct: float | None
    error: str | None = None
