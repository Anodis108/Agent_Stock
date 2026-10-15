"""Pydantic schemas for Web Portfolio API."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from common.base.base_model import CustomBaseModel


class CreateHoldingRequest(CustomBaseModel):
    symbol: str = Field(description="Mã chứng khoán")
    quantity: int = Field(gt=0, description="Số lượng cổ phiếu nắm giữ")
    buy_price: float = Field(default=0.0, description="Giá vốn bình quân (nghìn VNĐ)")
    avg_buy_price: float | None = Field(default=None, description="Giá vốn bình quân alias")
    buy_date: str | None = Field(default=None, description="Ngày mua (YYYY-MM-DD)")
    notes: str | None = Field(default=None, description="Ghi chú vị thế")

    @model_validator(mode="before")
    @classmethod
    def resolve_buy_price(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if ("buy_price" not in data or data.get("buy_price") is None) and "avg_buy_price" in data:
                data["buy_price"] = data["avg_buy_price"]
        return data


class HoldingOut(CustomBaseModel):
    id: int | str
    user_id: str
    symbol: str
    quantity: int | float
    buy_price: float
    avg_buy_price: float | None = None
    buy_date: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def resolve_avg_buy_price(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "avg_buy_price" not in data and "buy_price" in data:
                data["avg_buy_price"] = data["buy_price"]
        return data


class PortfolioItemOut(CustomBaseModel):
    holding: HoldingOut
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight_pct: float = 0.0
    alert_triggered: bool = False


class PortfolioSummaryOut(CustomBaseModel):
    user_id: str
    total_cost: float
    total_market_value: float
    total_pnl: float
    total_pnl_pct: float
    total_nav: float = 0.0
    items: list[PortfolioItemOut] = Field(default_factory=list)
    as_of: str | None = None

    @model_validator(mode="before")
    @classmethod
    def resolve_total_nav(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "total_nav" not in data or data.get("total_nav") == 0.0:
                data["total_nav"] = data.get("total_market_value", 0.0)
        return data


class UserSettingsOut(CustomBaseModel):
    user_id: str
    alert_threshold_pct: float
    risk_profile: str = "moderate"
    updated_at: str | None = None


class UpdateUserSettingsRequest(CustomBaseModel):
    alert_threshold_pct: float | None = Field(
        default=None, description="Ngưỡng cảnh báo lỗ %"
    )
    risk_profile: str | None = Field(
        default=None, description="Khẩu vị rủi ro: conservative, moderate, aggressive"
    )
