"""PriceAgent — hàm thuần, không LLM: % thay đổi giá so với phiên trước."""

from __future__ import annotations

from ai_backend.infra.agents.scan.price_agent.schemas import PriceAgentResult
from common.domain.ports import PriceQuote, PriceSource


def has_change_pct_evidence(price: PriceAgentResult | None) -> bool:
    """Đủ evidence giá để so sánh % (Phase 3c)."""
    return (
        price is not None
        and not price.error
        and price.change_pct is not None
    )


def prices_have_change_pct_evidence(
    prices: list[PriceAgentResult],
    symbols: list[str] | None = None,
) -> bool:
    """Mọi mã (hoặc tập symbols) đều có change_pct trước khi so sánh %."""
    if not prices:
        return False
    by_sym = {p.symbol.upper(): p for p in prices if p.symbol}
    targets = [s.upper() for s in symbols] if symbols else list(by_sym)
    if not targets:
        return False
    return all(has_change_pct_evidence(by_sym.get(s)) for s in targets)


from ai_backend.infra.monitoring.tracing import agent_step

def run_price_agent(symbol: str, price_source: PriceSource, turn: str = "") -> PriceAgentResult:
    try:
        with agent_step(turn, "price_agent", "fetch_quote", input={"symbol": symbol}) as box:
            try:
                quote = price_source.fetch_latest_close(symbol)
                box["output"] = {
                    "latest_close": quote.latest_close if quote else None,
                    "prev_close": quote.prev_close if quote else None,
                    "error": quote.error if quote else None,
                }
            except Exception as exc:
                box["output"] = {"error": str(exc)}
                raise
    except Exception as exc:  # noqa: BLE001
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=None,
            change_pct=None,
            error=f"không lấy được dữ liệu giá: {exc}",
        )
    if quote is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=None,
            change_pct=None,
            error="không lấy được dữ liệu giá",
        )
    res = _from_quote(symbol, quote)
    _sync_price_to_market_history(symbol, res)
    return res


def _sync_price_to_market_history(symbol: str, result: PriceAgentResult) -> None:
    """Tự động đồng bộ phiên giá mới nhất của PriceAgent vào bảng market_history_10d."""
    if result.latest_close is None or result.error:
        return
    try:
        from datetime import datetime
        from ai_backend.infra.database.connection import get_connection
        from ai_backend.infra.database.repositories import MarketHistoryRepository

        conn = get_connection()
        try:
            repo = MarketHistoryRepository(conn)
            today_str = datetime.now().date().isoformat()
            chg = round(result.change_pct, 2) if result.change_pct is not None else None
            repo.upsert_bar(
                symbol=symbol.strip().upper(),
                trade_date=today_str,
                close=result.latest_close,
                open_=result.prev_close,
                change_pct=chg,
            )
        finally:
            conn.close()
    except Exception:
        # Khi chạy trong test cô lập không có DB hoặc mock repo thì bỏ qua an toàn
        pass


def _from_quote(symbol: str, quote: PriceQuote) -> PriceAgentResult:
    if quote.error:
        err = quote.error.strip()
        lower = err.lower()
        if (
            err
            and not lower.startswith("không lấy được")
            and not lower.startswith("mã cổ phiếu")
            and not lower.startswith("không tìm thấy")
            and not lower.startswith("nguồn dữ liệu")
            and not lower.startswith("không thể kết nối")
            and not lower.startswith("symbol rỗng")
        ):
            err = f"không lấy được dữ liệu giá: {err}"
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=quote.prev_close,
            change_pct=None,
            error=err or "không lấy được dữ liệu giá",
        )
    if quote.latest_close is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=None,
            prev_close=quote.prev_close,
            change_pct=None,
            error="không lấy được dữ liệu giá",
        )
    if quote.prev_close is None:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=None,
            change_pct=None,
            error="không có giá phiên trước để tính % thay đổi",
        )
    if quote.prev_close == 0:
        return PriceAgentResult(
            symbol=symbol,
            latest_close=quote.latest_close,
            prev_close=quote.prev_close,
            change_pct=None,
            error="giá phiên trước = 0, không tính được % thay đổi",
        )

    change_pct = (quote.latest_close - quote.prev_close) / quote.prev_close * 100.0
    return PriceAgentResult(
        symbol=symbol,
        latest_close=quote.latest_close,
        prev_close=quote.prev_close,
        change_pct=change_pct,
        error=None,
    )

# ==============================================================================
# Graph node (Hierarchical Swarm)
# ==============================================================================

import time
from typing import Any

from langchain_core.runnables import RunnableConfig

from ai_backend.infra.agents.events import emit_agent_event, graph_deps, run_per_symbol, target_symbols
from ai_backend.infra.monitoring.tracing import agent_span
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # chỉ type hint — graph.state import ngược các agent
    from ai_backend.infra.agents.state import SwarmState


def price_node(
    sym: str,
    price_source: PriceSource,
    turn: str = "",
) -> PriceAgentResult:
    """Thu thập dữ liệu giá Vnstock cho một mã cổ phiếu cụ thể."""
    t0 = time.perf_counter()
    emit_agent_event("node_start", {"node": "price_agent", "symbol": sym, "timestamp": time.time()})
    has_cache = hasattr(price_source, "cache_stats") and callable(getattr(price_source, "cache_stats"))
    hits_before = price_source.cache_stats().get("hits", 0) if has_cache else 0
    with agent_span(turn, "price_agent", input=sym) as box:
        p = run_price_agent(sym, price_source, turn)
        from_cache = (price_source.cache_stats().get("hits", 0) > hits_before) if has_cache else False
        out = {
            "symbol": sym,
            "latest_close": p.latest_close,
            "change_pct": p.change_pct,
            "error": p.error,
            "from_cache": from_cache,
        }
        box["output"] = out
        dur = round(time.perf_counter() - t0, 3)
        finish_payload: dict[str, Any] = {
            "node": "price_agent",
            "symbol": sym,
            "duration_s": dur,
            "duration_ms": int(dur * 1000),
            "output": out,
            "status": "error" if p.error else "done",
        }
        if from_cache:
            emit_agent_event("node_start", {"node": "price_cache", "symbol": sym, "timestamp": time.time()})
            emit_agent_event(
                "node_finish",
                {
                    "node": "price_cache",
                    "symbol": sym,
                    "duration_s": 0,
                    "duration_ms": 0,
                    "output": {"cache_hit": True, "symbol": sym, "layer": "price_source_ttl"},
                    "status": "done",
                },
            )
        emit_agent_event("node_finish", finish_payload)
        return p


def price_agent_node(state: SwarmState, config: RunnableConfig) -> dict[str, Any]:
    """Worker giá: lấy giá mới nhất cho mọi mã cần thiết."""
    symbols = target_symbols(state)
    prices = run_per_symbol(price_node, symbols, graph_deps.get()["price_source"], state.get("turn") or "")
    main = (state.get("symbol") or "").upper()
    price = next((p for p in prices if p.symbol.upper() == main), prices[0] if prices else None)
    return {"price": price, "prices": prices, "completed": ["price_agent"]}
