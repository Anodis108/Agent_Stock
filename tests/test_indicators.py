"""Unit & Integration tests for TechnicalIndicatorService and technical indicator algorithms."""

from __future__ import annotations

import pytest
from backend.domain.indicators import (
    IndicatorSummary,
    analyze_technical_indicators,
    compute_rsi,
    compute_sma,
)
from backend.domain.ports import PriceBar, PriceSourcePort
from backend.services.technical_indicator_service import TechnicalIndicatorService


class DummyPriceSource(PriceSourcePort):
    def __init__(self, bars: list[PriceBar]) -> None:
        self.bars = bars

    def fetch_current_price(self, symbol: str) -> PriceBar:
        return self.bars[-1] if self.bars else PriceBar(date="2026-09-30", close=100.0)

    def fetch_history(self, symbol: str, lookback_days: int = 60) -> list[PriceBar]:
        return self.bars[-lookback_days:]


def test_compute_rsi_insufficient_data():
    """RSI cần ít nhất period + 1 phiên (15 phiên cho RSI 14)."""
    assert compute_rsi([], period=14) is None
    assert compute_rsi([100.0] * 14, period=14) is None
    # 15 phiên bằng nhau -> không đổi giá -> 50.0
    assert compute_rsi([100.0] * 15, period=14) == 50.0


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
    # Giá dao động quanh 50
    neutral_closes = [50.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(30)]
    rsi_neutral = compute_rsi(neutral_closes, period=14)
    assert rsi_neutral is not None
    assert 30.0 <= rsi_neutral <= 70.0


def test_compute_sma():
    """Kiểm tra SMA tính trung bình cộng chính xác cho chu kỳ chỉ định."""
    closes = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert compute_sma(closes, period=3) == 40.0  # (30+40+50)/3 = 40.0
    assert compute_sma(closes, period=5) == 30.0  # (10+20+30+40+50)/5 = 30.0
    assert compute_sma(closes, period=10) is None  # Không đủ dữ liệu


def test_crossover_golden_cross():
    """Kiểm tra phát hiện Golden Cross: SMA20 từ dưới cắt lên trên SMA50."""
    # 50 phiên giá bằng 50.0 (prev_sma_20 = 50.0, prev_sma_50 = 50.0)
    # Sau đó giá nhảy vọt lên 100.0 ở phiên thứ 51
    # prev: sma20 == sma50 (<=)
    # curr: sma20 = (19*50 + 100)/20 = 52.5, sma50 = (49*50 + 100)/50 = 51.0 -> sma20 > sma50!
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
    # 50 phiên giá bằng 100.0 (prev_sma_20 = 100.0, prev_sma_50 = 100.0)
    # Sau đó giá sụt giảm mạnh về 10.0 ở phiên thứ 51
    # prev: sma20 == sma50 (>=)
    # curr: sma20 = (19*100 + 10)/20 = 95.5, sma50 = (49*100 + 10)/50 = 98.2 -> sma20 < sma50!
    crossover_closes = [100.0] * 50 + [10.0]
    summary = analyze_technical_indicators(crossover_closes)
    assert summary.sma_20 is not None
    assert summary.sma_50 is not None
    assert summary.sma_20 < summary.sma_50
    assert summary.ma_cross == "death_cross"
    assert summary.trend == "bearish"
    assert "Death Cross" in summary.format_summary()


def test_technical_indicator_service_api():
    """Kiểm tra toàn bộ phương thức của TechnicalIndicatorService."""
    service = TechnicalIndicatorService()

    # calculate_rsi & calculate_sma
    series = [20.0 + i for i in range(25)]
    assert service.calculate_rsi(series, period=14) is not None
    assert service.calculate_sma(series, period=20) is not None

    # analyze
    summary = service.analyze(series)
    assert isinstance(summary, IndicatorSummary)
    assert summary.rsi is not None
    assert summary.rsi_status == "overbought"
    assert summary.sma_20 is not None

    # analyze_bars
    bars = [PriceBar(date=f"2026-09-{i:02d}", close=20.0 + i) for i in range(1, 26)]
    summary_bars = service.analyze_bars(bars)
    assert summary_bars.rsi == summary.rsi

    # analyze_symbol with price source
    mock_source = DummyPriceSource(bars=bars)
    service_with_source = TechnicalIndicatorService(price_source=mock_source)
    summary_symbol = service_with_source.analyze_symbol("HPG", lookback_days=30)
    assert summary_symbol.rsi is not None
    assert summary_symbol.rsi == summary.rsi

    # Empty source fallback
    empty_service = TechnicalIndicatorService(price_source=None)
    summary_empty = empty_service.analyze_symbol("HPG")
    assert summary_empty.rsi is None
