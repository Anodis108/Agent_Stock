"""Unit tests for technical indicator algorithms in common domain."""

from __future__ import annotations

import pytest
from common.domain.indicators import (
    IndicatorSummary,
    analyze_technical_indicators,
    calculate_rsi,
    calculate_sma,
    compute_rsi,
    compute_sma,
)
from common.domain.ports import PriceBar, PriceSourcePort


class DummyPriceSource(PriceSourcePort):
    def __init__(self, bars: list[PriceBar]) -> None:
        self.bars = bars

    def fetch_latest_close(self, symbol: str):
        from common.domain.ports import PriceQuote
        return PriceQuote(symbol=symbol, latest_close=self.bars[-1].close if self.bars else 100.0)

    def fetch_history(self, symbol: str, lookback_days: int = 60) -> list[PriceBar]:
        return self.bars[-lookback_days:]


def test_compute_rsi_insufficient_data():
    """RSI cần ít nhất period + 1 phiên (15 phiên cho RSI 14)."""
    assert compute_rsi([], period=14) is None
    assert compute_rsi([100.0] * 14, period=14) is None
    # 15 phiên bằng nhau -> không đổi giá -> 50.0
    assert compute_rsi([100.0] * 15, period=14) == 50.0
    assert calculate_rsi([100.0] * 15, period=14) == 50.0


def test_compute_rsi_overbought_and_oversold():
    """Kiểm tra RSI nhận diện quá mua (>70) và quá bán (<30)."""
    # Chuỗi tăng liên tục 25 phiên -> Quá mua (> 70)
    uptrend = [10.0 + i * 2.0 for i in range(25)]
    rsi_up = compute_rsi(uptrend, period=14)
    assert rsi_up is not None
    assert rsi_up > 70.0
    assert rsi_up <= 100.0

    # Chuỗi giảm liên tục 25 phiên -> Quá bán (< 30)
    downtrend = [100.0 - i * 2.0 for i in range(25)]
    rsi_down = compute_rsi(downtrend, period=14)
    assert rsi_down is not None
    assert 0.0 <= rsi_down < 30.0

    # Chuỗi dao động vừa phải (trung tính 30-70)
    neutral_closes = [50.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(30)]
    rsi_neutral = compute_rsi(neutral_closes, period=14)
    assert rsi_neutral is not None
    assert 30.0 <= rsi_neutral <= 70.0


def test_compute_sma():
    """Kiểm tra SMA tính trung bình cộng chính xác cho chu kỳ chỉ định."""
    closes = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert compute_sma(closes, period=3) == 40.0  # (30+40+50)/3 = 40.0
    assert calculate_sma(closes, period=3) == 40.0
    assert compute_sma(closes, period=5) == 30.0  # (10+20+30+40+50)/5 = 30.0
    assert compute_sma(closes, period=10) is None  # Không đủ dữ liệu


def test_crossover_golden_cross():
    """Kiểm tra phát hiện Golden Cross: SMA20 từ dưới cắt lên trên SMA50."""
    crossover_closes = [50.0] * 50 + [100.0]
    summary = analyze_technical_indicators(crossover_closes)
    assert summary.sma_20 is not None
    assert summary.sma_50 is not None
    assert summary.sma_20 > summary.sma_50
    assert summary.ma_cross == "golden_cross"
    assert summary.trend == "bullish"
    assert "Golden Cross" in summary.format_summary()


def test_crossover_death_cross():
    """Kiểm tra phát hiện Death Cross: SMA20 từ trên cắt xuống dưới SMA50."""
    crossover_closes = [100.0] * 50 + [10.0]
    summary = analyze_technical_indicators(crossover_closes)
    assert summary.sma_20 is not None
    assert summary.sma_50 is not None
    assert summary.sma_20 < summary.sma_50
    assert summary.ma_cross == "death_cross"
    assert summary.trend == "bearish"
    assert "Death Cross" in summary.format_summary()
