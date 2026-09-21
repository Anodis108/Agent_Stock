"""Re-export supervisor_agent — legacy path (Phase 12f)."""

from src.portfolio_watch.agents.supervisor_agent import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    LlmRewriteBrain,
    LlmSupervisorBrain,
    RewriteBrain,
    RewrittenQuestion,
    SupervisorBrain,
    _DEFAULT_REWRITE_FACTORY,
    _DEFAULT_SUPERVISOR_FACTORY,
    _extract_symbols,
    rewrite_question,
    route_question,
)

__all__ = [
    "HeuristicRewriteBrain",
    "HeuristicSupervisorBrain",
    "LlmRewriteBrain",
    "LlmSupervisorBrain",
    "RewriteBrain",
    "RewrittenQuestion",
    "SupervisorBrain",
    "_DEFAULT_REWRITE_FACTORY",
    "_DEFAULT_SUPERVISOR_FACTORY",
    "_extract_symbols",
    "rewrite_question",
    "route_question",
]
