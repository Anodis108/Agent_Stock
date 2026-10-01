"""Portfolio & User Settings Router — Quản lý Danh mục P&L và Đa người dùng (MVP 2.0).

Endpoints:
- GET    /api/portfolio             : Xem tổng quan danh mục và chi tiết P&L theo user_id.
- POST   /api/portfolio/holdings    : Thêm vị thế nắm giữ cổ phiếu mới.
- DELETE /api/portfolio/holdings/{id}: Xóa vị thế nắm giữ.
- GET    /api/user/settings         : Lấy thông tin cài đặt (ngưỡng cảnh báo) của người dùng.
- PUT    /api/user/settings         : Cập nhật ngưỡng cảnh báo của người dùng.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from backend.api.helpers.validation import normalize_symbol
from backend.application.portfolio_service import (
    PortfolioItemSummary,
    PortfolioService,
    PortfolioSummary,
)
from backend.database.connection import get_connection
from backend.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from backend.shared.settings import settings

router = APIRouter(tags=["portfolio"])


# ==============================================================================
# Helper & Dependency Injection
# ==============================================================================


def get_portfolio_service(deps: AppDeps = Depends(get_app_deps)) -> PortfolioService:
    """Khởi tạo PortfolioService với dependencies được tiêm từ AppDeps."""
    if deps.holdings_repo is not None and deps.user_settings_repo is not None:
        holdings_repo = deps.holdings_repo
        user_settings_repo = deps.user_settings_repo
    else:
        import os
        db_path = os.environ.get("SQLITE_PATH") or settings.sqlite_path
        conn = get_connection(db_path)
        holdings_repo = deps.holdings_repo or PortfolioHoldingRepository(conn)
        user_settings_repo = deps.user_settings_repo or UserSettingsRepository(conn)
    return PortfolioService(
        holdings_repo=holdings_repo,
        user_settings_repo=user_settings_repo,
        price_source=deps.price_source,
    )


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class CreateHoldingRequest(BaseModel):
    """Schema yêu cầu thêm vị thế cổ phiếu vào danh mục."""

    symbol: str = Field(description="Mã chứng khoán")
    quantity: int = Field(gt=0, description="Số lượng cổ phiếu nắm giữ (phải > 0)")
    avg_buy_price: float = Field(gt=0, description="Giá mua bình quân (VND hoặc nghìn VND)")
    purchase_date: str | None = Field(default=None, description="Ngày mua (YYYY-MM-DD)")


class HoldingOut(BaseModel):
    """Schema xuất vị thế cổ phiếu vừa thêm."""

    id: str
    user_id: str
    symbol: str
    quantity: int
    avg_buy_price: float
    purchase_date: str | None
    created_at: str | None


class PortfolioItemOut(BaseModel):
    """Schema chi tiết từng mã trong bảng P&L."""

    id: str
    user_id: str
    symbol: str
    quantity: int
    avg_buy_price: float
    purchase_date: str | None
    current_price: float | None
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    pnl_pct: float
    price_error: bool = False


class PortfolioSummaryOut(BaseModel):
    """Schema tổng quan danh mục P&L."""

    user_id: str
    total_nav: float
    total_cost: float
    total_unrealized_pnl: float
    total_pnl_pct: float
    count: int
    items: list[PortfolioItemOut] = Field(default_factory=list)


class UserSettingsOut(BaseModel):
    """Schema cài đặt của người dùng."""

    user_id: str
    alert_threshold_pct: float


class UpdateUserSettingsRequest(BaseModel):
    """Schema cập nhật cài đặt người dùng."""

    alert_threshold_pct: float = Field(
        gt=0.0, le=50.0, description="Ngưỡng cảnh báo biến động (0 < threshold <= 50%)"
    )


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.get("/api/portfolio", response_model=PortfolioSummaryOut)
@router.get("/api/v1/portfolio", response_model=PortfolioSummaryOut)
@router.get("/api/v1/portfolio/summary", response_model=PortfolioSummaryOut)
def get_portfolio(
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioSummaryOut:
    """Lấy tổng quan danh mục và chi tiết P&L của người dùng hiện tại."""
    summary = svc.get_portfolio_summary(user_id=user_id)
    return PortfolioSummaryOut(**summary.as_dict())


@router.get("/api/portfolio/holdings", response_model=list[PortfolioItemOut])
@router.get("/api/v1/portfolio/holdings", response_model=list[PortfolioItemOut])
def get_portfolio_holdings(
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> list[PortfolioItemOut]:
    """Lấy danh sách các vị thế cổ phiếu trong danh mục của người dùng."""
    summary = svc.get_portfolio_summary(user_id=user_id)
    return [PortfolioItemOut(**item.as_dict()) for item in summary.items]


@router.post(
    "/api/portfolio/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/api/v1/portfolio/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_holding(
    body: CreateHoldingRequest,
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> HoldingOut:
    """Thêm một vị thế cổ phiếu mới vào danh mục của người dùng."""
    symbol = normalize_symbol(body.symbol)
    record = svc.add_holding(
        symbol=symbol,
        quantity=body.quantity,
        avg_buy_price=body.avg_buy_price,
        purchase_date=body.purchase_date,
        user_id=user_id,
    )
    return HoldingOut(
        id=record.id,
        user_id=record.user_id,
        symbol=record.symbol,
        quantity=record.quantity,
        avg_buy_price=record.avg_buy_price,
        purchase_date=record.purchase_date,
        created_at=record.created_at,
    )


@router.delete("/api/portfolio/holdings/{holding_id}")
@router.delete("/api/v1/portfolio/holdings/{holding_id}")
def delete_holding(
    holding_id: str,
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> dict[str, Any]:
    """Xóa vị thế cổ phiếu khỏi danh mục."""
    success = svc.delete_holding(holding_id=holding_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vị thế #{holding_id} thuộc về user '{user_id}'",
        )
    return {"ok": True, "holding_id": holding_id, "user_id": user_id}



@router.get("/api/user/settings", response_model=UserSettingsOut)
def get_user_settings(
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> UserSettingsOut:
    """Lấy cài đặt người dùng (ngưỡng cảnh báo biến động riêng)."""
    settings_rec = svc.get_user_settings(user_id=user_id)
    return UserSettingsOut(
        user_id=settings_rec.user_id,
        alert_threshold_pct=settings_rec.alert_threshold_pct,
    )


@router.put("/api/user/settings", response_model=UserSettingsOut)
def update_user_settings(
    body: UpdateUserSettingsRequest,
    user_id: str = Depends(get_current_user_id),
    svc: PortfolioService = Depends(get_portfolio_service),
) -> UserSettingsOut:
    """Cập nhật cài đặt người dùng."""
    updated = svc.update_alert_threshold(
        threshold_pct=body.alert_threshold_pct,
        user_id=user_id,
    )
    return UserSettingsOut(
        user_id=updated.user_id,
        alert_threshold_pct=updated.alert_threshold_pct,
    )
