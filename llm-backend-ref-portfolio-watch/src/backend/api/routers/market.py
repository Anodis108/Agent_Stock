"""REST API router for Market Watch Matrix (10D) in Portfolio Watch V4.

Provides endpoints:
- GET /api/v1/market/matrix-10d : Return 10-day matrix data for 10 key tickers
  including closing prices, daily % changes, trading volumes, and SVG sparkline series.
- GET /api/market/matrix-10d    : Convenience alias route
- GET /market/matrix-10d        : Direct root alias
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.database.connection import get_connection
from backend.services.market_service import DEFAULT_MARKET_SYMBOLS, get_market_service

router = APIRouter(prefix="/api/v1/market", tags=["market"])
alias_router = APIRouter(prefix="/api/market", tags=["market-alias"])
direct_router = APIRouter(prefix="/market", tags=["market-direct"])


class MarketSessionOut(BaseModel):
    """Daily OHLCV session details for a single trading day."""

    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: int | None = None
    change_pct: float | None = None


class MarketMatrixItemOut(BaseModel):
    """Matrix item representing 10-day historical progression for a single stock."""

    symbol: str
    current_price: float
    change_pct: float | None = None
    total_volume: int = 0
    sparkline: list[float] = Field(default_factory=list)
    sessions: list[MarketSessionOut] = Field(default_factory=list)


class MarketMatrixResponse(BaseModel):
    """Payload for 10-day market watch matrix."""

    items: list[MarketMatrixItemOut] = Field(default_factory=list)
    count: int = 0
    updated_at: str


def _get_matrix_data(
    symbols_raw: str | None = None,
    days: int = 10,
    auto_sync: bool = True,
) -> MarketMatrixResponse:
    """Core handler to fetch and compute matrix data from SQLite via MarketService."""
    target_symbols = None
    if symbols_raw:
        parsed = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        if parsed:
            target_symbols = parsed

    conn = get_connection()
    try:
        from backend.api.deps import get_app_deps
        service = get_market_service(conn, price_source=get_app_deps().price_source)
        raw_items = service.get_matrix_10d(symbols=target_symbols, days=days, auto_sync=auto_sync)

        items = [
            MarketMatrixItemOut(
                symbol=item["symbol"],
                current_price=item["current_price"],
                change_pct=item["change_pct"],
                total_volume=item["total_volume"],
                sparkline=item["sparkline"],
                sessions=[
                    MarketSessionOut(
                        date=s["date"],
                        open=s["open"],
                        high=s["high"],
                        low=s["low"],
                        close=s["close"],
                        volume=s["volume"],
                        change_pct=s["change_pct"],
                    )
                    for s in item["sessions"]
                ],
            )
            for item in raw_items
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        return MarketMatrixResponse(items=items, count=len(items), updated_at=now_iso)
    finally:
        conn.close()


# /api/v1/market/matrix-10d
@router.get("/matrix-10d", response_model=MarketMatrixResponse)
def get_matrix_10d(
    symbols: str | None = Query(
        default=None,
        description="Comma-separated ticker list. If omitted, defaults to 10 key tickers.",
    ),
    days: int = Query(default=10, ge=1, le=60, description="Number of trading sessions."),
    auto_sync: bool = Query(default=True, description="Automatically sync history if cache is empty."),
) -> MarketMatrixResponse:
    return _get_matrix_data(symbols_raw=symbols, days=days, auto_sync=auto_sync)


# /api/market/matrix-10d
@alias_router.get("/matrix-10d", response_model=MarketMatrixResponse)
def alias_get_matrix_10d(
    symbols: str | None = Query(default=None),
    days: int = Query(default=10, ge=1, le=60),
    auto_sync: bool = Query(default=True),
) -> MarketMatrixResponse:
    return _get_matrix_data(symbols_raw=symbols, days=days, auto_sync=auto_sync)


# /market/matrix-10d
@direct_router.get("/matrix-10d", response_model=MarketMatrixResponse)
def direct_get_matrix_10d(
    symbols: str | None = Query(default=None),
    days: int = Query(default=10, ge=1, le=60),
    auto_sync: bool = Query(default=True),
) -> MarketMatrixResponse:
    return _get_matrix_data(symbols_raw=symbols, days=days, auto_sync=auto_sync)
