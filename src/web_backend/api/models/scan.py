"""Pydantic schemas for Web Scan API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from common.base.base_model import CustomBaseModel


class ScanRequest(CustomBaseModel):
    symbols: list[str] = Field(
        default_factory=list,
        description="Danh sách mã cổ phiếu cần quét. Để trống để quét mặc định.",
    )
    threshold_pct: float = Field(
        default=3.0,
        description="Ngưỡng biến động giá cảnh báo (%)",
    )


class ScanResponse(CustomBaseModel):
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
