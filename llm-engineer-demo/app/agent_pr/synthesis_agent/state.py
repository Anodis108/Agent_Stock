"""SynthState — một node `compose` ghi `result`."""

from __future__ import annotations

from typing import Any, TypedDict

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.synthesis_agent.schemas import Agent_Output


class SynthState(TypedDict, total=False):
    price: PriceOut
    news: NewsOut
    eval: EvalOut
    n_history: int
    result: Agent_Output                  # compose ghi; run_synthesis lấy field này
    _trace_span: Any                      # span cha từ hub
