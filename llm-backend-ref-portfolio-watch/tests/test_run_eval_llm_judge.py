"""Phase 9 — LLM-judge scorer in scripts/run_eval.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    spec = importlib.util.spec_from_file_location("run_eval_judge", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_eval_judge"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_llm_judge_skipped_when_rule_fails() -> None:
    mod = _load_run_eval()
    case = {
        "id": "lookup_01",
        "question": "Giá FPT?",
        "expected": "Có FPT và giá",
        "slice": {"type": "lookup", "multihop": False},
        "must_include": ["FPT"],
        "must_not_include": [],
    }
    rule = mod.score_case_rule_based(case, "không nhắc mã")
    assert rule.passed is False

    def boom(*_a, **_k):
        raise AssertionError("must not call LLM")

    result = mod.score_case_llm_judge(case, "không nhắc mã", rule, chat_parsed_fn=boom)
    assert result.skipped is True
    assert "rule-based" in (result.skip_reason or "")
    assert result.score is None


def test_llm_judge_skipped_for_out_of_scope_and_injection() -> None:
    mod = _load_run_eval()

    def boom(*_a, **_k):
        raise AssertionError("must not call LLM")

    for stype in ("out_of_scope", "injection"):
        case = {
            "question": "q",
            "expected": "e",
            "slice": {"type": stype, "multihop": False},
            "must_include": [],
            "must_not_include": [],
        }
        rule = mod.RuleBasedScore(passed=True)
        result = mod.score_case_llm_judge(case, "ok", rule, chat_parsed_fn=boom)
        assert result.skipped is True
        assert "không dùng LLM-judge" in (result.skip_reason or "")


def test_llm_judge_runs_for_lookup_and_comparison_when_rule_passes() -> None:
    mod = _load_run_eval()
    calls: list[dict] = []

    def fake_parse(messages, schema, params):
        calls.append({"params": params, "schema": schema})
        assert params.temperature == 0.0
        assert schema is mod.LlmJudgeScore
        return mod.LlmJudgeScore(
            correctness=5, completeness=4, grounding=5, reasoning="tốt"
        )

    for stype in ("lookup", "comparison"):
        calls.clear()
        case = {
            "question": "So sánh VNM HPG" if stype == "comparison" else "Giá FPT?",
            "expected": "có mã",
            "slice": {"type": stype, "multihop": stype == "comparison"},
            "must_include": [],
            "must_not_include": [],
        }
        rule = mod.RuleBasedScore(passed=True)
        result = mod.score_case_llm_judge(
            case, "VNM và HPG ổn" if stype == "comparison" else "FPT 100",
            rule,
            chat_parsed_fn=fake_parse,
        )
        assert result.skipped is False
        assert result.passed is True
        assert result.score is not None
        assert result.score.overall >= mod.JUDGE_PASS_THRESHOLD
        assert len(calls) == 1


def test_llm_judge_fail_below_threshold() -> None:
    mod = _load_run_eval()

    def fake_parse(*_a, **_k):
        return mod.LlmJudgeScore(
            correctness=2, completeness=2, grounding=1, reasoning="yếu"
        )

    case = {
        "question": "Giá FPT?",
        "expected": "có giá",
        "slice": {"type": "lookup", "multihop": False},
    }
    result = mod.score_case_llm_judge(
        case, "FPT", mod.RuleBasedScore(passed=True), chat_parsed_fn=fake_parse
    )
    assert result.skipped is False
    assert result.passed is False


def test_judge_model_constant_pinned() -> None:
    mod = _load_run_eval()
    assert mod.JUDGE_MODEL == "gpt-4o-mini"


def test_checklist_llm_judge_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert (
        "- [x] `scripts/run_eval.py` — scorer LLM-judge (correctness/completeness/"
        in text
    )
