"""Phase 1 — chat steps[] contract."""

from __future__ import annotations

from src.portfolio_watch.application.answer_question import build_chat_steps
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.agents.supervisor import RewrittenQuestion
from src.portfolio_watch.domain.entities import RoutingDecision


def test_build_chat_steps_shape_and_order():
    steps = build_chat_steps(
        rewritten=RewrittenQuestion(
            original="Giá FPT?", rewritten="Giá FPT hiện tại", symbol="FPT", intent="price_lookup"
        ),
        routing=RoutingDecision(
            route="price_lookup", reason="chỉ giá", agents_to_call=["price"]
        ),
        price=PriceAgentResult(
            symbol="FPT",
            latest_close=100.0,
            prev_close=99.0,
            change_pct=1.01,
            error=None,
        ),
        answer="FPT giá 100",
    )
    assert [s["id"] for s in steps] == [str(i) for i in range(1, len(steps) + 1)]
    assert steps[0]["name"] == "rewrite_question"
    assert steps[1]["name"] == "supervisor"
    assert steps[2]["name"] == "price_agent"
    assert steps[-1]["name"] == "answer_composer"
    for s in steps:
        assert s["status"] == "done"
        assert "detail" in s
