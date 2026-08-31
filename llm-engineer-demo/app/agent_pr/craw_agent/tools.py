"""Tools PriceAgent — LLM chọn, ToolNode thực thi. Logic IO vẫn ở nodes.py."""

from __future__ import annotations

from langchain_core.tools import tool

from app.agent_pr.craw_agent.nodes import fetch, normalize, parse


@tool
def normalize_ticker(symbol: str) -> str:
    """Chuẩn hoá mã niêm yết VN (vd hpg → HPG). Sai định dạng thì báo lỗi."""
    out = normalize({"symbol": symbol})
    return str(out["symbol"])


@tool
def fetch_latest_close(symbol: str) -> str:
    """Lấy giá đóng cửa 2 phiên mới nhất từ vnstock (KBS), đơn vị VND + %."""
    st = normalize({"symbol": symbol})
    st.update(fetch(st))
    st.update(parse(st))
    return st["quote"].model_dump_json()


@tool
def describe_price_source() -> str:
    """Nguồn giá PriceAgent dùng (không gọi mạng)."""
    return "vnstock Quote.history nguồn KBS, close nghìn đồng ×1000 = VND."


TOOLS = [normalize_ticker, fetch_latest_close, describe_price_source]
