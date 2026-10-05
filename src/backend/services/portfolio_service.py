"""Portfolio Service — Quản lý danh mục đầu tư và tính toán lãi/lỗ (P&L Engine).

Cung cấp dịch vụ quản lý vị thế cổ phiếu và tính toán P&L theo chuẩn nghiệp vụ:
- Unrealized P&L = (current_price - avg_buy_price) * quantity
- Total NAV = sum(current_price * quantity)
- Cô lập dữ liệu tuyệt đối theo user_id
- Fallback an toàn khi lỗi giá thị trường
"""

from __future__ import annotations

from backend.application.portfolio_service import (
    PortfolioItemSummary,
    PortfolioService,
    PortfolioSummary,
)

__all__ = [
    "PortfolioItemSummary",
    "PortfolioService",
    "PortfolioSummary",
]
