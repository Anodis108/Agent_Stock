"""Pure financial domain calculations for portfolio and risk management in Web Backend."""

from __future__ import annotations

from typing import Any

from common.base.base_model import CustomBaseModel


class HoldingCalculationResult(CustomBaseModel):
    """Kết quả tính toán chi tiết P&L của một mã cổ phiếu."""

    id: str | int = ""
    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: float | None = None
    cost_basis: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_pct: float = 0.0
    weight_pct: float = 0.0
    price_error: bool = False
    purchase_date: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_buy_price": self.avg_buy_price,
            "current_price": self.current_price,
            "cost_basis": round(self.cost_basis, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "weight_pct": round(self.weight_pct, 2),
            "price_error": self.price_error,
            "purchase_date": self.purchase_date,
        }


class PortfolioCalculationResult(CustomBaseModel):
    """Tổng quan danh mục đầu tư và phân bổ tỷ trọng."""

    user_id: str = "default"
    total_nav: float = 0.0
    total_cost: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    holdings_count: int = 0
    items: list[HoldingCalculationResult] = []
    concentration_warning: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_nav": round(self.total_nav, 2),
            "total_cost": round(self.total_cost, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "count": self.holdings_count,
            "items": [it.as_dict() for it in self.items],
            "concentration_warning": self.concentration_warning,
        }


class PortfolioAlert(CustomBaseModel):
    """Cảnh báo rủi ro (Cắt lỗ / Chốt lời) theo ngưỡng thiết lập."""

    symbol: str
    pnl_pct: float
    alert_type: str  # "STOP_LOSS" | "TAKE_PROFIT"
    threshold_pct: float
    message: str


