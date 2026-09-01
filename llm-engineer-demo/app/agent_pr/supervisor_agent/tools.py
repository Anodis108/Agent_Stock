"""Tools Coordinator — chỉ *đánh dấu* worker nào cần (intent).

Không gọi vnstock/CafeF/sqlite. ToolNode trên hub *không* gắn các tool này
để thực thi IO: `_make_plan` đọc `tool_calls` rồi `_sanitize_plan`. Việc thật
là subgraph ReAct sau `Send`.

Năm tool nhỏ (cùng shape `symbol`) để retrieval/bind_tools chọn được nhiều
cờ cùng lúc — khác 1 tool "plan_all" sẽ khoá cứng 1 domain.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def need_price(symbol: str) -> str:
    """Cần giá đóng cửa / % so phiên trước. Dùng khi hỏi giá, tăng/giảm, biến động. Giao PriceAgent."""
    return symbol.upper().strip()


@tool
def need_news(symbol: str) -> str:
    """Cần tin CafeF thô. Dùng khi hỏi tin, nguyên nhân, tại sao giá đổi. Giao NewsAgent — không chấm sentiment."""
    return symbol.upper().strip()


@tool
def need_db(symbol: str) -> str:
    """Cần nêu lịch sử đã lưu trong sqlite. Dùng khi hỏi kho/lịch sử đã lưu — hub vẫn đọc DB trước crawl."""
    return symbol.upper().strip()


@tool
def need_eval(symbol: str) -> str:
    """Cần chấm tin vs chiều giá. CHỈ gọi khi cũng need_price VÀ need_news (câu phân tích/tại sao)."""
    return symbol.upper().strip()


@tool
def need_synth(symbol: str) -> str:
    """Cần ghép câu trả lời có cấu trúc cho user. Gần như luôn bật sau khi đã có dữ liệu."""
    return symbol.upper().strip()


TOOLS = [need_price, need_news, need_db, need_eval, need_synth]
