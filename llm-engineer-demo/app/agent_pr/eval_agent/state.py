"""EvalState — bảng chung graph eval.

Khác craw/news: không `rows` mạng. Input đã là 2 model; node `score` ghi `report`.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class EvalState(TypedDict, total=False):
    """total=False: node chỉ trả field nó cập nhật (`report`)."""

    price: PriceOut                # run_eval đưa vào
    news: NewsOut                  # run_eval đưa vào
    report: Agent_Output           # score ghi; run_eval lấy field này
    _trace_span: Any               # span cha từ hub (trùng tên SupervisorState)
