"""API dependency wiring — shared stores/sources for routers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from fastapi import Header, Query

from backend.database.connection import get_connection
from backend.database.repositories import (
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
from backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from backend.infra.notify import ConsoleNotifier
from backend.infra.storage import (
    SqliteMemoryStore,
    SqlitePriceHistoryStore,
    SqliteWatchlistStore,
)
from backend.shared.settings import settings

_override: "AppDeps | None" = None


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
        news_source=CafefNewsSource(),
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


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    user_id: str | None = Query(default=None),
) -> str:
    """Xác định user_id hiện tại từ HTTP Header X-User-ID hoặc query param user_id."""
    raw = x_user_id or user_id or "default"
    cleaned = raw.strip()
    return cleaned if cleaned else "default"
