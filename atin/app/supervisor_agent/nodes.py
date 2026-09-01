"""Nodes hub — 1 worker (stat_agent), không plan/Send."""

from __future__ import annotations

from app.stat_agent.graph import stat_agent as run_stat_agent
from app.supervisor_agent.schemas import Agent_Output
from app.supervisor_agent.state import SupervisorState


def stat_agent(state: SupervisorState) -> dict:
    return run_stat_agent(state)


def reply(state: SupervisorState) -> dict:
    question = str(state.get("question") or "")
    stat = state.get("stat")
    answer = stat.answer if stat else "Xin lỗi, chưa có kết quả."
    return {"output": Agent_Output(question=question, answer=answer, stat=stat)}
