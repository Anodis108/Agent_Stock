"""Eval use cases & CLI — golden runner, regression, reports.

Infra (scorers, dataset, gate policy, cache): `ai_backend.infra.eval`.
"""

from ai_backend.application.eval.agent_eval import (  # noqa: F401 — re-export shim
    AgentEvalSummary,
    CaseAgentEvalResult,
    export_eval_report,
    run_agent_eval,
)
from ai_backend.application.eval.gate import (
    GATES,
    GateCheck,
    GateResult,
    check_gates,
    load_gate_report,
)

__all__ = [
    "AgentEvalSummary",
    "CaseAgentEvalResult",
    "export_eval_report",
    "run_agent_eval",
    "GATES",
    "GateCheck",
    "GateResult",
    "check_gates",
    "load_gate_report",
]
