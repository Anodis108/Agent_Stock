"""CRUD /watchlist — thêm/xem/sửa ngưỡng/xóa mã (không qua HITL)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.portfolio_watch.api.deps import AppDeps, get_app_deps
from src.portfolio_watch.api.helpers.validation import (
    normalize_symbol,
    validate_threshold_pct,
)
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.shared.settings import settings

router = APIRouter(tags=["watchlist"])


class WatchlistItemOut(BaseModel):
    symbol: str
    threshold_pct: float
    user_id: str = "default"


class WatchlistListResponse(BaseModel):
    items: list[WatchlistItemOut] = Field(default_factory=list)
    count: int = 0


class CreateWatchlistRequest(BaseModel):
    symbol: str = Field(description="Mã chứng khoán VN")
    threshold_pct: float | None = Field(
        default=None, description="None = ngưỡng mặc định"
    )
    user_id: str = "default"


class UpdateWatchlistRequest(BaseModel):
    threshold_pct: float
    user_id: str = "default"


def _to_out(item: WatchlistItem) -> WatchlistItemOut:
    return WatchlistItemOut(
        symbol=item.symbol,
        threshold_pct=float(item.threshold_pct),
        user_id=item.user_id,
    )


@router.get("/watchlist", response_model=WatchlistListResponse)
def get_watchlist(
    user_id: str = Query(default="default"),
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistListResponse:
    items = [_to_out(i) for i in deps.watchlist_store.list_items(user_id)]
    return WatchlistListResponse(items=items, count=len(items))


@router.post("/watchlist", response_model=WatchlistItemOut)
def post_watchlist(
    body: CreateWatchlistRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistItemOut:
    symbol = normalize_symbol(body.symbol)
    thr = validate_threshold_pct(body.threshold_pct)
    if thr is None:
        thr = float(settings.default_alert_threshold_pct)
    saved = deps.watchlist_store.upsert(
        WatchlistItem(
            symbol=symbol,
            threshold_pct=thr,
            user_id=body.user_id or "default",
        )
    )
    return _to_out(saved)


@router.patch("/watchlist/{symbol}", response_model=WatchlistItemOut)
def patch_watchlist(
    symbol: str,
    body: UpdateWatchlistRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> WatchlistItemOut:
    sym = normalize_symbol(symbol)
    user_id = body.user_id or "default"
    existing = deps.watchlist_store.get(user_id, sym)
    if existing is None:
        raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
    thr = validate_threshold_pct(body.threshold_pct, required=True)
    assert thr is not None
    saved = deps.watchlist_store.upsert(
        WatchlistItem(
            symbol=sym,
            threshold_pct=thr,
            user_id=user_id,
        )
    )
    return _to_out(saved)


@router.delete("/watchlist/{symbol}")
def delete_watchlist(
    symbol: str,
    user_id: str = Query(default="default"),
    deps: AppDeps = Depends(get_app_deps),
) -> dict[str, object]:
    sym = normalize_symbol(symbol)
    ok = deps.watchlist_store.delete(user_id, sym)
    if not ok:
        raise HTTPException(status_code=404, detail="không tìm thấy mã trong watchlist")
    return {"ok": True, "symbol": sym, "user_id": user_id}
