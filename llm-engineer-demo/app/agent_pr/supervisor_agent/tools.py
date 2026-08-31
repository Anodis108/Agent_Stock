"""Tools Coordinator — LLM chọn worker nào cần. ToolNode không crawl:
chỉ đánh dấu intent; hub Send subgraph (ReAct) chạy việc thật.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def need_price(symbol: str) -> str:
    """Cần giá đóng cửa / % so phiên trước — giao PriceAgent."""
    return symbol.upper().strip()


@tool
def need_news(symbol: str) -> str:
    """Cần tin CafeF — giao NewsAgent."""
    return symbol.upper().strip()


@tool
def need_db(symbol: str) -> str:
    """Cần nêu lịch sử đã lưu trong DB (hub vẫn đọc DB trước khi crawl)."""
    return symbol.upper().strip()


@tool
def need_eval(symbol: str) -> str:
    """Cần chấm tin vs chiều giá — chỉ khi cũng cần giá VÀ tin."""
    return symbol.upper().strip()


@tool
def need_synth(symbol: str) -> str:
    """Cần ghép câu trả lời có cấu trúc cho user."""
    return symbol.upper().strip()


TOOLS = [need_price, need_news, need_db, need_eval, need_synth]
