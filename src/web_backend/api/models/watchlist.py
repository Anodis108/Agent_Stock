"""Pydantic schemas for Web Watchlist API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class WatchlistItemOut(CustomBaseModel):
    symbol: str
    threshold_pct: float
    alert_threshold_pct: float | None = None
    user_id: str = "default"

    def model_post_init(self, __context: Any) -> None:
        if self.alert_threshold_pct is None:
            self.alert_threshold_pct = self.threshold_pct


class WatchlistListResponse(CustomBaseModel):
    items: list[WatchlistItemOut] = Field(default_factory=list)
    count: int = 0


class CreateWatchlistRequest(CustomBaseModel):
    symbol: str = Field(description="Mã chứng khoán VN")
    threshold_pct: float | None = Field(
        default=None, description="None = ngưỡng mặc định"
    )
    alert_threshold_pct: float | None = Field(
        default=None, description="Ngưỡng cảnh báo biến động %"
    )
    user_id: str = "default"


class UpdateWatchlistRequest(CustomBaseModel):
    threshold_pct: float | None = None
    alert_threshold_pct: float | None = None
    user_id: str = "default"
