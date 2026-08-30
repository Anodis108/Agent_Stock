"""Test live craw_agent — gọi vnstock thật, in quote để đối chiếu CafeF/Simplize.

Chạy từ llm-engineer-demo (để import `app`):
    python -m pytest tests/test_craw_agent.py -s -q

`-s` bắt buộc: không thì pytest nuốt print. Banner VNSTOCK INSIDERS là ads
của vnai, không phải fail.

Không hardcode last=22100: giá đổi theo phiên. Assert chỉ sanity (mã, last>0).
Đúng/sai số: so với https://simplize.vn/co-phieu/HPG (đóng cửa / % / ngày).
"""

from __future__ import annotations

import pytest

from app.agent_pr.craw_agent import run_crawl


@pytest.mark.asyncio
async def test_hpg_online():
    """HPG nằm ALLOWED — graph chạy hết, in 6 field PriceQuote."""
    q = await run_crawl("HPG")
    print()
    print("symbol      :", q.symbol)
    print("last (VND)  :", q.last)
    print("prev_close  :", q.prev_close)
    print("pct_change  :", q.pct_change)
    print("trading_date:", q.trading_date)
    print("source      :", q.source)

    assert q.symbol == "HPG"
    assert q.last > 0
    assert q.prev_close and q.prev_close > 0
    assert q.trading_date
    assert q.source == "vnstock"


@pytest.mark.asyncio
async def test_ma_sai():
    """ABC không whitelist — normalize raise trước khi gọi vnstock."""
    with pytest.raises(ValueError):
        await run_crawl("ABC")
