"""synthesis_agent — alert + guardrail loop."""

from src.portfolio_watch.agents.synthesis_agent.nodes import (
    MAX_DRAFT_ATTEMPTS,
    MODEL_HEAVY,
    MODEL_LIGHT,
    AlertComposer,
    HeuristicAlertComposer,
    LlmAlertComposer,
    SynthesisResult,
    _DEFAULT_COMPOSER_FACTORY,
    run_synthesis_agent,
    select_model,
)

__all__ = [
    "MAX_DRAFT_ATTEMPTS",
    "MODEL_HEAVY",
    "MODEL_LIGHT",
    "AlertComposer",
    "HeuristicAlertComposer",
    "LlmAlertComposer",
    "SynthesisResult",
    "_DEFAULT_COMPOSER_FACTORY",
    "run_synthesis_agent",
    "select_model",
]
