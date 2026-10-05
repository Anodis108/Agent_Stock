"""Portfolio Service — Tính toán Lãi/Lỗ Danh Mục và Quản lý Vị Thế (MVP 2.0).

Nhiệm vụ:
- Lấy danh sách vị thế nắm giữ (holdings) của người dùng từ PortfolioHoldingRepository.
- Kết nối PriceSource lấy giá thị trường mới nhất.
- Chuẩn hóa đơn vị VND và tính toán: Market Value, Cost Basis, Unrealized P&L (VND), Tỷ suất (%), Tổng NAV.
- Xử lý lỗi an toàn nếu có mã không lấy được thị giá (graceful fallback).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.database.repositories import (
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    UserSettingsRecord,
    UserSettingsRepository,
)
from backend.domain.ports import PriceSource


@dataclass(slots=True)
class PortfolioItemSummary:
    """Tóm tắt vị thế nắm giữ của một mã cổ phiếu."""

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_buy_price": self.avg_buy_price,
            "purchase_date": self.purchase_date,
            "current_price": self.current_price,
            "cost_basis": round(self.cost_basis, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "price_error": self.price_error,
        }


@dataclass(slots=True)
class PortfolioSummary:
    """Tổng quan danh mục đầu tư và P&L của người dùng."""

    user_id: str
    total_nav: float
    total_cost: float
    total_unrealized_pnl: float
    total_pnl_pct: float
    items: list[PortfolioItemSummary]
    count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_nav": round(self.total_nav, 2),
            "total_cost": round(self.total_cost, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "count": self.count,
            "items": [item.as_dict() for item in self.items],
        }


class PortfolioService:
    """Service tính toán lãi lỗ và điều phối danh mục đầu tư."""

    def __init__(
        self,
        holdings_repo: PortfolioHoldingRepository,
        user_settings_repo: UserSettingsRepository,
        price_source: PriceSource,
    ) -> None:
        self.holdings_repo = holdings_repo
        self.user_settings_repo = user_settings_repo
        self.price_source = price_source

    @staticmethod
    def _normalize_price_vnd(price: float | None) -> float | None:
        """Chuẩn hóa giá về đơn vị VND đầy đủ.
        
        Nếu giá <= 1000 (quy ước nghìn VND của bảng giá/Vnstock, vd 66.0, 120.0),
        nhân 1,000 để thành VND (66,000 VND, 120,000 VND).
        """
        if price is None:
            return None
        return float(price * 1000.0 if price <= 1000.0 else price)

    def get_portfolio_summary(self, user_id: str = "default") -> PortfolioSummary:
        """Lấy tổng quan danh mục và chi tiết P&L cho user_id."""
        holdings = self.holdings_repo.list_by_user(user_id)
        items: list[PortfolioItemSummary] = []

        total_cost = 0.0
        total_market_value = 0.0

        for h in holdings:
            avg_price_vnd = self._normalize_price_vnd(h.avg_buy_price) or 0.0
            cost_basis = float(h.quantity) * avg_price_vnd

            quote = self.price_source.fetch_latest_close(h.symbol)
            cur_price_raw = quote.latest_close
            has_error = quote.error is not None or cur_price_raw is None

            if has_error or cur_price_raw is None:
                # Fallback an toàn: giữ nguyên giá vốn, không tính lãi/lỗ ảo
                cur_price_vnd = None
                market_val = cost_basis
                pnl = 0.0
                pnl_pct = 0.0
                price_err = True
            else:
                cur_price_vnd = self._normalize_price_vnd(cur_price_raw)
                market_val = float(h.quantity) * (cur_price_vnd or 0.0)
                pnl = market_val - cost_basis
                pnl_pct = ((pnl / cost_basis) * 100.0) if cost_basis > 0 else 0.0
                price_err = False

            total_cost += cost_basis
            total_market_value += market_val

            items.append(
                PortfolioItemSummary(
                    id=h.id,
                    user_id=h.user_id,
                    symbol=h.symbol,
                    quantity=h.quantity,
                    avg_buy_price=h.avg_buy_price,
                    purchase_date=h.purchase_date,
                    current_price=cur_price_raw,
                    cost_basis=cost_basis,
                    market_value=market_val,
                    unrealized_pnl=pnl,
                    pnl_pct=pnl_pct,
                    price_error=price_err,
                )
            )

        total_pnl = total_market_value - total_cost
        total_pnl_pct = ((total_pnl / total_cost) * 100.0) if total_cost > 0 else 0.0

        return PortfolioSummary(
            user_id=user_id,
            total_nav=total_market_value,
            total_cost=total_cost,
            total_unrealized_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            items=items,
            count=len(items),
        )

    def add_holding(
        self,
        symbol: str,
        quantity: int,
        avg_buy_price: float,
        purchase_date: str | None = None,
        user_id: str = "default",
    ) -> PortfolioHoldingRecord:
        """Thêm mới vị thế cổ phiếu vào danh mục."""
        return self.holdings_repo.create(
            user_id=user_id,
            symbol=symbol.upper().strip(),
            quantity=quantity,
            avg_buy_price=avg_buy_price,
            purchase_date=purchase_date,
        )

    def delete_holding(self, holding_id: str, user_id: str = "default") -> bool:
        """Xóa vị thế cổ phiếu nếu thuộc về user_id."""
        existing = self.holdings_repo.get(holding_id)
        if existing is None or existing.user_id != user_id:
            return False
        return self.holdings_repo.delete(holding_id)

    def get_user_settings(self, user_id: str = "default") -> UserSettingsRecord:
        """Lấy cài đặt người dùng."""
        return self.user_settings_repo.get(user_id)

    def update_alert_threshold(
        self, threshold_pct: float, user_id: str = "default"
    ) -> UserSettingsRecord:
        """Cập nhật ngưỡng cảnh báo của người dùng."""
        return self.user_settings_repo.set_threshold(user_id, threshold_pct)
