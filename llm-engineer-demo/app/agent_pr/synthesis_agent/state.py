"""SynthState — một node `compose` ghi `result`."""

from __future__ import annotations

from typing import Annotated, TypedDict

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
    question: str                      # câu user — subgraph copy từ hub
    rewritten_question: str            # rewrite; compose ưu tiên
    n_history: int
    result: Agent_Output                  # pack từ tool compose_user_answer
    draft: Agent_Output                   # cùng result — tên field hub
    turn: str
    synth_turn: str
    messages: Annotated[list, add_messages]
