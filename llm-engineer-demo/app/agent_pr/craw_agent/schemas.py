"""Hợp đồng vào/ra craw_agent — HTTP / test / agent sau này đọc đúng type này.

Agent_Input: caller đưa vào graph (hiện chỉ mã CP). Thêm field ở đây khi
PriceAgent/Coordinator cần (câu hỏi, khoảng ngày) — đừng nhét vào CrawlState
trước.

Agent_Output: snapshot 2 phiên sau parse. `last` là VND. vnstock VCI trả
`close` nghìn đồng (22.1 = 22.100 VND) — node `parse` nhân 1000.

Không nhét DataFrame vnstock vào schema: graph chỉ đi dict/model.
"""

from __future__ import annotations

from pydantic import BaseModel


class Agent_Input(BaseModel):
    """Đầu vào graph. Slice 1 chỉ cần symbol; field khác thêm khi agent sau cần."""

    symbol: str                           # mã CP thô, vd. "hpg" — normalize sẽ upper


class Agent_Output(BaseModel):
    """Đầu ra graph — giá đóng cửa 2 phiên (sau khi parse rows)."""

    symbol: str                           # mã đã chuẩn hoá, vd. HPG
    last: float                           # đóng cửa phiên mới nhất — VND
    prev_close: float | None = None       # đóng cửa phiên trước — VND; None nếu chỉ 1 dòng
    pct_change: float | None = None       # (last - prev) / prev * 100; None nếu thiếu prev
    trading_date: str = ""                # YYYYMMDD rút từ time của dòng cuối
    source: str = "vnstock"               # cố định slice 1; không phải URL SSI/TCBS