class PortfolioCalculator:
    """Các công thức tài chính chuyên biệt cho danh mục đầu tư (Pure Domain Logic)."""

    @staticmethod
    def normalize_price_vnd(price: float | None) -> float | None:
        """Chuẩn hóa giá về đơn vị VND đầy đủ.
        
        Thị trường chứng khoán Việt Nam thường niêm yết giá theo nghìn đồng (ví dụ: 52.5 hoặc 52500).
        Nếu giá <= 1000.0, nhân 1000.0 để đưa về VND chuẩn.
        """
        if price is None:
            return None
        return float(price * 1000.0 if price <= 1000.0 else price)

    @classmethod
    def calculate_item_pnl(
        cls,
        quantity: int,
        avg_buy_price: float,
        current_price: float | None,
        symbol: str = "",
        item_id: str | int = "",
        purchase_date: str | None = None,
    ) -> HoldingCalculationResult:
        """Tính toán giá vốn, thị giá, Unrealized P&L và tỷ suất sinh lời của một vị thế."""
        norm_buy_price = cls.normalize_price_vnd(avg_buy_price) or 0.0
        cost_basis = float(quantity) * norm_buy_price

        if current_price is None or current_price <= 0:
            # Khi nguồn dữ liệu không có giá hoặc bị lỗi, fallback thị giá bằng giá vốn
            return HoldingCalculationResult(
                id=item_id,
                symbol=symbol,
                quantity=quantity,
                avg_buy_price=avg_buy_price,
                current_price=None,
                cost_basis=cost_basis,
                market_value=cost_basis,
                unrealized_pnl=0.0,
                pnl_pct=0.0,
                weight_pct=0.0,
                price_error=True,
                purchase_date=purchase_date,
            )

        norm_cur_price = cls.normalize_price_vnd(current_price) or 0.0
        market_val = float(quantity) * norm_cur_price
        pnl = market_val - cost_basis
        pnl_pct = ((pnl / cost_basis) * 100.0) if cost_basis > 0 else 0.0

        return HoldingCalculationResult(
            id=item_id,
            symbol=symbol,
            quantity=quantity,
            avg_buy_price=avg_buy_price,
            current_price=current_price,
            cost_basis=cost_basis,
            market_value=market_val,
            unrealized_pnl=pnl,
            pnl_pct=pnl_pct,
            weight_pct=0.0,
            price_error=False,
            purchase_date=purchase_date,
        )

    @classmethod
    def calculate_portfolio_summary(
        cls,
        holdings_data: list[Any],
        user_id: str = "default",
    ) -> PortfolioCalculationResult:
        """Tổng hợp toàn bộ danh mục, tính toán tổng NAV, P&L và tỷ trọng danh mục."""
        items: list[HoldingCalculationResult] = []
        total_cost = 0.0
        total_nav = 0.0

        for h in holdings_data:
            if isinstance(h, HoldingCalculationResult):
                calc_item = h
            elif isinstance(h, dict):
                calc_item = cls.calculate_item_pnl(
                    quantity=int(h.get("quantity", 0)),
                    avg_buy_price=float(h.get("avg_buy_price", h.get("buy_price", 0.0))),
                    current_price=h.get("current_price"),
                    symbol=str(h.get("symbol", "")),
                    item_id=h.get("id", ""),
                    purchase_date=h.get("purchase_date"),
                )
            else:
                qty = int(getattr(h, "quantity", 0))
                buy_p = float(getattr(h, "avg_buy_price", getattr(h, "buy_price", 0.0)))
                cur_p = getattr(h, "current_price", None)
                sym = str(getattr(h, "symbol", ""))
                hid = getattr(h, "id", "")
                p_date = getattr(h, "purchase_date", getattr(h, "buy_date", None))
                calc_item = cls.calculate_item_pnl(
                    quantity=qty,
                    avg_buy_price=buy_p,
                    current_price=cur_p,
                    symbol=sym,
                    item_id=hid,
                    purchase_date=p_date,
                )

            items.append(calc_item)
            total_cost += calc_item.cost_basis
            total_nav += calc_item.market_value

        # Tính tỷ trọng weight_pct cho từng mã
        concentration_warning = None
        for it in items:
            if total_nav > 0:
                it.weight_pct = (it.market_value / total_nav) * 100.0
            else:
                it.weight_pct = 0.0

            # Cảnh báo rủi ro tập trung nếu 1 mã chiếm >= 40% NAV (khi danh mục có từ 2 mã trở lên)
            if len(items) >= 2 and it.weight_pct >= 40.0:
                concentration_warning = (
                    f"Cảnh báo rủi ro tập trung: Mã {it.symbol} chiếm {round(it.weight_pct, 1)}% tổng NAV."
                )

        total_pnl = total_nav - total_cost
        total_pnl_pct = ((total_pnl / total_cost) * 100.0) if total_cost > 0 else 0.0

        return PortfolioCalculationResult(
            user_id=user_id,
            total_nav=total_nav,
            total_cost=total_cost,
            total_unrealized_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            holdings_count=len(items),
            items=items,
            concentration_warning=concentration_warning,
        )

    @classmethod
    def check_alert_triggers(
        cls,
        items: list[HoldingCalculationResult],
        threshold_pct: float,
    ) -> list[PortfolioAlert]:
        """Kiểm tra xem vị thế nào chạm ngưỡng cảnh báo cắt lỗ hoặc chốt lời."""
        if threshold_pct <= 0:
            return []

        alerts: list[PortfolioAlert] = []
        limit = abs(threshold_pct)

        for it in items:
            if it.price_error:
                continue

            if it.pnl_pct <= -limit:
                alerts.append(
                    PortfolioAlert(
                        symbol=it.symbol,
                        pnl_pct=round(it.pnl_pct, 2),
                        alert_type="STOP_LOSS",
                        threshold_pct=limit,
                        message=f"Mã {it.symbol} giảm {round(it.pnl_pct, 2)}%, chạm ngưỡng cắt lỗ (-{limit}%).",
                    )
                )
            elif it.pnl_pct >= limit:
                alerts.append(
                    PortfolioAlert(
                        symbol=it.symbol,
                        pnl_pct=round(it.pnl_pct, 2),
                        alert_type="TAKE_PROFIT",
                        threshold_pct=limit,
                        message=f"Mã {it.symbol} tăng +{round(it.pnl_pct, 2)}%, chạm ngưỡng chốt lời (+{limit}%).",
                    )
                )

        return alerts
