"""EvalState — bảng chung graph eval.

Khác craw/news: không `rows` mạng. Input đã là 2 model; node `score` ghi `report`.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class EvalState(TypedDict, total=False):
    """total=False: node chỉ trả field nó cập nhật (`report`).

    LangGraph lọc input theo field khai báo ở đây trước khi gọi node — thiếu
    khai `symbol` thì `eval_agent()` (graph.py) nhận `state.get("symbol")`
    rỗng dù hub đã set đúng, dù type hint chỉ dùng cho runtime filtering chứ
    không static-check."""

    symbol: str                    # hub set mỗi vòng — wrapper eval_agent() đọc để tách đúng price/news theo mã
    price: PriceOut                # run_eval đưa vào
    news: NewsOut                  # run_eval đưa vào
    report: Agent_Output           # pack từ tool score_price_vs_news
    eval: Agent_Output             # cùng report — tên field hub
    turn: str                      # uuid HTTP từ hub Send — key span "eval_agent" (xem tracing.agent_span)
    eval_turn: str                 # pack ghi = turn vừa chấm xong; hub so với turn hiện tại để biết đã chấm lượt này chưa (tránh chấm lại)
    messages: Annotated[list, add_messages]  # ReAct LLM ⇄ ToolNode
