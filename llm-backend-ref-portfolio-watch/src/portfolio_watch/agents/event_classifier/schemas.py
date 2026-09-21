"""I/O event_classifier — normal vs abnormal routing."""

from __future__ import annotations

from typing import Protocol

from src.portfolio_watch.agents.news_agent import NewsAgentResult
from src.portfolio_watch.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import RoutingDecision


class EventClassifierBrain(Protocol):
    def classify(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        threshold_pct: float,
    ) -> RoutingDecision:
        ...
