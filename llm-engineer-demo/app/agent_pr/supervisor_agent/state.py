"""SupervisorState — bảng chung. Worker ghi từng field; assemble đọc hết.

Không reducer/Send: gather tự asyncio.gather, không fan-out LangGraph.
"""

from __future__ import annotations

from typing import TypedDict

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.schemas import Agent_Output


class SupervisorState(TypedDict, total=False):
    """total=False: mỗi node chỉ trả phần nó ghi."""

    symbol: str                    # normalize
    price: PriceOut                # gather
    news: NewsOut                  # gather
    eval: EvalOut                  # evaluate
    result: Agent_Output           # assemble — run_supervisor lấy field này
