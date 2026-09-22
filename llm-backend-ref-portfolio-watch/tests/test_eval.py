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

def test_build_report_by_slice_all_five_slices():
    report = eval_mod.build_report([])
    assert len(report.by_slice) == 5
    types = [s.slice_type for s in report.by_slice]
    assert types == ["lookup", "comparison", "out_of_scope", "injection", "diagram"]
    assert report.by_slice[4].slice_type == "diagram"
    assert report.by_slice[4].total == 0
    assert report.by_slice[4].passed == 0
    assert report.by_slice[4].rate is None

def test_build_report_by_slice_with_diagram_cases():
    cases = [
        eval_mod.CaseEvalResult(
            case_id="diagram_01",
            slice_type="diagram",
            question="q",
            output="out",
            rule=eval_mod.RuleBasedScore(passed=True),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        )
    ]
    report = eval_mod.build_report(cases)
    assert len(report.by_slice) == 5
    diag = next(s for s in report.by_slice if s.slice_type == "diagram")
    assert diag.total == 1
    assert diag.passed == 1
    assert diag.rate == 1.0

def test_format_report_includes_diagram_line():
    report = eval_mod.build_report([])
    out = eval_mod.format_report(report)
    assert "  - diagram: 0/0 passed (n/a)" in out

def test_regression_by_slice_catches_comparison_drop():
    baseline = {
        "rate": 1.0,
        "by_slice": {
            "comparison": {"rate": 1.0, "total": 6}
        }
    }
    report = eval_mod.EvalReport(
        total=6, passed=3,
        by_slice=[eval_mod.SliceScore("comparison", 6, 3)],
        failures=[]
    )
    reg = eval_mod.check_regression_by_slice(report, baseline, tolerance=0.05)
    assert reg.passed is False
    assert len(reg.failures) == 1
    assert reg.failures[0][0] == "comparison"
    assert reg.failures[0][1] == 0.5
    assert reg.failures[0][2] == 1.0
    assert reg.failures[0][3] == 0.5

def test_regression_by_slice_skips_diagram_zero_baseline():
    baseline = {
        "rate": 1.0,
        "by_slice": {
            "diagram": {"rate": None, "total": 0}
        }
    }
    report = eval_mod.EvalReport(
        total=1, passed=0,
        by_slice=[eval_mod.SliceScore("diagram", 1, 0)],
        failures=[]
    )
    reg = eval_mod.check_regression_by_slice(report, baseline, tolerance=0.05)
    assert reg.passed is True
    assert len(reg.failures) == 0

def test_eval_gates_passed_fails_on_injection_or_by_slice_regression():
    report_ok = eval_mod.EvalReport(total=1, passed=1, by_slice=[], failures=[])
    reg_ok = eval_mod.RegressionResult(True, True, 1.0, 1.0, 0.0, 0.05, "")
    reg_slice_ok = eval_mod.RegressionBySliceResult(True, [])
    
    # Injection fail
    bad_inj_cases = [eval_mod.CaseEvalResult("inj1", "injection", "q", "", eval_mod.RuleBasedScore(False), eval_mod.LlmJudgeResult(True), False)]
    assert eval_mod.eval_gates_passed(report_ok, bad_inj_cases, reg_ok, reg_slice_ok) is False
    
    # By slice fail
    reg_slice_fail = eval_mod.RegressionBySliceResult(False, [("comparison", 0.0, 1.0, 1.0)])
    ok_inj_cases = [eval_mod.CaseEvalResult("inj1", "injection", "q", "", eval_mod.RuleBasedScore(True), eval_mod.LlmJudgeResult(True), True)]
    assert eval_mod.eval_gates_passed(report_ok, ok_inj_cases, reg_ok, reg_slice_fail) is False
