"""Portfolio Application Service for Web Backend — Tính toán P&L danh mục đầu tư theo chuẩn BaseService."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.logging.logger import get_logger

logger = get_logger("web_backend.application.portfolio")

from web_backend.infra.database.repositories import (
    PortfolioHoldingRecord,
    PortfolioHoldingRepository,
    UserSettingsRecord,
    UserSettingsRepository,
)
from common.domain.ports import IPriceSource as PriceSource

from web_backend.domain.portfolio_calculator import PortfolioCalculator


@dataclass(slots=True)
class PortfolioItemSummary:
    """Tóm tắt vị thế nắm giữ của một mã cổ phiếu."""

    id: str | int
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


class PortfolioInput(CustomBaseModel):
    user_id: str = "default"
    action: str = "summary"  # "summary" | "add" | "delete" | "settings"
    symbol: str | None = None
    quantity: int | None = None
    buy_price: float | None = None
    holding_id: str | int | None = None
    alert_threshold_pct: float | None = None
    risk_profile: str | None = None


class PortfolioOutput(CustomBaseModel):
    user_id: str
    total_nav: float = 0.0
    total_cost: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    count: int = 0
    items: list[dict[str, Any]] = []
    message: str = ""


class PortfolioService(BaseService):
    """Service tính toán lãi/lỗ danh mục đầu tư kế thừa BaseService."""

    def __init__(
        self,
        holdings_repo: Any,
        user_settings_repo: Any,
        price_source: Any,
    ) -> None:
        self.holdings_repo = holdings_repo
        self.user_settings_repo = user_settings_repo
        self.price_source = price_source

    @staticmethod
    def _normalize_price_vnd(price: float | None) -> float | None:
        """Chuẩn hóa giá về đơn vị VND đầy đủ thông qua PortfolioCalculator."""
        return PortfolioCalculator.normalize_price_vnd(price)

    def process(self, inputs: PortfolioInput) -> PortfolioOutput:
        """Xử lý use-case chính theo chuẩn BaseService."""
        user_id = inputs.user_id or "default"

        if inputs.action == "add" and inputs.symbol and inputs.quantity and inputs.buy_price:
            self.add_holding(
                symbol=inputs.symbol,
                quantity=inputs.quantity,
                avg_buy_price=inputs.buy_price,
                user_id=user_id,
            )
        elif inputs.action == "delete" and inputs.holding_id is not None:
            self.delete_holding(str(inputs.holding_id), user_id=user_id)
        elif inputs.action == "settings" and inputs.alert_threshold_pct is not None:
            self.update_user_settings(
                user_id=user_id,
                alert_threshold_pct=inputs.alert_threshold_pct,
                risk_profile=inputs.risk_profile,
            )

        summary = self.get_portfolio_summary(user_id=user_id)
        return PortfolioOutput(
            user_id=summary.user_id,
            total_nav=summary.total_nav,
            total_cost=summary.total_cost,
            total_unrealized_pnl=summary.total_unrealized_pnl,
            total_pnl_pct=summary.total_pnl_pct,
            count=summary.count,
            items=[it.as_dict() for it in summary.items],
            message="Thành công",
        )

    def get_portfolio_summary(self, user_id: str = "default") -> PortfolioSummary:
        """Lấy tổng quan danh mục và chi tiết P&L cho user_id."""
        holdings = self.holdings_repo.list_by_user(user_id) if hasattr(self.holdings_repo, "list_by_user") else []
        items: list[PortfolioItemSummary] = []

        total_cost = 0.0
        total_market_value = 0.0

        for h in holdings:
            avg_price_raw = getattr(h, "avg_buy_price", getattr(h, "buy_price", 0.0))
            avg_price_vnd = self._normalize_price_vnd(avg_price_raw) or 0.0
            quantity = int(getattr(h, "quantity", 0))
            cost_basis = float(quantity) * avg_price_vnd

            cur_price_raw = None
            has_error = True
            if self.price_source is not None and hasattr(self.price_source, "fetch_latest_close"):
                try:
                    quote = self.price_source.fetch_latest_close(h.symbol)
                    cur_price_raw = getattr(quote, "latest_close", getattr(quote, "close", None))
                    has_error = getattr(quote, "error", None) is not None or cur_price_raw is None
                except Exception:
                    has_error = True

            if has_error or cur_price_raw is None:
                cur_price_vnd = None
                market_val = cost_basis
                pnl = 0.0
                pnl_pct = 0.0
                price_err = True
            else:
                cur_price_vnd = self._normalize_price_vnd(cur_price_raw)
                market_val = float(quantity) * (cur_price_vnd or 0.0)
                pnl = market_val - cost_basis
                pnl_pct = ((pnl / cost_basis) * 100.0) if cost_basis > 0 else 0.0
                price_err = False

            total_cost += cost_basis
            total_market_value += market_val

            items.append(
                PortfolioItemSummary(
                    id=getattr(h, "id", ""),
                    user_id=getattr(h, "user_id", user_id),
                    symbol=getattr(h, "symbol", ""),
                    quantity=quantity,
                    avg_buy_price=avg_price_raw,
                    purchase_date=getattr(h, "purchase_date", getattr(h, "buy_date", None)),
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
        avg_buy_price: float | None = None,
        purchase_date: str | None = None,
        buy_date: str | None = None,
        notes: str | None = None,
        user_id: str = "default",
        buy_price: float | None = None,
        **kwargs: Any,
    ) -> Any:
        price = avg_buy_price if avg_buy_price is not None else (buy_price if buy_price is not None else 0.0)
        date = purchase_date or buy_date
        return self.holdings_repo.create(
            user_id=user_id,
            symbol=symbol.upper().strip(),
            quantity=quantity,
            avg_buy_price=price,
            purchase_date=date,
        )

    def delete_holding(self, holding_id: str | int, user_id: str = "default") -> bool:
        hid = str(holding_id)
        existing = self.holdings_repo.get(hid)
        if existing is None or str(getattr(existing, "user_id", "")) != user_id:
            return False
        return self.holdings_repo.delete(hid)

    def get_user_settings(self, user_id: str = "default") -> Any:
        return self.user_settings_repo.get(user_id)

    def update_user_settings(
        self,
        user_id: str = "default",
        alert_threshold_pct: float | None = None,
        risk_profile: str | None = None,
    ) -> Any:
        if alert_threshold_pct is not None:
            return self.user_settings_repo.set_threshold(user_id, alert_threshold_pct)
        return self.user_settings_repo.get(user_id)

    def update_alert_threshold(
        self, threshold_pct: float, user_id: str = "default"
    ) -> Any:
        return self.user_settings_repo.set_threshold(user_id, threshold_pct)
