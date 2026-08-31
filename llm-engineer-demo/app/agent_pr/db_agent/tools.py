"""Tools DBAgent — đọc sqlite / soạn pending. COMMIT không ở đây (HITL hub)."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.agent_pr.db_agent.nodes import normalize, parse, read, stage_writes
from app.agent_pr.db_agent.schemas import CandidateNews, CandidatePrice


@tool
def read_symbol_store(symbol: str) -> str:
    """Đọc tối đa 5 phiên giá + tin đã lưu trong DB (không HITL)."""
    st = normalize({"symbol": symbol})
    st.update(read(st))
    st.update(parse(st))
    return st["result"].model_dump_json()


@tool
def stage_new_rows(symbol: str, news_json: str = "[]", prices_json: str = "[]") -> str:
    """Soạn lệnh ghi tin/giá chưa có trong kho. news_json/prices_json là list JSON.
    Chưa COMMIT — hub HITL mới ghi bảng chính."""
    st = normalize({"symbol": symbol})
    st.update(read(st))
    news = [CandidateNews.model_validate(x) for x in json.loads(news_json or "[]")]
    prices = [CandidatePrice.model_validate(x) for x in json.loads(prices_json or "[]")]
    st["candidate_news"] = news
    st["candidate_prices"] = prices
    st.update(stage_writes(st))
    st.update(parse(st))
    return st["result"].model_dump_json()


@tool
def describe_db_hitl() -> str:
    """Vì sao ghi DB phải qua người duyệt."""
    return "Đọc tự động. Soạn pending rồi hub interrupt_before hitl_commit mới COMMIT."


TOOLS = [read_symbol_store, stage_new_rows, describe_db_hitl]
