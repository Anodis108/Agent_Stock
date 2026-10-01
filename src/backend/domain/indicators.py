"""Technical Indicators Calculation — RSI, SMA & Crossovers (MVP 2.0).

Cung cấp các hàm thuần túy (pure functions) tính toán chỉ báo kỹ thuật định lượng:
- compute_rsi: Tính Relative Strength Index theo phương pháp Wilder (chu kỳ 14 phiên mặc định).
- compute_sma: Tính Simple Moving Average (SMA 20, SMA 50).
- analyze_technical_indicators: Phân tích tổng thể trạng thái Quá mua (RSI > 70), Quá bán (RSI < 30),
  và phát hiện tín hiệu giao cắt Golden Cross (SMA20 cắt lên SMA50) / Death Cross (SMA20 cắt xuống SMA50).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class IndicatorSummary:
    """Tóm tắt các chỉ báo kỹ thuật của cổ phiếu."""

    rsi: float | None = None
    rsi_status: str = "neutral"  # "overbought" | "oversold" | "neutral" | "unknown"
    sma_20: float | None = None
    sma_50: float | None = None
    ma_cross: str = "none"  # "golden_cross" | "death_cross" | "none"
    trend: str = "neutral"  # "bullish" | "bearish" | "neutral"

    def as_dict(self) -> dict[str, Any]:
        return {
            "rsi": self.rsi,
            "rsi_status": self.rsi_status,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "ma_cross": self.ma_cross,
            "trend": self.trend,
        }

    def format_summary(self) -> str:
        """Định dạng chuỗi tóm tắt ngắn gọn đưa vào Context của EvalAgent."""
        parts: list[str] = []
        if self.rsi is not None:
            status_desc = {
                "overbought": "Quá mua (Rủi ro điều chỉnh)",
                "oversold": "Quá bán (Khả năng hồi phục kỹ thuật)",
                "neutral": "Trung tính",
            }.get(self.rsi_status, self.rsi_status)
            parts.append(f"RSI(14): {self.rsi:.1f} ({status_desc})")
        else:
            parts.append("RSI(14): N/A (chưa đủ dữ liệu)")

        sma_parts: list[str] = []
        if self.sma_20 is not None:
            sma_parts.append(f"SMA20: {self.sma_20:.1f}")
        if self.sma_50 is not None:
            sma_parts.append(f"SMA50: {self.sma_50:.1f}")

        if sma_parts:
            parts.append(", ".join(sma_parts))

        if self.ma_cross == "golden_cross":
            parts.append("Tín hiệu: Golden Cross (SMA20 cắt lên SMA50 - Xu hướng tăng mạnh)")
        elif self.ma_cross == "death_cross":
            parts.append("Tín hiệu: Death Cross (SMA20 cắt xuống SMA50 - Xu hướng giảm mạnh)")
        elif self.trend != "neutral":
            trend_desc = "Xu hướng ngắn/trung hạn tăng" if self.trend == "bullish" else "Xu hướng ngắn/trung hạn giảm"
            parts.append(f"Xu hướng: {trend_desc}")

        return " | ".join(parts) if parts else "(chưa đủ dữ liệu chỉ báo kỹ thuật)"


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Tính Relative Strength Index (RSI) theo công thức Wilder smoothing.
    
    Yêu cầu tối thiểu `period + 1` điểm giá đóng cửa.
    Kết quả nằm trong khoảng [0.0, 100.0], làm tròn 2 chữ số thập phân.
    """
    if len(closes) <= period or period <= 0:
        return None

    # Tính biến động giữa các phiên
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)

    if len(gains) < period:
        return None

    # Khởi tạo trung bình tăng/giảm cho kỳ đầu tiên
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder's Smoothing cho các kỳ tiếp theo
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi), 2)


def compute_sma(closes: list[float], period: int) -> float | None:
    """Tính Simple Moving Average (SMA) của `period` phiên gần nhất."""
    if len(closes) < period or period <= 0:
        return None
    return round(float(sum(closes[-period:]) / period), 2)


def analyze_technical_indicators(closes: list[float]) -> IndicatorSummary:
    """Phân tích toàn diện chỉ báo kỹ thuật từ chuỗi giá đóng cửa (thứ tự tăng dần theo thời gian)."""
    if not closes:
        return IndicatorSummary()

    rsi = compute_rsi(closes, period=14)
    if rsi is not None:
        if rsi >= 70.0:
            rsi_status = "overbought"
        elif rsi <= 30.0:
            rsi_status = "oversold"
        else:
            rsi_status = "neutral"
    else:
        rsi_status = "unknown"

    sma_20 = compute_sma(closes, period=20)
    sma_50 = compute_sma(closes, period=50)

    ma_cross = "none"
    trend = "neutral"

    # Kiểm tra tín hiệu giao cắt nếu có đủ ít nhất 51 phiên (để tính SMA20 và SMA50 cho 2 phiên gần nhất)
    if len(closes) >= 51 and sma_20 is not None and sma_50 is not None:
        prev_closes = closes[:-1]
        prev_sma_20 = compute_sma(prev_closes, period=20)
        prev_sma_50 = compute_sma(prev_closes, period=50)

        if prev_sma_20 is not None and prev_sma_50 is not None:
            if prev_sma_20 <= prev_sma_50 and sma_20 > sma_50:
                ma_cross = "golden_cross"
                trend = "bullish"
            elif prev_sma_20 >= prev_sma_50 and sma_20 < sma_50:
                ma_cross = "death_cross"
                trend = "bearish"
            elif sma_20 > sma_50:
                trend = "bullish"
            elif sma_20 < sma_50:
                trend = "bearish"
    elif sma_20 is not None and sma_50 is not None:
        if sma_20 > sma_50:
            trend = "bullish"
        elif sma_20 < sma_50:
            trend = "bearish"

    return IndicatorSummary(
        rsi=rsi,
        rsi_status=rsi_status,
        sma_20=sma_20,
        sma_50=sma_50,
        ma_cross=ma_cross,
        trend=trend,
    )
