"""DBState — bảng dữ liệu chung của graph db_agent.

State chảy qua: normalize → read → (stage_writes?) → parse.

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

    symbol: str
    mode: str                          # read | write — hub ghi, lift phân turn
    candidate_news: list[CandidateNews]
    candidate_prices: list[CandidatePrice]
    price_rows: list[dict[str, Any]]
    news_rows: list[dict[str, Any]]
    pending_rows: list[dict[str, Any]]
    result: Agent_Output
    messages: Annotated[list, add_messages]
    _trace_span: Any
