"""API dependency wiring for Web Backend."""

from __future__ import annotations

from fastapi import Header, HTTPException, Query

from dataclasses import dataclass
from typing import Any


@dataclass
class AppDeps:
    price_source: Any = None
    news_source: Any = None
    history_store: Any = None
    memory_store: Any = None
    notifier: Any = None
    watchlist_store: Any = None
    holdings_repo: Any = None
    user_settings_repo: Any = None


_deps_instance: AppDeps | None = None


def get_app_deps() -> AppDeps:
    global _deps_instance
    if _deps_instance is not None:
        return _deps_instance
    try:
        from web_backend.infra.database.connection import get_connection
        from web_backend.infra.database.repositories import (
            PortfolioHoldingRepository,
            UserSettingsRepository,
            WatchlistRepository,
        )
        conn = get_connection()
        _deps_instance = AppDeps(
            holdings_repo=PortfolioHoldingRepository(conn),
            user_settings_repo=UserSettingsRepository(conn),
            watchlist_store=WatchlistRepository(conn),
        )
    except Exception:
        _deps_instance = AppDeps()
    return _deps_instance


def set_app_deps(deps: AppDeps | None) -> None:
    global _deps_instance
    _deps_instance = deps


def clear_deps_cache() -> None:
    global _deps_instance
    _deps_instance = None


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    user_id: str | None = Query(default=None),
) -> str:
    """user_id hiện tại từ HTTP Header X-User-ID hoặc query param user_id — bắt buộc, thiếu → 400 (không tự gán)."""
    cleaned = (x_user_id or user_id or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Thiếu user_id (header X-User-ID hoặc query user_id)")
    return cleaned


__all__ = [
    "AppDeps",
    "get_app_deps",
    "set_app_deps",
    "clear_deps_cache",
    "get_current_user_id",
]
