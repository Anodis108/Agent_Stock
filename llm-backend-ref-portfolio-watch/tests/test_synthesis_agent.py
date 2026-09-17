from __future__ import annotations

from src.portfolio_watch.domain.agents.synthesis_agent import (
    MODEL_HEAVY,
    MODEL_LIGHT,
    run_synthesis_agent,
    select_model,
)
from src.portfolio_watch.domain.entities import Severity, SeverityLevel
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from tests.fakes import FakeMemoryStore


def test_high_severity_selects_heavy_model():
    sev = Severity(
        level=SeverityLevel.HIGH,
        confidence=0.9,
        reasoning="giảm mạnh",
        evidence=["change_pct=-10.00%"],
    )
    assert select_model(sev) == MODEL_HEAVY
    result = run_synthesis_agent("FPT", sev, FakeMemoryStore())
    assert result.model == MODEL_HEAVY
    assert result.draft_attempts == 1
    assert result.alert.body


def test_low_severity_selects_light_model():
    sev = Severity(
        level=SeverityLevel.LOW,
        confidence=0.5,
        reasoning="nhẹ",
        evidence=["change_pct=-1.00%"],
    )
    assert select_model(sev) == MODEL_LIGHT


def test_buy_sell_advice_triggers_rewrite():
    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="biến động",
        evidence=["change_pct=-4.00%"],
    )

    class BadThenGood:
        def __init__(self):
            self.calls = 0

        def compose(self, symbol, severity, preferences, *, model, attempt, previous_violations):
            self.calls += 1
            if attempt == 0:
                return "Cảnh báo", "FPT change_pct=-4.00%. Nhà đầu tư nên mua bắt đáy."
            return (
                "Cảnh báo FPT",
                "FPT change_pct=-4.00%. Thông tin tham khảo, không phải lời khuyên đầu tư.",
            )

    composer = BadThenGood()
    result = run_synthesis_agent("FPT", sev, FakeMemoryStore(), composer=composer)
    assert result.draft_attempts > 1
    assert composer.calls > 1
    assert "nên mua" not in result.alert.body.lower()


def test_nen_ban_also_blocked_and_forced_fallback_is_clean():
    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="nên bán hết danh mục",
        evidence=["change_pct=-4.00%"],
    )

    class AlwaysBad:
        def compose(self, symbol, severity, preferences, *, model, attempt, previous_violations):
            return "Alert", "change_pct=-4.00%. Nhà đầu tư nên bán ngay."

    result = run_synthesis_agent(
        "FPT", sev, FakeMemoryStore(), composer=AlwaysBad(), max_attempts=2
    )
    assert result.draft_attempts == 2
    assert "nên bán" not in result.alert.body.lower()
    assert "nên mua" not in result.alert.body.lower()
    assert check_output(result.alert.title, result.alert.body, sev.evidence).ok


def test_guardrail_blocks_number_not_in_evidence():
    bad = check_output(
        "Cảnh báo",
        "Giá giảm 12.5% trong phiên.",
        evidence=["change_pct=-4.00%"],
    )
    assert bad.ok is False
    assert any("không khớp evidence" in v for v in bad.violations)

    # Số đứng trước dấu chấm câu vẫn phải bị kiểm
    bad_period = check_output(
        "Cảnh báo",
        "Giá giảm 12.5.",
        evidence=["change_pct=-4.00%"],
    )
    assert bad_period.ok is False

    good = check_output(
        "Cảnh báo",
        "Giá change_pct=-4.00% trong phiên.",
        evidence=["change_pct=-4.00%"],
    )
    assert good.ok is True
