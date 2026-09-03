"""Tools DBAgent — đọc sqlite / soạn pending. COMMIT ở hub HITL.

`stage_new_rows` có side-effect → nhận `idempotency_key` (LLM gửi khi RETRY
đúng lời gọi trước, vd sau lỗi mạng — không tự suy luận key từ payload: 2
lần gọi khác nhau CÙNG symbol+payload là chuyện bình thường, hợp lệ, khác
"cùng 1 lần gọi retry"). Cùng ý `app.agent_m2.tools._run_idempotent`: có key
→ chặn thật re-run trong process (dict in-memory), trả lại kết quả cũ thay
vì soạn lại. Không key → luôn chạy thật, để UNIQUE (symbol, url/date) +
INSERT OR IGNORE ở tầng DB tự dedup (bền qua restart, đúng bản chất hơn).
Đọc không cần key.
"""

from __future__ import annotations

import json
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.agent_pr.db_agent.nodes import parse, read, stage_writes
from app.agent_pr.db_agent.schemas import Agent_Output, CandidateNews, CandidatePrice

# Cùng agent_m2/tools.py — dict in-memory, demo/process-local (không bền qua
# restart; production sẽ là bảng DB có unique constraint trên key).
_IDEMPOTENCY_STORE: dict[str, str] = {}


@tool
def read_symbol_store(symbol: str, turn: Annotated[str, InjectedState("turn")] = "") -> str:
    """Đọc tối đa 5 phiên giá + tin đã lưu trong DB (không HITL)."""
    try:
        st = {"symbol": str(symbol or "").strip().upper(), "turn": turn}
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
    turn: Annotated[str, InjectedState("turn")] = "",
) -> str:
    """Soạn lệnh ghi tin/giá chưa có. Cùng url/date không nhân pending.

    Gọi lại với cùng `idempotency_key` (model tự gửi khi RETRY, vd sau lỗi
    mạng) trả THẲNG kết quả lần trước, không soạn lại. Không có key → luôn
    chạy thật (payload trùng ngẫu nhiên giữa 2 turn khác nhau là hợp lệ,
    không phải retry) — UNIQUE index vẫn chặn ghi trùng ở tầng DB. Chưa
    COMMIT — hub HITL mới ghi bảng chính.
    """
    symbol_u = str(symbol or "").strip().upper()
    if idempotency_key:
        cached = _IDEMPOTENCY_STORE.get(idempotency_key)
        if cached is not None:
            return cached
    try:
        st = {"symbol": symbol_u, "turn": turn}
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
        result = out.model_dump_json()
        if idempotency_key:
            _IDEMPOTENCY_STORE[idempotency_key] = result
        return result
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
