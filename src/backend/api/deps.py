"""API dependency wiring — HTTP dependencies and re-export of shared AppDeps."""

from __future__ import annotations

from fastapi import Header, Query

from backend.shared.deps import (
    AppDeps,
    clear_deps_cache,
    get_app_deps,
    set_app_deps,
)

__all__ = [
    "AppDeps",
    "get_app_deps",
    "set_app_deps",
    "clear_deps_cache",
    "get_current_user_id",
]


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    user_id: str | None = Query(default=None),
) -> str:
    """Xác định user_id hiện tại từ HTTP Header X-User-ID hoặc query param user_id."""
    raw = x_user_id or user_id or "default"
    cleaned = raw.strip()
    return cleaned if cleaned else "default"
