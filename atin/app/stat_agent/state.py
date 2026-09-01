"""StatState — state của graph stat_agent (seed → agent ⇄ tools → pack)."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.stat_agent.schemas import Agent_Output


class StatState(TypedDict, total=False):
    question: str
    result: Agent_Output
    stat: Agent_Output
    messages: Annotated[list, add_messages]
