"""PriceQuote — hợp đồng ra ngoài graph (HTTP / test / agent sau này).

`last` là VND. vnstock Quote.history (KBS) trả `close` theo nghìn đồng
(22.1 = 22.100 VND) — node `parse` nhân 1000 trước khi ghi vào đây.

Không nhét DataFrame vnstock vào schema: graph chỉ đi dict/model, test không
cần import pandas. PriceAgent / Coordinator (slice sau) đọc đúng type này,
không gọi vnstock trực tiếp.
"""

from __future__ import annotations

from pydantic import BaseModel


class PriceQuote(BaseModel):
    """Một snapshot giá đóng cửa (2 phiên) sau khi parse rows."""

    symbol: str                           # mã đã chuẩn hoá, vd. HPG
    last: float                           # đóng cửa phiên mới nhất — VND
    prev_close: float | None = None       # đóng cửa phiên trước — VND; None nếu chỉ 1 dòng
    pct_change: float | None = None       # (last - prev) / prev * 100; None nếu thiếu prev
    trading_date: str = ""                # YYYYMMDD rút từ time của dòng cuối
    source: str = "vnstock"               # cố định slice 1; không phải URL SSI/TCBS
