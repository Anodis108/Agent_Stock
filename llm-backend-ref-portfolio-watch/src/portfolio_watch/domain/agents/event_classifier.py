"""Re-export event_classifier — legacy path (Phase 12c)."""

from src.portfolio_watch.agents.event_classifier import (
    EventClassifierBrain,
    HeuristicEventClassifier,
    LlmEventClassifier,
    _DEFAULT_BRAIN_FACTORY,
    classify_event,
)

__all__ = [
    "EventClassifierBrain",
    "HeuristicEventClassifier",
    "LlmEventClassifier",
    "_DEFAULT_BRAIN_FACTORY",
    "classify_event",
]
