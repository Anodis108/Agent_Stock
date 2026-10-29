"""Tool worker price_agent — giá Vnstock theo mã (artifact {"prices": [PriceAgentResult]})."""

from __future__ import annotations

from itertools import chain

from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from ai_backend.domain.agents.scan.price_agent.state import PriceAgentResult
from ai_backend.infra.monitoring.tracing import current_span, trace_step


def prices_from_tool_artifacts(message_worker: list) -> list[PriceAgentResult]:
    """Mỗi lần gọi get_stock_price → ToolMessage + artifact {"prices": [PriceAgentResult]}."""
    slices = (
        a["prices"]
        for m in message_worker
        if getattr(m, "type", None) == "tool"
        and (a := getattr(m, "artifact", None)) is not None
        and "prices" in a
    )
    return list(chain.from_iterable(slices))


@tool(response_format="content_and_artifact")
def get_stock_price(symbol: str):
    """Lấy giá đóng cửa mới nhất, giá phiên trước và % thay đổi của MỘT mã cổ phiếu (vd: FPT)."""
    sym = symbol.strip().upper()
    with trace_step(current_span(), "price_agent.fetch_quote", input={"symbol": sym}, as_type="tool") as box:
        try:
            q = get_runtime().context["price_source"].fetch_latest_close(sym)
            change = (q.latest_close - q.prev_close) / q.prev_close * 100 if q.latest_close and q.prev_close else None
            p = PriceAgentResult(symbol=sym, latest_close=q.latest_close, prev_close=q.prev_close, change_pct=change, error=q.error)
        except Exception as exc:  # noqa: BLE001 — trả lỗi cho LLM thay vì crash
            p = PriceAgentResult(symbol=sym, latest_close=None, prev_close=None, change_pct=None, error=f"không lấy được dữ liệu giá: {exc}")
        box["output"] = {"latest_close": p.latest_close, "change_pct": p.change_pct, "error": p.error}
    text = f"{sym}: lỗi {p.error}" if p.error else f"{sym}: đóng cửa {p.latest_close}, phiên trước {p.prev_close}, thay đổi {p.change_pct:.2f}%"
    return text, {"prices": [p]}


TOOLS = [get_stock_price]
