"""Re-export eval_agent — legacy path (Phase 12d)."""

from src.portfolio_watch.agents.eval_agent import (
    EvalAgentBrain,
    EvalAgentResult,
    HeuristicEvalBrain,
    LlmEvalBrain,
    _DEFAULT_EVAL_BRAIN_FACTORY,
    read_price_history,
    run_eval_agent,
)

__all__ = [
    "EvalAgentBrain",
    "EvalAgentResult",
    "HeuristicEvalBrain",
    "LlmEvalBrain",
    "_DEFAULT_EVAL_BRAIN_FACTORY",
    "read_price_history",
    "run_eval_agent",
]
