"""Tools PriceAgent — LLM chọn, ToolNode chạy. IO thật: nodes.normalize/fetch/parse.

`fetch_latest_close` là tool bắt buộc.
`normalize_ticker` / `describe_price_source` để model hỏi thêm, không thay fetch.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from app.agent_pr.craw_agent.nodes import fetch, normalize, parse
from app.agent_pr.craw_agent.schemas import Agent_Output


@tool
def normalize_ticker(symbol: str) -> str:
    """Chuẩn hoá mã (vd hpg → HPG). Không kiểm tra tồn tại sàn."""
    out = normalize({"symbol": symbol})
    return str(out["symbol"])


@tool
def fetch_latest_close(symbol: str, turn: Annotated[str, InjectedState("turn")] = "") -> str:
    """Bắt buộc khi cần giá: đóng cửa 2 phiên mới nhất vnstock VCI, VND + %. Không bịa số."""
    try:
        # Không gọi normalize() — đã có trace_step; LLM hay gọi normalize_ticker trước
        # thì sẽ bị 2 hàng craw_normalize trên Langfuse. `turn` injected (không lộ ra
        # LLM) — cho fetch/parse tìm đúng span "price_agent" làm cha (xem tracing.py).
        st = {"symbol": str(symbol or "").strip().upper(), "turn": turn}
        st.update(fetch(st))
        st.update(parse(st))
        return st["quote"].model_dump_json()
    except Exception as exc:
        return Agent_Output(
            symbol=str(symbol or "").strip().upper(),
            last=0,
            source=f"Lỗi vnstock: {exc}. Thử lại hoặc dùng lịch sử DB.",
        ).model_dump_json()


@tool
def describe_price_source() -> str:
    """Nguồn giá PriceAgent dùng (không gọi mạng)."""
    return "vnstock Quote.history nguồn VCI, close nghìn đồng ×1000 = VND."


TOOLS = [normalize_ticker, fetch_latest_close, describe_price_source]
