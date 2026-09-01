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

from app.agent_pr.craw_agent import Agent_Input, run_crawl


def test_hpg_online():
    """HPG — graph chạy hết, in 6 field Agent_Output."""
    q = run_crawl(Agent_Input(symbol="HPG"))
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


def test_ma_sai():
    """Không chặn regex — chỉ upper/strip."""
    from app.agent_pr.craw_agent.nodes import normalize

    assert normalize({"symbol": "hp"})["symbol"] == "HP"
