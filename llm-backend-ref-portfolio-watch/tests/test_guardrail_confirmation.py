"""Phase 5 — xác nhận Guardrail vs test-plan (mua/bán chắc chắn + số liệu lệch evidence).

test-plan: SynthesisAgent + Guardrail; AnswerComposer dùng chung module.
product-spec AC: chặn lời khuyên mua/bán chắc chắn.
"""

from __future__ import annotations

from src.portfolio_watch.domain.agents.answer_composer import run_answer_composer
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.agents.synthesis_agent import run_synthesis_agent
from src.portfolio_watch.domain.entities import Severity, SeverityLevel
from src.portfolio_watch.domain.guardrails import output_checks
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from tests.fakes import FakeMemoryStore


def test_check_output_blocks_nen_mua_and_nen_ban():
    """test-plan: câu cố định chứa 'nên mua'/'nên bán' → Guardrail chặn."""
    buy = check_output("Alert", "Nhà đầu tư nên mua FPT.", evidence=["change_pct=-4.00%"])
    sell = check_output("Alert", "Nhà đầu tư nên bán FPT.", evidence=["change_pct=-4.00%"])
    assert buy.ok is False
    assert sell.ok is False
    assert any("nên mua" in v for v in buy.violations)
    assert any("nên bán" in v for v in sell.violations)


def test_check_output_blocks_number_not_in_evidence():
    """test-plan: số liệu không khớp evidence → Guardrail chặn."""
    bad = check_output(
        "Cảnh báo",
        "Giá giảm 12.5% trong phiên.",
        evidence=["change_pct=-4.00%"],
    )
    assert bad.ok is False
    assert any("không khớp evidence" in v for v in bad.violations)

    good = check_output(
        "Cảnh báo",
        "Giá change_pct=-4.00% trong phiên.",
        evidence=["change_pct=-4.00%"],
    )
    assert good.ok is True


def test_synthesis_rewrite_when_buy_or_sell_advice():
    """test-plan: câu cố định 'nên mua'/'nên bán' → chặn + soạn lại (>1 lần)."""
    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="biến động",
        evidence=["change_pct=-4.00%"],
    )

    for bad_phrase, clean_ok in (
        ("Nhà đầu tư nên mua bắt đáy.", "nên mua"),
        ("Nhà đầu tư nên bán ngay.", "nên bán"),
    ):

        class BadThenGood:
            def __init__(self):
                self.calls = 0

            def compose(
                self, symbol, severity, preferences, *, model, attempt, previous_violations
            ):
                self.calls += 1
                if attempt == 0:
                    return "Cảnh báo", f"FPT change_pct=-4.00%. {bad_phrase}"
                return (
                    "Cảnh báo FPT",
                    "FPT change_pct=-4.00%. Thông tin tham khảo, không phải lời khuyên đầu tư.",
                )

        composer = BadThenGood()
        result = run_synthesis_agent("FPT", sev, FakeMemoryStore(), composer=composer)
        assert result.draft_attempts > 1
        assert composer.calls > 1
        assert clean_ok not in result.alert.body.lower()
        assert check_output(result.alert.title, result.alert.body, sev.evidence).ok


def test_synthesis_rewrite_when_fabricated_number():
    """test-plan: số bịa → Guardrail chặn, Synthesis soạn lại."""
    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="biến động",
        evidence=["change_pct=-4.00%"],
    )

    class BadNumThenGood:
        def __init__(self):
            self.calls = 0

        def compose(self, symbol, severity, preferences, *, model, attempt, previous_violations):
            self.calls += 1
            if attempt == 0:
                return "Cảnh báo", "Giá giảm 12.5%; change_pct=-4.00%."
            return "Cảnh báo FPT", "FPT change_pct=-4.00%. Thông tin tham khảo."

    composer = BadNumThenGood()
    result = run_synthesis_agent("FPT", sev, FakeMemoryStore(), composer=composer)
    assert result.draft_attempts > 1
    assert composer.calls > 1
    assert "12.5" not in result.alert.body
    assert check_output(result.alert.title, result.alert.body, sev.evidence).ok


def test_answer_composer_rewrite_when_sell_and_fabricated_number():
    """test-plan AnswerComposer: cùng Guardrail; rewrite khi bán + số lệch."""
    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)

    class AlwaysBadSell:
        def __init__(self):
            self.calls = 0

        def compose(self, **kwargs):
            self.calls += 1
            return "Nên bán FPT với biên 99.9%."

    sell_brain = AlwaysBadSell()
    sell_result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=sell_brain,
        max_attempts=2,
    )
    assert sell_result.hitl_used is False
    assert sell_result.draft_attempts > 1
    assert sell_brain.calls > 1
    assert "nên bán" not in sell_result.answer.lower()
    assert check_output("", sell_result.answer, sell_result.evidence).ok

    class BadNumThenGood:
        def __init__(self):
            self.calls = 0

        def compose(self, **kwargs):
            self.calls += 1
            if kwargs.get("attempt", 0) == 0:
                return "Giá giảm 12.5%."
            return (
                "FPT latest_close=100.0; change_pct=0.00%. "
                "Thông tin tham khảo, không phải lời khuyên đầu tư."
            )

    brain = BadNumThenGood()
    num_result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=brain,
    )
    assert num_result.draft_attempts > 1
    assert brain.calls > 1
    assert "12.5" not in num_result.answer
    assert check_output("", num_result.answer, num_result.evidence).ok


def test_answer_composer_blocks_number_only_in_eval_reasoning():
    """Số chỉ có trong Eval reasoning không được whitelist qua evidence blob."""
    from src.portfolio_watch.domain.agents.answer_composer import (
        HeuristicAnswerDraftBrain,
        build_evidence,
    )

    class FakeEval:
        severity = Severity(
            level=SeverityLevel.MEDIUM,
            confidence=0.5,
            reasoning="Giá có thể giảm thêm 12.5% tới đây",
            evidence=["change_pct=-4.00%"],
        )
        config_proposal = None

    price = PriceAgentResult("FPT", 96.0, 100.0, -4.0)
    evidence = build_evidence(price, None, FakeEval())
    assert not any("12.5" in e for e in evidence)

    draft = HeuristicAnswerDraftBrain().compose(
        question="Tại sao giảm?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=FakeEval(),
        evidence=evidence,
        model="gpt-4o-mini",
        attempt=0,
        previous_violations=[],
    )
    assert check_output("", draft, evidence).ok is False

    result = run_answer_composer(
        question="Tại sao giảm?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=FakeEval(),
    )
    assert "12.5" not in result.answer
    assert check_output("", result.answer, result.evidence).ok
    assert result.hitl_used is False


def test_shared_guardrail_module_for_both_branches():
    """test-plan: nhánh giám sát và hỏi-đáp dùng chung module output_checks."""
    assert output_checks.check_output is check_output
    from src.portfolio_watch.domain.agents import synthesis_agent, answer_composer

    assert synthesis_agent.check_output is check_output
    assert answer_composer.check_output is check_output
