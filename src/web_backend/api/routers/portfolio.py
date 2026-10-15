"""Portfolio & User Settings Router for Web Backend."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from common.logging.logger import get_logger
from web_backend.api.deps import AppDeps, get_app_deps, get_current_user_id
from web_backend.api.helpers.validation import normalize_symbol
from web_backend.api.models.portfolio import (
    CreateHoldingRequest,
    HoldingOut,
    PortfolioItemOut,
    PortfolioSummaryOut,
    UpdateUserSettingsRequest,
    UserSettingsOut,
)

logger = get_logger("web_backend.api.routers.portfolio")
router = APIRouter(tags=["portfolio"])

from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)

try:
    from web_backend.application.portfolio_service import (
        PortfolioItemSummary,
        PortfolioService,
        PortfolioSummary,
    )
except ImportError:
    PortfolioService = None



def get_portfolio_service(deps: AppDeps = Depends(get_app_deps)) -> Any:
    """Khởi tạo PortfolioService với dependencies được tiêm từ AppDeps."""
    if deps.holdings_repo is not None and deps.user_settings_repo is not None:
        holdings_repo = deps.holdings_repo
        user_settings_repo = deps.user_settings_repo
    else:
        conn = get_connection()
        holdings_repo = deps.holdings_repo or PortfolioHoldingRepository(conn)
        user_settings_repo = deps.user_settings_repo or UserSettingsRepository(conn)

    if PortfolioService is not None:
        return PortfolioService(
            holdings_repo=holdings_repo,
            user_settings_repo=user_settings_repo,
            price_source=deps.price_source,
        )
    return None


@router.get(
    "/api/portfolio",
    response_model=PortfolioSummaryOut,
    summary="Xem tổng quan danh mục đầu tư và P&L",
)
@router.get(
    "/portfolio",
    response_model=PortfolioSummaryOut,
    summary="Xem tổng quan danh mục đầu tư và P&L (alias)",
)
@router.get(
    "/api/v1/portfolio/summary",
    response_model=PortfolioSummaryOut,
    summary="Xem tổng quan danh mục đầu tư (v1 alias)",
)
@router.get(
    "/api/v1/portfolio",
    response_model=PortfolioSummaryOut,
    summary="Xem tổng quan danh mục đầu tư (v1)",
)
def get_portfolio(
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> PortfolioSummaryOut:
    """Lấy danh sách các vị thế, tính toán chi phí vốn, giá trị thị trường và P&L."""
    if service is None:
        return PortfolioSummaryOut(
            user_id=current_user_id,
            total_cost=0.0,
            total_market_value=0.0,
            total_nav=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            items=[],
        )

    summary = service.get_portfolio_summary(user_id=current_user_id)
    items_out = []
    for it in summary.items:
        h = getattr(it, "holding", it)
        price_val = float(getattr(h, "avg_buy_price", getattr(h, "buy_price", 0.0)))
        holding_out = HoldingOut(
            id=getattr(h, "id", ""),
            user_id=getattr(h, "user_id", current_user_id),
            symbol=getattr(h, "symbol", ""),
            quantity=getattr(h, "quantity", 0),
            buy_price=price_val,
            avg_buy_price=price_val,
            buy_date=getattr(h, "purchase_date", getattr(h, "buy_date", None)),
            notes=getattr(h, "notes", None),
            created_at=getattr(h, "created_at", None),
            updated_at=getattr(h, "updated_at", None),
        )
        items_out.append(
            PortfolioItemOut(
                holding=holding_out,
                current_price=getattr(it, "current_price", 0.0) or 0.0,
                cost_basis=getattr(it, "cost_basis", 0.0) or 0.0,
                market_value=getattr(it, "market_value", 0.0) or 0.0,
                unrealized_pnl=getattr(it, "unrealized_pnl", 0.0) or 0.0,
                unrealized_pnl_pct=getattr(it, "pnl_pct", getattr(it, "unrealized_pnl_pct", 0.0)) or 0.0,
                weight_pct=getattr(it, "weight_pct", 0.0),
                alert_triggered=getattr(it, "alert_triggered", False),
            )
        )
    tot_nav = float(getattr(summary, "total_nav", getattr(summary, "total_market_value", 0.0)))
    tot_pnl = float(getattr(summary, "total_unrealized_pnl", getattr(summary, "total_pnl", 0.0)))
    return PortfolioSummaryOut(
        user_id=summary.user_id,
        total_cost=float(getattr(summary, "total_cost", 0.0)),
        total_market_value=tot_nav,
        total_nav=tot_nav,
        total_pnl=tot_pnl,
        total_pnl_pct=float(getattr(summary, "total_pnl_pct", 0.0)),
        items=items_out,
        as_of=getattr(summary, "as_of", None),
    )


@router.get(
    "/api/portfolio/holdings",
    summary="Lấy danh sách các vị thế cổ phiếu trong danh mục",
)
@router.get(
    "/portfolio/holdings",
    summary="Lấy danh sách các vị thế cổ phiếu trong danh mục (alias)",
)
def list_holdings(
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> dict[str, Any]:
    """Trả về danh sách các vị thế nắm giữ của user."""
    if service is None:
        return {"items": [], "count": 0}
    summary = service.get_portfolio_summary(user_id=current_user_id)
    raw_holdings = []
    for it in summary.items:
        h = getattr(it, "holding", it)
        price_val = float(getattr(h, "avg_buy_price", getattr(h, "buy_price", 0.0)))
        raw_holdings.append(
            {
                "id": getattr(h, "id", ""),
                "user_id": getattr(h, "user_id", current_user_id),
                "symbol": getattr(h, "symbol", ""),
                "quantity": getattr(h, "quantity", 0),
                "buy_price": price_val,
                "avg_buy_price": price_val,
                "buy_date": getattr(h, "purchase_date", getattr(h, "buy_date", None)),
                "notes": getattr(h, "notes", None),
            }
        )
    return {"items": raw_holdings, "count": len(raw_holdings)}


@router.get(
    "/api/v1/portfolio/holdings",
    summary="Lấy danh sách các vị thế cổ phiếu trong danh mục (v1 dạng list)",
)
def list_holdings_v1(
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> list[dict[str, Any]]:
    """Trả về danh sách dạng list cho API v1."""
    res = list_holdings(current_user_id=current_user_id, service=service)
    return res.get("items", [])


@router.post(
    "/api/portfolio/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_200_OK,
    summary="Thêm mới vị thế cổ phiếu vào danh mục",
)
@router.post(
    "/api/v1/portfolio/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_200_OK,
    summary="Thêm mới vị thế cổ phiếu vào danh mục (v1)",
)
@router.post(
    "/portfolio/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_200_OK,
    summary="Thêm mới vị thế cổ phiếu vào danh mục (alias)",
)
def add_holding(
    req: CreateHoldingRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> HoldingOut:
    """Thêm một vị thế cổ phiếu cho user hiện tại."""
    symbol = normalize_symbol(req.symbol)
    if service is None:
        raise HTTPException(status_code=500, detail="Portfolio service unavailable")

    try:
        price = req.buy_price if req.buy_price else (req.avg_buy_price or 0.0)
        record = service.add_holding(
            user_id=current_user_id,
            symbol=symbol,
            quantity=req.quantity,
            avg_buy_price=price,
            buy_price=price,
            buy_date=req.buy_date,
            notes=req.notes,
        )
        rec_price = float(getattr(record, "buy_price", getattr(record, "avg_buy_price", price)))
        return HoldingOut(
            id=record.id,
            user_id=record.user_id,
            symbol=record.symbol,
            quantity=record.quantity,
            buy_price=rec_price,
            avg_buy_price=rec_price,
            buy_date=getattr(record, "purchase_date", getattr(record, "buy_date", req.buy_date)),
            notes=getattr(record, "notes", req.notes),
            created_at=getattr(record, "created_at", None),
            updated_at=getattr(record, "updated_at", None),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/api/portfolio/holdings/{holding_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa vị thế cổ phiếu khỏi danh mục",
)
def delete_holding(
    holding_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> dict[str, Any]:
    """Xóa vị thế theo ID. Chỉ user sở hữu vị thế mới được phép xóa."""
    if service is None:
        raise HTTPException(status_code=500, detail="Portfolio service unavailable")

    deleted = service.delete_holding(holding_id=holding_id, user_id=current_user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vị thế ID {holding_id} của user '{current_user_id}'.",
        )
    return {"status": "success", "ok": True, "deleted_id": holding_id}


@router.get(
    "/api/user/settings",
    response_model=UserSettingsOut,
    summary="Lấy cài đặt người dùng",
)
def get_user_settings(
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> UserSettingsOut:
    """Lấy thông tin ngưỡng cảnh báo và khẩu vị rủi ro của người dùng."""
    if service is None:
        return UserSettingsOut(
            user_id=current_user_id,
            alert_threshold_pct=7.0,
            risk_profile="moderate",
        )

    s = service.get_user_settings(user_id=current_user_id)
    return UserSettingsOut(
        user_id=s.user_id,
        alert_threshold_pct=s.alert_threshold_pct,
        risk_profile=s.risk_profile,
        updated_at=s.updated_at,
    )


@router.put(
    "/api/user/settings",
    response_model=UserSettingsOut,
    summary="Cập nhật cài đặt người dùng",
)
def update_user_settings(
    req: UpdateUserSettingsRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: Any = Depends(get_portfolio_service),
) -> UserSettingsOut:
    """Cập nhật ngưỡng cảnh báo rủi ro % hoặc khẩu vị rủi ro."""
    if service is None:
        raise HTTPException(status_code=500, detail="Portfolio service unavailable")

    try:
        s = service.update_user_settings(
            user_id=current_user_id,
            alert_threshold_pct=req.alert_threshold_pct,
            risk_profile=req.risk_profile,
        )
        return UserSettingsOut(
            user_id=s.user_id,
            alert_threshold_pct=s.alert_threshold_pct,
            risk_profile=s.risk_profile,
            updated_at=s.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
