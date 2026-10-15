"""CRUD /watchlist — Web Watchlist router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from web_backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from web_backend.api.helpers.validation import normalize_symbol, validate_threshold_pct
from web_backend.api.models.watchlist import (
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    WatchlistItemOut,
    WatchlistListResponse,
)

router = APIRouter(tags=["watchlist"])

from common.domain.entities import WatchlistItem
from web_backend.shared.settings import settings


class _FallbackWatchlistStore:
    def __init__(self) -> None:
        self._items: dict[str, float] = {}

    def get_watchlist(self) -> list[str]:
        return list(self._items.keys())

    def add_to_watchlist(self, symbol: str, threshold: float = 3.0) -> None:
        self._items[symbol] = threshold

    def remove_from_watchlist(self, symbol: str) -> None:
        self._items.pop(symbol, None)


_store = _FallbackWatchlistStore()
store = _store



def _to_out(item: Any) -> WatchlistItemOut:
    return WatchlistItemOut(
        symbol=item.symbol,
        threshold_pct=float(item.threshold_pct),
        alert_threshold_pct=float(getattr(item, "alert_threshold_pct", item.threshold_pct)),
        user_id=getattr(item, "user_id", "default"),
    )


@router.get("/api/v1/watchlist", response_model=WatchlistListResponse)
@router.get("/api/watchlist", response_model=WatchlistListResponse)
@router.get("/watchlist", response_model=WatchlistListResponse)
def get_watchlist(
    user_id: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistListResponse:
    if hasattr(deps, "watchlist_store") and deps.watchlist_store is not None:
        store = deps.watchlist_store
        items_raw = store.list_items(user_id) if hasattr(store, "list_items") else (store.list(user_id=user_id) if hasattr(store, "list") else [])
        out = [_to_out(x) for x in items_raw]
        return WatchlistListResponse(items=out, count=len(out))

    if _store is not None:
        raw = _store.get_watchlist()
        default_thr = float(settings.default_alert_threshold_pct) if settings else 3.0
        out = [
            WatchlistItemOut(
                symbol=s,
                threshold_pct=default_thr,
                alert_threshold_pct=default_thr,
                user_id=user_id,
            )
            for s in raw
        ]
        return WatchlistListResponse(items=out, count=len(out))

    return WatchlistListResponse(items=[], count=0)


@router.post("/api/v1/watchlist", response_model=WatchlistItemOut)
@router.post("/api/watchlist", response_model=WatchlistItemOut)
@router.post("/watchlist", response_model=WatchlistItemOut)
def post_watchlist(
    body: CreateWatchlistRequest,
    current_user: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistItemOut:
    symbol = normalize_symbol(body.symbol)
    raw_thr = body.alert_threshold_pct if body.alert_threshold_pct is not None else body.threshold_pct
    thr = validate_threshold_pct(raw_thr)
    if thr is None:
        thr = float(settings.default_alert_threshold_pct) if settings else 3.0
    effective_user = body.user_id if body.user_id != "default" else current_user

    if hasattr(deps, "watchlist_store") and deps.watchlist_store is not None:
        store = deps.watchlist_store
        if hasattr(store, "upsert") and WatchlistItem is not None:
            saved = store.upsert(
                WatchlistItem(
                    symbol=symbol,
                    threshold_pct=thr,
                    user_id=effective_user,
                )
            )
            return _to_out(saved)
        elif hasattr(store, "add"):
            item = store.add(symbol, threshold_pct=thr, user_id=effective_user)
            return _to_out(item)

    if _store is not None:
        _store.add_to_watchlist(symbol)
    return WatchlistItemOut(
        symbol=symbol,
        threshold_pct=thr,
        alert_threshold_pct=thr,
        user_id=effective_user,
    )


@router.patch("/api/v1/watchlist/{symbol}", response_model=WatchlistItemOut)
@router.patch("/api/watchlist/{symbol}", response_model=WatchlistItemOut)
@router.patch("/watchlist/{symbol}", response_model=WatchlistItemOut)
@router.put("/api/v1/watchlist/{symbol}", response_model=WatchlistItemOut)
@router.put("/api/watchlist/{symbol}", response_model=WatchlistItemOut)
@router.put("/watchlist/{symbol}", response_model=WatchlistItemOut)
def update_watchlist(
    symbol: str,
    body: UpdateWatchlistRequest,
    current_user: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistItemOut:
    sym = normalize_symbol(symbol)
    user_id = body.user_id if body.user_id != "default" else current_user

    raw_thr = body.alert_threshold_pct if body.alert_threshold_pct is not None else body.threshold_pct
    thr = validate_threshold_pct(raw_thr, required=True)
    assert thr is not None

    if hasattr(deps, "watchlist_store") and deps.watchlist_store is not None:
        store = deps.watchlist_store
        if hasattr(store, "get") and hasattr(store, "upsert") and WatchlistItem is not None:
            existing = store.get(user_id, sym)
            if existing is None:
                raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
            saved = store.upsert(
                WatchlistItem(
                    symbol=sym,
                    threshold_pct=thr,
                    user_id=user_id,
                )
            )
            return _to_out(saved)
        elif hasattr(store, "update_threshold"):
            item = store.update_threshold(sym, threshold_pct=thr, user_id=user_id)
            if item is None:
                raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
            return _to_out(item)

    return WatchlistItemOut(
        symbol=sym,
        threshold_pct=thr,
        alert_threshold_pct=thr,
        user_id=user_id,
    )


@router.delete("/api/v1/watchlist/{symbol}")
@router.delete("/api/watchlist/{symbol}")
@router.delete("/watchlist/{symbol}")
def delete_watchlist(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    deps: AppDeps = Depends(get_app_deps),
) -> dict[str, Any]:
    sym = normalize_symbol(symbol)
    if hasattr(deps, "watchlist_store") and deps.watchlist_store is not None:
        store = deps.watchlist_store
        if hasattr(store, "delete"):
            ok = store.delete(user_id, sym)
            if not ok:
                raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
            return {"status": "success", "ok": True, "symbol": sym, "user_id": user_id}
        elif hasattr(store, "remove"):
            ok = store.remove(sym, user_id=user_id)
            if not ok:
                raise HTTPException(status_code=404, detail=f"{sym} không có trong watchlist")
            return {"status": "success", "ok": True, "symbol": sym, "user_id": user_id}

    if _store is not None:
        _store.remove_from_watchlist(sym)
    return {"status": "success", "ok": True, "symbol": sym, "user_id": user_id}
