"""Tool worker news_agent — tin CafeF / Vnstock theo mã (artifact {"news": [NewAgentResult]})."""

from __future__ import annotations

from itertools import chain

from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from ai_backend.domain.agents.scan.news_agent.state import NewAgentResult
from ai_backend.infra.monitoring.tracing import trace_step


def news_from_tool_artifacts(message_worker: list) -> list[NewAgentResult]:
    """Mỗi lần gọi get_stock_news → ToolMessage + artifact {"news": [NewAgentResult]}."""
    slices = (
        a["news"]
        for m in message_worker
        if getattr(m, "type", None) == "tool"
        and (a := getattr(m, "artifact", None)) is not None
        and "news" in a
    )
    return list(chain.from_iterable(slices))


@tool(response_format="content_and_artifact")
def get_stock_news(symbol: str, query: str = ""):
    """Lấy tin tức doanh nghiệp mới nhất của MỘT mã cổ phiếu; `query` (tuỳ chọn) để lọc chủ đề (vd: "lợi nhuận")."""
    sym = symbol.strip().upper()
    deps = get_runtime().context
    with trace_step(deps["trace_span"], "news_agent.fetch_news", input={"symbol": sym, "query": query}) as box:
        try:
            items = deps["news_source"].fetch_news(sym, query=query or sym, days=deps["news_days"]) or []
            n = NewAgentResult(symbol=sym, items=items)
        except Exception as exc:  # noqa: BLE001
            n = NewAgentResult(symbol=sym, items=[], error=f"không lấy được tin: {exc}")
        box["output"] = {"items": len(n.items), "error": n.error}
    titles = "; ".join(i.title for i in n.items[:8])
    return (f"{sym}: lỗi {n.error}" if n.error else f"{sym}: {len(n.items)} tin — {titles}"), {"news": [n]}


TOOLS = [get_stock_news]
