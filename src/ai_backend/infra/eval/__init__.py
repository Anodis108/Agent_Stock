"""Eval adapters — scorers, dataset, gate policy, cache, agent metrics.

Import cụ thể: `infra.eval.scorers`, `infra.eval.gate`, `infra.eval.agent_scorers`.
Application orchestration: `application.eval.runner`, `application.eval.run`.
"""

from ai_backend.infra.eval.agent_scorers import (
    AgentEvalResult,
    TaskSuccessResult,
    TrajectoryResult,
    evaluate_run,
)
from ai_backend.infra.eval.gate import (
    GATES,
    GateCheck,
    GateResult,
    check_gates,
    load_gate_report,
)

__all__ = [
    "AgentEvalResult",
    "TaskSuccessResult",
    "TrajectoryResult",
    "evaluate_run",
    "GATES",
    "GateCheck",
    "GateResult",
    "check_gates",
    "load_gate_report",
]
