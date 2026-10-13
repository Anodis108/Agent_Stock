"""I/O event_classifier — normal vs abnormal routing + Pydantic schemas."""

from __future__ import annotations

from typing import Protocol

from backend.application.agents.news_agent import NewsAgentResult
from backend.application.agents.price_agent import PriceAgentResult
from backend.domain.entities import RoutingDecision
from backend.shared.schemas import ClassifierOutput


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
