"""DBState — bảng dữ liệu chung của graph db_agent.

Graph là ReAct chung (seed → agent ⇄ tools → pack, xem react.py), không phải
graph tuyến tính — tool `read_symbol_store`/`stage_new_rows` (tools.py) tự gọi
thẳng `read`/`stage_writes`/`parse` (nodes.py) theo đúng thứ tự, không đi qua
`normalize` (mã đã upper/strip ngay khi tool nhận input).

HITL không còn trong graph này. Hub interrupt_before=["hitl_commit"] sau synth.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from app.agent_pr.db_agent.schemas import Agent_Output, CandidateNews, CandidatePrice


class DBState(TypedDict, total=False):
    """State xuyên suốt graph đọc/soạn-ghi DB.

    total=False: node chỉ trả field nó cập nhật.
    """

    symbol: str                        # mã đã upper/strip — tool tự normalize khi nhận input
    mode: str                          # read | write — hub ghi, lift phân turn
    candidate_news: list[CandidateNews]    # tin PriceAgent/NewsAgent vừa crawl, đưa `stage_writes` xét soạn ghi
    candidate_prices: list[CandidatePrice]  # phiên giá vừa crawl, đưa `stage_writes` xét soạn ghi
    price_rows: list[dict[str, Any]]   # `read` đọc từ bảng `prices` — parse dựng PriceRow
    news_rows: list[dict[str, Any]]    # `read` đọc từ bảng `news` — parse dựng SavedNews
    pending_rows: list[dict[str, Any]] # `stage_writes` ghi — lệnh vừa soạn vào *_pending, parse dựng PendingWrite
    result: Agent_Output               # `parse` ghi — output graph
    db: Agent_Output                   # cùng result — tên field hub
    turn: str                          # uuid HTTP từ hub Send — pack ghi *_turn
    db_lookup_turn: str                # pack ghi khi mode=read — đánh dấu đã lookup đúng turn này
    db_write_turn: str                 # pack ghi khi mode=write — đánh dấu đã soạn ghi đúng turn này
    messages: Annotated[list, add_messages]  # ReAct LLM ⇄ ToolNode
