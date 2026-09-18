"""Guardrail rewrite phải giữ grounding (số liệu evidence) — Phase 3c."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.answer_composer import run_answer_composer
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.agents.synthesis_agent import run_synthesis_agent
from src.portfolio_watch.domain.entities import Severity, SeverityLevel
from src.portfolio_watch.domain.guardrails.output_checks import (
    check_output,
    check_rewrite_grounding,
    has_evidence_grounding,
    rewrite_keep_grounding,
)
from tests.fakes import FakeMemoryStore


def test_rewrite_keep_grounding_strips_buy_keeps_numbers():
    prev = "FPT change_pct=-4.00%. Nhà đầu tư nên bán ngay."
    evid = ["change_pct=-4.00%", "FPT.latest_close=96.0"]
    out = rewrite_keep_grounding(prev, evid)
    assert "nên bán" not in out.lower()
    assert has_evidence_grounding(out, evid)
    assert check_output("", out, evid).ok


def test_check_rewrite_grounding_rejects_disclaimer_only():
    evid = ["change_pct=-4.00%"]
    bad = check_rewrite_grounding(
        "Thông tin tham khảo, không phải lời khuyên đầu tư.",
        evid,
        require=True,
    )
    assert bad.ok is False
    good = check_rewrite_grounding(
        "FPT change_pct=-4.00%. Thông tin tham khảo.",
        evid,
        require=True,
    )
    assert good.ok is True


def test_answer_composer_rewrite_must_keep_price_numbers():
    """LLM rewrite chỉ disclaimer → hệ thống không chấp nhận; giữ số liệu."""
    price = PriceAgentResult("FPT", 96.0, 100.0, -4.0)

    class BuyThenDisclaimer:
        def compose(self, **kwargs):
            if kwargs.get("attempt", 0) == 0:
                return "FPT change_pct=-4.00%. Nên mua bắt đáy."
            # Rewrite mất grounding — chỉ disclaimer
            return "Thông tin tham khảo, không phải lời khuyên đầu tư."

    result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=BuyThenDisclaimer(),
        max_attempts=2,
    )
    assert "nên mua" not in result.answer.lower()
    assert has_evidence_grounding(result.answer, result.evidence)
    assert check_output("", result.answer, result.evidence).ok
    assert "-4" in result.answer or "96" in result.answer


def test_synthesis_rewrite_keeps_evidence_numbers():
    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="biến động",
        evidence=["change_pct=-4.00%"],
    )

    class BuyThenEmpty:
        def compose(
            self, symbol, severity, preferences, *, model, attempt, previous_violations
        ):
            if attempt == 0:
                return "Cảnh báo", "FPT change_pct=-4.00%. Nên bán ngay."
            return "Cảnh báo", "Không có khuyến nghị."

    result = run_synthesis_agent(
        "FPT", sev, FakeMemoryStore(), composer=BuyThenEmpty(), max_attempts=2
    )
    assert "nên bán" not in result.alert.body.lower()
    assert has_evidence_grounding(result.alert.body, sev.evidence)
    assert check_output(result.alert.title, result.alert.body, sev.evidence).ok
