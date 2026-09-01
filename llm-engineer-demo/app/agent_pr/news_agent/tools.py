"""Tools NewsAgent — CafeF Ajax. Parse/fetch thật ở nodes.py."""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent_pr.news_agent.nodes import fetch, normalize, parse
from app.agent_pr.news_agent.schemas import Agent_Output


@tool
def normalize_ticker(symbol: str) -> str:
    """Chuẩn hoá mã niêm yết trước khi lấy tin CafeF."""
    return str(normalize({"symbol": symbol})["symbol"])


@tool
def fetch_cafef_news(symbol: str) -> str:
    """Bắt buộc khi cần tin: bài mới trên trang mã CafeF (News.ashx). Không chấm sentiment, không bịa tiêu đề."""
    try:
        st = normalize({"symbol": symbol})
        st.update(fetch(st))
        st.update(parse(st))
        return st["news"].model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol=str(symbol or "").strip().upper(),
            articles=[],
            source=f"Lỗi CafeF: {exc}. Thử lại hoặc dùng tin đã lưu trong DB.",
        ).model_dump_json()


@tool
def describe_news_source() -> str:
    """Nguồn tin NewsAgent (không gọi mạng)."""
    return "CafeF du-lieu/Ajax/PageNew/News.ashx NewsType=0."


TOOLS = [normalize_ticker, fetch_cafef_news, describe_news_source]
