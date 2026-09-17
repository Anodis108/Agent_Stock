"""Unit tests SynthesisAgent — test-plan (heuristic via conftest) + LLM (mock)."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.synthesis_agent import (
    MODEL_HEAVY,
    MODEL_LIGHT,
    HeuristicAlertComposer,
    LlmAlertComposer,
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


def test_llm_composer_uses_registry_and_parses_json():
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            '{"title":"Cảnh báo FPT","body":"Mức high. change_pct=-10.00%. '
            'Đây là thông tin tham khảo, không phải lời khuyên đầu tư."}'
        )

    sev = Severity(
        level=SeverityLevel.HIGH,
        confidence=0.9,
        reasoning="giảm mạnh",
        evidence=["change_pct=-10.00%"],
    )
    result = run_synthesis_agent(
        "FPT",
        sev,
        FakeMemoryStore({"tone": "ngắn gọn"}),
        composer=LlmAlertComposer(chat_fn=fake_chat),
    )
    assert result.draft_attempts == 1
    assert result.guardrail_violations == []
    assert "change_pct=-10.00%" in result.alert.body
    assert "nên mua" not in result.alert.body.lower()
    assert "FPT" in seen[0]
    assert "change_pct=-10.00%" in seen[0]
    assert "tone=ngắn gọn" in seen[0] or "ngắn gọn" in seen[0]
    assert "$symbol" not in seen[0]


def test_llm_composer_rewrite_on_guardrail_violation():
    responses = iter(
        [
            '{"title":"Alert","body":"change_pct=-4.00%. Nhà đầu tư nên mua ngay."}',
            '{"title":"Cảnh báo FPT","body":"change_pct=-4.00%. '
            'Đây là thông tin tham khảo, không phải lời khuyên đầu tư."}',
        ]
    )
    prompts: list[str] = []

    def fake_chat(messages, params=None):
        prompts.append(messages[0]["content"])
        return next(responses)

    sev = Severity(
        level=SeverityLevel.MEDIUM,
        confidence=0.7,
        reasoning="biến động",
        evidence=["change_pct=-4.00%"],
    )
    result = run_synthesis_agent(
        "FPT",
        sev,
        FakeMemoryStore(),
        composer=LlmAlertComposer(chat_fn=fake_chat),
    )
    assert result.draft_attempts > 1
    assert "nên mua" not in result.alert.body.lower()
    assert len(prompts) >= 2
    # Lần 2 phải nhận violations từ guardrail
    assert "nên mua" in prompts[1].lower() or "vi phạm" in prompts[1].lower()


def test_llm_composer_invalid_json_falls_back_clean():
    def bad_chat(messages, params=None):
        return "not-json"

    sev = Severity(
        level=SeverityLevel.LOW,
        confidence=0.5,
        reasoning="ok",
        evidence=["change_pct=-1.00%"],
    )
    result = run_synthesis_agent(
        "FPT",
        sev,
        FakeMemoryStore(),
        composer=LlmAlertComposer(chat_fn=bad_chat),
        max_attempts=2,
    )
    assert "nên mua" not in result.alert.body.lower()
    assert check_output(result.alert.title, result.alert.body, sev.evidence).ok


def test_llm_composer_respects_production_prompt_version(tmp_path, monkeypatch):
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "synthesis_alert"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "SYN_V1"), (2, "SYN_V2")):
        (d / f"v{ver}.yaml").write_text(
            yaml.dump(
                {
                    "name": name,
                    "version": ver,
                    "model": "gpt-4o-mini",
                    "description": f"v{ver}",
                    "owner": "test",
                    "created": "2026-09-17",
                    "changelog": f"v{ver}",
                    "eval_score": None,
                    "template": (
                        f"{marker} symbol=$symbol level=$severity_level "
                        f"conf=$confidence reason=$reasoning evidence=$evidence "
                        f"prefs=$preferences viol=$violations"
                    ),
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(pr, "resolve_prompts_dir", lambda: tmp_path)
    pr.registry.cache_clear()
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            '{"title":"Cảnh báo FPT","body":"change_pct=-1.00%. '
            'Đây là thông tin tham khảo, không phải lời khuyên đầu tư."}'
        )

    sev = Severity(
        level=SeverityLevel.LOW,
        confidence=0.5,
        reasoning="nhẹ",
        evidence=["change_pct=-1.00%"],
    )
    run_synthesis_agent(
        "FPT",
        sev,
        FakeMemoryStore(),
        composer=LlmAlertComposer(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "SYN_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    run_synthesis_agent(
        "FPT",
        sev,
        FakeMemoryStore(),
        composer=LlmAlertComposer(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "SYN_V2" in seen[-1]
    pr.registry.cache_clear()


def test_heuristic_composer_still_injectable():
    sev = Severity(
        level=SeverityLevel.LOW,
        confidence=0.5,
        reasoning="nhẹ",
        evidence=["change_pct=-1.00%"],
    )
    result = run_synthesis_agent(
        "FPT", sev, FakeMemoryStore(), composer=HeuristicAlertComposer()
    )
    assert result.draft_attempts == 1
    assert "change_pct=-1.00%" in result.alert.body
