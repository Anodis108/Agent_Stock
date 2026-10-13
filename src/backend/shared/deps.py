"""Shared Application Dependencies & Composition Root.

Wire các adapters, repositories, market data sources và stores dùng chung cho cả Web và AI Swarm.
Hoàn toàn độc lập với FastAPI HTTP framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.infra.database.connection import get_connection
from backend.infra.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from backend.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from backend.infra.market_data import (
    CafefNewsSource,
    MultiSourceNewsSource,
    VnstockNewsSource,
    VnstockPriceSource,
)
from backend.infra.notify import ConsoleNotifier
from backend.infra.storage import (
    SqliteMemoryStore,
    SqlitePriceHistoryStore,
    SqliteWatchlistStore,
)
from backend.shared.settings import settings

_override: AppDeps | None = None


@dataclass
class AppDeps:
    price_source: PriceSource
    news_source: NewsSource
    history_store: PriceHistoryStore
    memory_store: MemoryStore
    notifier: Notifier
    watchlist_store: WatchlistStore
    holdings_repo: PortfolioHoldingRepository | None = None
    user_settings_repo: UserSettingsRepository | None = None


def set_app_deps(deps: AppDeps | None) -> None:
    """Test/override hook — None = dùng default từ settings."""
    global _override
    _override = deps


@lru_cache
def _build_default_deps() -> AppDeps:
    db_path = settings.sqlite_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    memory = SqliteMemoryStore(db_path)
    return AppDeps(
        price_source=VnstockPriceSource(),
        news_source=MultiSourceNewsSource([CafefNewsSource(), VnstockNewsSource()]),
        history_store=SqlitePriceHistoryStore(db_path),
        memory_store=memory,
        notifier=ConsoleNotifier(memory),
        watchlist_store=SqliteWatchlistStore(db_path),
        holdings_repo=PortfolioHoldingRepository(conn),
        user_settings_repo=UserSettingsRepository(conn),
    )


def get_app_deps() -> AppDeps:
    if _override is not None:
        return _override
    return _build_default_deps()


def clear_deps_cache() -> None:
    _build_default_deps.cache_clear()
