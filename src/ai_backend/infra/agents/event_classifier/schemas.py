"""I/O event_classifier — normal vs abnormal routing + Pydantic schemas."""

from __future__ import annotations

from typing import Protocol

from ai_backend.infra.agents.news_agent import NewsAgentResult
from ai_backend.infra.agents.price_agent import PriceAgentResult
from common.domain.entities import RoutingDecision
from common.transport.schemas import ClassifierOutput


class EventClassifierBrain(Protocol):
    def classify(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        threshold_pct: float,
    ) -> RoutingDecision:
        ...


__all__ = [
    "ClassifierOutput",
    "EventClassifierBrain",
]
