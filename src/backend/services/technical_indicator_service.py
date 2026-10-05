"""Technical Indicator Service — Calculation engine for RSI, SMA, and Crossover signals.

Cung cấp dịch vụ tính toán và phân tích các chỉ báo kỹ thuật:
- RSI (chu kỳ 14 mặc định theo thuật toán Wilder's smoothing)
- SMA (chu kỳ 20, 50 phiên)
- Tín hiệu giao cắt: Golden Cross (SMA20 cắt lên SMA50), Death Cross (SMA20 cắt xuống SMA50)
- Phân tích trạng thái thị trường: Quá mua (>70), Quá bán (<30), Bullish/Bearish
"""

from __future__ import annotations

from typing import Sequence

from backend.domain.indicators import (
    IndicatorSummary,
    analyze_technical_indicators,
    compute_rsi,
    compute_sma,
)
from backend.domain.ports import PriceBar, PriceSourcePort


class TechnicalIndicatorService:
    """Dịch vụ động cơ chỉ báo kỹ thuật cho Portfolio Watch Swarm."""

    def __init__(self, price_source: PriceSourcePort | None = None) -> None:
        self.price_source = price_source

    def calculate_rsi(
        self,
        closes: Sequence[float],
        period: int = 14,
    ) -> float | None:
        """Tính chỉ báo Relative Strength Index (RSI) theo chu kỳ.
        
        Trả về None nếu không đủ dữ liệu (yêu cầu ít nhất period + 1 phiên).
        """
        return compute_rsi(list(closes), period=period)

    def calculate_sma(
        self,
        closes: Sequence[float],
        period: int,
    ) -> float | None:
        """Tính đường trung bình động giản đơn SMA theo chu kỳ."""
        return compute_sma(list(closes), period=period)

    def analyze(self, closes: Sequence[float]) -> IndicatorSummary:
        """Phân tích toàn diện chỉ báo từ mảng giá đóng cửa."""
        return analyze_technical_indicators(list(closes))

    def analyze_bars(self, bars: Sequence[PriceBar]) -> IndicatorSummary:
        """Trích xuất giá đóng cửa từ danh sách PriceBar và phân tích chỉ báo."""
        closes = [b.close for b in bars if getattr(b, "close", None) is not None]
        return self.analyze(closes)

    def analyze_symbol(
        self,
        symbol: str,
        lookback_days: int = 60,
    ) -> IndicatorSummary:
        """Nạp dữ liệu lịch sử từ price_source và thực hiện phân tích chỉ báo kỹ thuật."""
        if not self.price_source:
            return IndicatorSummary()
        try:
            bars = self.price_source.fetch_history(symbol, lookback_days=lookback_days)
            return self.analyze_bars(bars)
        except Exception:
            return IndicatorSummary()
