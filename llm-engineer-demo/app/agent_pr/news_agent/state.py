"""NewsState — bảng dữ liệu chung của graph news_agent.

State chảy qua 3 node: normalize → fetch → parse. Mỗi node nhận state, trả
partial dict; LangGraph merge (giống CrawlState / GraphState ở app/agent).

Khác app/agent: không Send/fan-out, không reducer. Tuyến tính — mỗi field
một node ghi. Khác craw_agent: rows là tin (title/url/time), không phải OHLCV.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from app.agent_pr.news_agent.schemas import Agent_Output


class NewsState(TypedDict, total=False):
    """State xuyên suốt graph lấy tin.

    total=False: node chỉ trả field nó cập nhật (normalize → symbol; fetch → rows).
    """

    symbol: str                    # mã đã upper + đúng định dạng (normalize ghi)
    turn: str                      # uuid HTTP từ hub Send — key span "news_agent" (xem tracing.agent_span)
    rows: list[dict[str, Any]]     # [{title, url, publish_time}, ...] từ CafeF News.ashx
    news: Agent_Output             # pack ghi từ tool fetch_cafef_news
    error: str                     # fetch ghi khi CafeF lỗi — parse đưa vào source
    messages: Annotated[list, add_messages]
