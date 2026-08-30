"""Live supervisor: 1 mã → giá + tin + eval.

    python -m pytest tests/test_supervisor_agent.py -s -q
"""

from __future__ import annotations

import sys

import pytest

from app.agent_pr.supervisor_agent import Agent_Input, run_supervisor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@pytest.mark.asyncio
async def test_hpg_online():
    out = await run_supervisor(Agent_Input(symbol="HPG"))
    print()
    print("answer:", out.answer)
    for step in out.trace:
        print("trace :", step)
    print("pct   :", out.price.pct_change, "| tin:", len(out.news.articles))

    assert out.symbol == "HPG"
    assert out.price.last > 0
    assert out.news.articles
    assert out.eval.has_enough_evidence
    assert "HPG" in out.answer
    assert "giảm" in out.answer or "tăng" in out.answer


@pytest.mark.asyncio
async def test_ma_sai():
    with pytest.raises(ValueError):
        await run_supervisor(Agent_Input(symbol="ABC"))
