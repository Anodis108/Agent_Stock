"""Hợp đồng vào/ra hub."""

from __future__ import annotations

from pydantic import BaseModel

from app.stat_agent.schemas import Agent_Output as StatOut


class Agent_Input(BaseModel):
    question: str
    thread_id: str = ""


class Agent_Output(BaseModel):
    question: str
    answer: str
    stat: StatOut | None = None
    thread_id: str = ""
