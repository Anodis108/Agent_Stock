"""Tools PriceAgent — LLM chọn, ToolNode chạy. IO thật: nodes.normalize/fetch/parse.

`fetch_latest_close` là tool bắt buộc (offline_call cũng giả đúng tool này).
`normalize_ticker` / `describe_price_source` để model hỏi thêm, không thay fetch.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent_pr.craw_agent.nodes import fetch, normalize, parse
from app.agent_pr.craw_agent.schemas import Agent_Output


@tool
def normalize_ticker(symbol: str) -> str:
    """Chuẩn hoá mã (vd hpg → HPG). Không kiểm tra tồn tại sàn."""
    out = normalize({"symbol": symbol})
    return str(out["symbol"])


@tool
def fetch_latest_close(symbol: str) -> str:
    """Bắt buộc khi cần giá: đóng cửa 2 phiên mới nhất vnstock KBS, VND + %. Không bịa số."""
    try:
        st = normalize({"symbol": symbol})
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
    return "vnstock Quote.history nguồn KBS, close nghìn đồng ×1000 = VND."


TOOLS = [normalize_ticker, fetch_latest_close, describe_price_source]
