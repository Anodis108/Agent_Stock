"""Pydantic schemas for AI Backend Symbol Technical Scanner (POST /v1/scan)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from ai_backend.api.models.stream_models import HoldingSnapshot, WatchlistSnapshot
from common.base.base_model import CustomBaseModel


class ScanRequest(CustomBaseModel):
    """Yêu cầu quét tín hiệu kỹ thuật gửi tới AI Backend (POST /v1/scan)."""
    symbol: str = Field(description="Mã chứng khoán cần quét")
    user_id: str = Field(default="default", description="Mã định danh người dùng")
    threshold_pct: float | None = Field(default=None, description="Ngưỡng cảnh báo biến động %")
    request_id: str | None = Field(default=None, description="Mã tương quan yêu cầu")
    watchlist: list[WatchlistSnapshot] | None = Field(
        default=None, description="Ảnh chụp danh mục theo dõi"
    )
    holdings: list[HoldingSnapshot] | None = Field(
        default=None, description="Ảnh chụp danh mục nắm giữ"
    )


class ScanAlertOut(CustomBaseModel):
    """Chi tiết cảnh báo kỹ thuật của một mã."""
    symbol: str
    route: str = "market"
    price: dict[str, Any] | None = None
    change_pct: float = 0.0
    threshold_pct: float = 3.0
    triggered: bool = False
    reason: str = ""


class ScanResponse(CustomBaseModel):
    """Kết quả phân tích và quét cảnh báo trả về từ AI Backend."""
    symbol: str
    route: str = "market"
    alerts: list[ScanAlertOut] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""
    threshold_pct: float = 0.0
    gate1_action: str | None = None
    gate2_pending: bool = False
    error: str | None = None
    request_id: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    pending_events: list[dict[str, Any]] = Field(default_factory=list)
