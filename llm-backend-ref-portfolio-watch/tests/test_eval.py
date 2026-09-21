"""Eval golden — schema, scorer, injection gate."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.portfolio_watch.eval import run as eval_mod

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "specs" / "eval" / "golden_dataset.yaml"


def test_golden_30_cases_18_6_3_3():
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))
    assert len(data["cases"]) == 30
    counts = {"lookup": 0, "comparison": 0, "out_of_scope": 0, "injection": 0}
    for c in data["cases"]:
        counts[c["slice"]["type"]] += 1
    assert counts == {"lookup": 18, "comparison": 6, "out_of_scope": 3, "injection": 3}


def test_v2_baseline_30_30():
    data = json.loads((ROOT / "specs" / "eval" / "v2_baseline.json").read_text())
    assert data["total"] == 30 and data["passed"] == 30 and data["rate"] == 1.0


def test_rule_based_scorer():
    ok = eval_mod.score_rule_based(
        "Giá FPT hôm nay 100",
        must_include=["FPT"],
        must_not_include=["nên mua"],
    )
    assert ok.passed is True
    bad = eval_mod.score_rule_based(
        "Khuyên mua cổ phiến này",
        must_include=["FPT"],
        must_not_include=["nên mua"],
    )
    assert bad.passed is False


def test_injection_gate_requires_100_percent():
    ok_results = [
        eval_mod.CaseEvalResult(
            case_id="injection_01",
            slice_type="injection",
            question="q",
            output="",
            rule=eval_mod.RuleBasedScore(passed=True),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        )
    ]
    assert eval_mod.check_injection_gate(ok_results).passed is True

    fail = list(ok_results)
    fail[0] = eval_mod.CaseEvalResult(
        case_id="injection_01",
        slice_type="injection",
        question="q",
        output="fail",
        rule=eval_mod.RuleBasedScore(passed=False),
        judge=eval_mod.LlmJudgeResult(skipped=True),
        passed=False,
    )
    assert eval_mod.check_injection_gate(fail).passed is False


def test_eval_self_check():
    assert eval_mod.main(["--self-check"]) == 0
