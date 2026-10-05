"""I/O price_agent — không LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PriceAgentResult:
    symbol: str
    latest_close: float | None
    prev_close: float | None
    change_pct: float | None
    error: str | None = None

    @property
    def reference_price(self) -> float | None:
        """Giá tham chiếu (phiên đóng cửa liền trước)."""
        return self.prev_close

    @property
    def ceiling_price(self) -> float | None:
        """Giá trần theo biên độ sàn HOSE (+7%)."""
        if self.prev_close is None or self.prev_close <= 0:
            return None
        return round(self.prev_close * 1.07, 2)

    @property
    def floor_price(self) -> float | None:
        """Giá sàn theo biên độ sàn HOSE (-7%)."""
        if self.prev_close is None or self.prev_close <= 0:
            return None
        return round(self.prev_close * 0.93, 2)

