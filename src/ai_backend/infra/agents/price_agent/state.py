"""PriceState — TypedDict cho graph (Phase 13)."""

from __future__ import annotations

from typing import TypedDict

from ai_backend.infra.agents.price_agent.schemas import PriceAgentResult


class PriceState(TypedDict, total=False):
    symbol: str
    result: PriceAgentResult
