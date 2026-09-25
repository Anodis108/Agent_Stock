"""POST /scan — quét giám sát 1 mã."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.deps import AppDeps, get_app_deps
from backend.api.helpers.validation import (
    normalize_symbol,
    validate_threshold_pct,
)
from backend.application.scan_symbol import scan_symbol

router = APIRouter(tags=["scan"])


class ScanRequest(BaseModel):
    symbol: str = Field(description="Mã chứng khoán VN")
    user_id: str = "default"
    threshold_pct: float | None = Field(
        default=None, description="Ghi đè ngưỡng %; None = lấy watchlist"
    )


class ScanResponse(BaseModel):
    symbol: str
    route: str
    reason: str = ""
    threshold_pct: float
    gate1_action: str | None = None
    gate2_pending: bool = False
    error: str | None = None
    price: dict[str, Any]
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    pending_events: list[dict[str, Any]] = Field(default_factory=list)


def _route_value(route: Any) -> str:
    return str(getattr(route, "value", route))


@router.post("/scan", response_model=ScanResponse)
@router.post("/api/v1/scan", response_model=ScanResponse)
@router.post("/api/scan", response_model=ScanResponse)
def post_scan(
    body: ScanRequest,
    deps: AppDeps = Depends(get_app_deps),
) -> ScanResponse:
    symbol = normalize_symbol(body.symbol)
    thr = validate_threshold_pct(body.threshold_pct)

    result = scan_symbol(
        symbol,
        price_source=deps.price_source,
        news_source=deps.news_source,
        history_store=deps.history_store,
        memory_store=deps.memory_store,
        notifier=deps.notifier,
        watchlist_store=deps.watchlist_store,
        user_id=body.user_id,
        threshold_pct=thr,
    )

    news_items = [
        {
            "title": i.title,
            "url": i.url,
            "published_at": i.published_at,
            "snippet": i.snippet,
        }
        for i in (result.news.items or [])
    ]
    price = result.price
    return ScanResponse(
        symbol=result.symbol,
        route=_route_value(result.routing.route),
        reason=result.routing.reason or "",
        threshold_pct=result.threshold_pct,
        gate1_action=result.gate1_action,
        gate2_pending=result.gate2_pending,
        error=result.error,
        price={
            "symbol": price.symbol,
            "latest_close": price.latest_close,
            "prev_close": price.prev_close,
            "change_pct": price.change_pct,
            "error": price.error,
        },
        news_count=len(news_items),
        news=news_items,
        news_error=result.news.error,
        severity=(
            result.severity.model_dump(mode="json") if result.severity else None
        ),
        alert=(result.alert.model_dump(mode="json") if result.alert else None),
        pending_events=list(result.pending_events),
    )
