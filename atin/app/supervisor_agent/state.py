"""SupervisorState — blackboard hub (1 worker, không Send/plan)."""

from __future__ import annotations

from typing import TypedDict

from app.stat_agent.schemas import Agent_Output as StatOut
from app.supervisor_agent.schemas import Agent_Output


class SupervisorState(TypedDict, total=False):
    question: str
    out_of_scope: bool
    stat: StatOut
    output: Agent_Output
    output_issues: list[str]
