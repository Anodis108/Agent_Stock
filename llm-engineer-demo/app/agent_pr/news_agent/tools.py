"""Tools NewsAgent — CafeF Ajax. Parse/fetch thật ở nodes.py."""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent_pr.news_agent.nodes import fetch, normalize, parse


@tool
def normalize_ticker(symbol: str) -> str:
    """Chuẩn hoá mã niêm yết trước khi lấy tin CafeF."""
    return str(normalize({"symbol": symbol})["symbol"])


@tool
def fetch_cafef_news(symbol: str) -> str:
    """Lấy tin bài mới nhất trên trang mã CafeF (News.ashx, không chấm sentiment)."""
    st = normalize({"symbol": symbol})
    st.update(fetch(st))
    st.update(parse(st))
    return st["news"].model_dump_json()


@tool
def describe_news_source() -> str:
    """Nguồn tin NewsAgent (không gọi mạng)."""
    return "CafeF du-lieu/Ajax/PageNew/News.ashx NewsType=0."


TOOLS = [normalize_ticker, fetch_cafef_news, describe_news_source]
