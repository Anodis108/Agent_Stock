"""SynthState — một node `compose` ghi `result`."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.synthesis_agent.schemas import Agent_Output


class SynthState(TypedDict, total=False):
    price: PriceOut
    news: NewsOut
    eval: EvalOut
    db: DbOut
    n_history: int
    result: Agent_Output                  # pack từ tool compose_user_answer
    messages: Annotated[list, add_messages]
    _trace_span: Any                      # span cha từ hub
