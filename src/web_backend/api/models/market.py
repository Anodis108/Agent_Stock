"""Pydantic schemas for Web Market Status API."""

from __future__ import annotations

from pydantic import Field

from common.base.base_model import CustomBaseModel


class MarketSessionOut(CustomBaseModel):
    session_type: str
    start_time: str
    end_time: str
    is_active: bool = False
    description: str = ""


class MarketMatrixItemOut(CustomBaseModel):
    symbol: str
    price: float
    change_pct: float
    rsi: float | None = None
    signal: str = "NEUTRAL"


class MarketMatrixResponse(CustomBaseModel):
    sessions: list[MarketSessionOut] = Field(default_factory=list)
    items: list[MarketMatrixItemOut] = Field(default_factory=list)
