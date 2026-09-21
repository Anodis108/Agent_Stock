"""Tools eval_agent — read_price_history."""

from __future__ import annotations

from src.portfolio_watch.domain.ports import PriceBar, PriceHistoryStore


def read_price_history(
    store: PriceHistoryStore,
    symbol: str,
    *,
    days: int = 30,
) -> list[PriceBar]:
    return list(store.read_history(symbol, days=days) or [])
