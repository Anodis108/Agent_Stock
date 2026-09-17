"""API dependency wiring — shared stores/sources for routers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.portfolio_watch.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from src.portfolio_watch.infra.market_data import CafefNewsSource, VnstockPriceSource
from src.portfolio_watch.infra.notify import ConsoleNotifier
from src.portfolio_watch.infra.storage import (
    SqliteMemoryStore,
    SqlitePriceHistoryStore,
    SqliteWatchlistStore,
)
from src.portfolio_watch.shared.settings import settings

_override: "AppDeps | None" = None


@dataclass
class AppDeps:
    price_source: PriceSource
    news_source: NewsSource
    history_store: PriceHistoryStore
    memory_store: MemoryStore
    notifier: Notifier
    watchlist_store: WatchlistStore


def set_app_deps(deps: AppDeps | None) -> None:
    """Test/override hook — None = dùng default từ settings."""
    global _override
    _override = deps


@lru_cache
def _build_default_deps() -> AppDeps:
    db_path = settings.sqlite_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    memory = SqliteMemoryStore(db_path)
    return AppDeps(
        price_source=VnstockPriceSource(),
        news_source=CafefNewsSource(),
        history_store=SqlitePriceHistoryStore(db_path),
        memory_store=memory,
        notifier=ConsoleNotifier(memory),
        watchlist_store=SqliteWatchlistStore(db_path),
    )


def get_app_deps() -> AppDeps:
    if _override is not None:
        return _override
    return _build_default_deps()


def clear_deps_cache() -> None:
    _build_default_deps.cache_clear()
