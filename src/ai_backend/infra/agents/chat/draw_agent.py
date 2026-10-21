"""DrawAgent — worker vẽ của team chat: biểu đồ giá/nến/so sánh (chart_agent) và sơ đồ Mermaid (diagram_agent)."""

from __future__ import annotations

import re
import time
from typing import Any

from langchain_core.runnables import RunnableConfig

from ai_backend.infra.agents.chat.chart_agent import run_chart_agent
from ai_backend.infra.agents.chat.diagram_agent import run_diagram_agent
from ai_backend.infra.agents.scan.price_agent import PriceAgentResult
from ai_backend.infra.agents.events import emit_agent_event, graph_deps, target_symbols
from ai_backend.infra.monitoring.tracing import agent_span
from common.domain.ports import PriceBar, PriceHistoryStore, PriceSource
from common.logging import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # chỉ type hint — graph.state import ngược các agent
    from ai_backend.infra.agents.state import SwarmState

_logger = get_logger(__name__)


def chart_node(
    target_symbols: list[str],
    prices: list[PriceAgentResult],
    price_source: PriceSource,
    history_store: PriceHistoryStore | None = None,
    turn: str = "",
    question: str = "",
) -> Any | None:
    """Sinh biểu đồ kỹ thuật Matplotlib cho một hoặc nhiều mã cổ phiếu."""
    if not target_symbols:
        return None
    history_map: dict[str, list[PriceBar]] = {}

    q_lower = (question or "").lower()
    session_limit: int | None = None
    m_sess = re.search(r"(\d+)\s*(?:phiên|ngày|session|day)", q_lower)
    if m_sess:
        try:
            val = int(m_sess.group(1))
            if 2 <= val <= 100:
                session_limit = val
        except ValueError:
            pass

    fetch_days = max(30, (session_limit or 15) + 15)

    for sym_item in target_symbols:
        s_upper = sym_item.upper()
        bars: list[PriceBar] = []
        if history_store:
            try:
                bars = list(history_store.read_history(s_upper, days=fetch_days) or [])
            except Exception as exc:
                _logger.warning("history_store read_history failed for %s: %s", s_upper, exc)
                bars = []
        if len(bars) < 5 and hasattr(price_source, "fetch_history"):
            try:
                fetched = price_source.fetch_history(s_upper, days=fetch_days)
                if fetched:
                    bars = fetched
                    if history_store and hasattr(history_store, "upsert_bars"):
                        try:
                            history_store.upsert_bars(s_upper, bars)
                        except Exception:
                            pass
            except Exception as exc:
                _logger.warning("price_source fetch_history failed for %s: %s", s_upper, exc)
        if session_limit and len(bars) > session_limit:
            bars = bars[-session_limit:]
        history_map[s_upper] = bars

    is_candlestick = any(w in q_lower for w in ("nến", "candle", "candlestick"))
    style = "candle" if is_candlestick else "line"

    is_relative_comparison = any(
        w in q_lower
        for w in (
            "so sánh", "so sanh",
            "hiệu suất", "hieu suat",
            "tương đối", "tuong doi",
            "tỷ suất", "ty suat",
            "tăng trưởng", "tang truong",
            "tương quan", "tuong quan",
            "tỷ lệ tăng", "ty le tang",
        )
    )

    if is_relative_comparison:
        chosen_chart_type = "comparison"
    elif is_candlestick:
        chosen_chart_type = "candlestick"
    else:
        chosen_chart_type = "price_history"

    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "draw_agent", "symbols": target_symbols, "timestamp": time.time()})
    with agent_span(turn, "draw_agent", input=",".join(target_symbols)) as box:
        if len(target_symbols) == 1:
            chart_result = run_chart_agent(
                target_symbols[0],
                history_map.get(target_symbols[0].upper(), []),
                style=style,
                chart_type=chosen_chart_type,
                limit_sessions=session_limit,
            )
        else:
            chart_result = run_chart_agent(
                target_symbols,
                history_map,
                style=style,
                chart_type=chosen_chart_type,
                limit_sessions=session_limit,
            )
        box["output"] = {
            "success": chart_result.success,
            "url": chart_result.url,
            "file_path": chart_result.file_path,
            "error": chart_result.error,
        }
    if chart_result and getattr(chart_result, "success", False) and getattr(chart_result, "url", None):
        emit_agent_event(
            "chart_url",
            {
                "url": chart_result.url,
                "symbols": target_symbols,
                "chart_type": getattr(chart_result, "chart_type", chosen_chart_type),
                "file_path": getattr(chart_result, "file_path", None),
            },
        )
    dur = round(time.perf_counter() - t0, 3)
    emit_agent_event("node_finish", {"node": "draw_agent", "duration_s": dur, "duration_ms": int(dur * 1000)})
    return chart_result


def draw_agent_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Worker vẽ: biểu đồ giá/nến/so sánh (Matplotlib) và/hoặc sơ đồ Mermaid, tuỳ kế hoạch của chat_supervisor."""
    cfg = graph_deps.get()
    routing = state.get("routing")
    route = str(getattr(getattr(routing, "route", None), "value", getattr(routing, "route", "")))
    agents = [a.lower() for a in (routing.agents_to_call or [])] if routing else []
    update: dict[str, Any] = {"completed": ["draw_agent"]}
    turn = state.get("turn") or ""

    if route == "diagram" or "diagram" in agents:
        t0 = time.perf_counter()
        emit_agent_event("node_start", {"node": "draw_agent", "kind": "diagram", "timestamp": time.time()})
        symbol = state.get("symbol")
        with agent_span(turn, "draw_agent", input={"kind": "diagram", "symbol": symbol}) as box:
            diagram = run_diagram_agent(
                symbol, turn=turn, question=state.get("question") or "", brain=cfg.get("diagram_brain")
            )
            box["output"] = diagram.placeholder
        dur = round(time.perf_counter() - t0, 3)
        emit_agent_event("node_finish", {"node": "draw_agent", "duration_s": dur, "duration_ms": int(dur * 1000)})
        update["diagram_result"] = diagram

    if not ("chart" in agents or route == "chart"):
        return update

    prices = state.get("prices") or []
    symbols = target_symbols(state)
    if not symbols and state.get("price") and state["price"].symbol:
        symbols = [state["price"].symbol]
    req_q = state.get("question") or ""
    rw = state.get("rewritten")
    if rw and getattr(rw, "rewritten", None):
        req_q = f"{req_q} {rw.rewritten}"
    chart_result = chart_node(
        target_symbols=symbols,
        prices=prices,
        price_source=cfg["price_source"],
        history_store=cfg.get("history_store"),
        turn=turn,
        question=req_q,
    )
    update["chart_result"] = chart_result
    update["chart_path"] = chart_result.url if (chart_result and chart_result.success) else None
    return update
