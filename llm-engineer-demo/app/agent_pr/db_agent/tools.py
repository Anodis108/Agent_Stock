"""Tools DBAgent — đọc sqlite / soạn pending. COMMIT ở hub HITL.

`stage_new_rows` có side-effect → nhận `idempotency_key` (LLM có thể gửi).
Gọi lại không nhân hàng: UNIQUE (symbol, url/date) + INSERT OR IGNORE.
Đọc không cần key.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.agent_pr.db_agent.nodes import normalize, parse, read, stage_writes
from app.agent_pr.db_agent.schemas import Agent_Output, CandidateNews, CandidatePrice


@tool
def read_symbol_store(symbol: str) -> str:
    """Đọc tối đa 5 phiên giá + tin đã lưu trong DB (không HITL)."""
    try:
        st = normalize({"symbol": symbol})
        st.update(read(st))
        st.update(parse(st))
        return st["result"].model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol=str(symbol or ""),
            detail=f"Lỗi đọc DB: {exc}. Thử lại hoặc bỏ qua lịch sử kho.",
        ).model_dump_json()


@tool
def stage_new_rows(
    symbol: str,
    news_json: str = "[]",
    prices_json: str = "[]",
    idempotency_key: str = "",
) -> str:
    """Soạn lệnh ghi tin/giá chưa có. Cùng url/date không nhân pending.

    `idempotency_key` để model gửi khi retry cùng payload. Chưa COMMIT —
    hub HITL mới ghi bảng chính.
    """
    try:
        st = normalize({"symbol": symbol})
        st.update(read(st))
        news = [CandidateNews.model_validate(x) for x in json.loads(news_json or "[]")]
        prices = [CandidatePrice.model_validate(x) for x in json.loads(prices_json or "[]")]
        st["candidate_news"] = news
        st["candidate_prices"] = prices
        st.update(stage_writes(st))
        st.update(parse(st))
        out = st["result"]
        if idempotency_key and out.detail:
            out = out.model_copy(update={"detail": f"{out.detail} [key={idempotency_key}]"})
        return out.model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol=str(symbol or ""),
            detail=f"Lỗi soạn pending: {exc}. Thử lại hoặc đọc kho trước.",
        ).model_dump_json()


@tool
def describe_db_hitl() -> str:
    """Vì sao ghi DB phải qua người duyệt."""
    return "Đọc tự động. Soạn pending rồi hub interrupt_before hitl_commit mới COMMIT."


TOOLS = [read_symbol_store, stage_new_rows, describe_db_hitl]
