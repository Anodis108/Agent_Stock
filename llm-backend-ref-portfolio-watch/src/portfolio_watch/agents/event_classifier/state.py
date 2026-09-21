"""EventClassifierState — TypedDict cho graph (Phase 13)."""

from __future__ import annotations

from typing import TypedDict

from src.portfolio_watch.domain.entities import RoutingDecision


class EventClassifierState(TypedDict, total=False):
    threshold_pct: float
    decision: RoutingDecision
