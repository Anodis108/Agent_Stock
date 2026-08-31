"""Live supervisor: LLM chọn worker.

    python -m pytest tests/test_supervisor_agent.py -s -q
"""

from __future__ import annotations

import sys

import pytest

from app.agent_pr.supervisor_agent import Agent_Input, AgentPlan, run_supervisor
from app.agent_pr.supervisor_agent.nodes import _sanitize_plan

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_sanitize_eval_can_gia_va_tin():
    raw = AgentPlan(
        symbol="hpg",
        use_price=False,
        use_news=True,
        use_db=False,
        use_eval=True,
        use_synth=True,
        reasoning="muốn eval nhưng quên giá",
    )
    plan = _sanitize_plan(raw, "HPG")
    assert plan.symbol == "HPG"
    assert plan.use_eval is False
    assert plan.use_news is True


def test_sanitize_giu_ma_user_gui():
    raw = AgentPlan(
        symbol="FPT",
        use_price=True,
        use_news=False,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="nhầm ticker",
    )
    plan = _sanitize_plan(raw, "HPG")
    assert plan.symbol == "HPG"


@pytest.mark.asyncio
async def test_hpg_online():
    out = await run_supervisor(Agent_Input(symbol="HPG"))
    print()
    print("answer:", out.answer)
    print("plan  :", out.plan.model_dump() if out.plan else None)
    for step in out.trace:
        print("trace :", step)
    if out.price:
        print("pct   :", out.price.pct_change, "| tin:", len(out.news.articles) if out.news else 0)

    assert out.symbol == "HPG"
    assert out.plan is not None
    assert "HPG" in out.answer
    assert out.price is not None and out.price.last > 0
    assert out.news is not None and out.news.articles
    assert out.eval is not None
    assert "giảm" in out.answer or "tăng" in out.answer


@pytest.mark.asyncio
async def test_chi_gia_khong_goi_news(monkeypatch):
    """Plan tắt news/eval/db → graph không chạy các worker đó."""

    def fake_plan(question: str, hint: str, **_kwargs) -> AgentPlan:
        return AgentPlan(
            symbol="HPG",
            use_price=True,
            use_news=False,
            use_db=False,
            use_eval=False,
            use_synth=True,
            reasoning="chỉ hỏi giá",
        )

    monkeypatch.setattr(
        "app.agent_pr.supervisor_agent.nodes._make_plan", fake_plan
    )
    out = await run_supervisor(
        Agent_Input(symbol="HPG", question="giá HPG hôm nay bao nhiêu")
    )
    print()
    print("answer:", out.answer)
    for step in out.trace:
        print("trace :", step)

    assert out.price is not None and out.price.last > 0
    assert out.news is None
    assert out.eval is None
    assert out.db is None
    assert "HPG" in out.answer


@pytest.mark.asyncio
async def test_ma_sai():
    with pytest.raises(ValueError):
        await run_supervisor(Agent_Input(symbol="HP"))
