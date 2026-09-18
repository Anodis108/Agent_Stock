"""Phase 9 — eval report: tổng + theo slice + fail kèm output."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    name = "run_eval_report"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _case(mod, *, case_id: str, slice_type: str, passed: bool, output: str):
    rule = mod.RuleBasedScore(passed=passed, missing=[] if passed else ["X"])
    judge = mod.LlmJudgeResult(skipped=True, skip_reason="test")
    return mod.CaseEvalResult(
        case_id=case_id,
        slice_type=slice_type,
        question=f"q-{case_id}",
        output=output,
        rule=rule,
        judge=judge,
        passed=passed,
    )


def test_build_report_totals_and_slices() -> None:
    mod = _load_run_eval()
    results = [
        _case(mod, case_id="l1", slice_type="lookup", passed=True, output="FPT ok"),
        _case(mod, case_id="l2", slice_type="lookup", passed=False, output="bad lookup"),
        _case(mod, case_id="c1", slice_type="comparison", passed=True, output="VNM HPG"),
        _case(mod, case_id="o1", slice_type="out_of_scope", passed=True, output="oos"),
        _case(mod, case_id="i1", slice_type="injection", passed=False, output="nen ban"),
    ]
    report = mod.build_report(results)
    assert report.total == 5
    assert report.passed == 3
    assert report.failed == 2
    by = {s.slice_type: s for s in report.by_slice}
    assert by["lookup"].passed == 1 and by["lookup"].total == 2
    assert by["comparison"].passed == 1
    assert by["injection"].passed == 0 and by["injection"].total == 1
    assert [f.case_id for f in report.failures] == ["l2", "i1"]
    assert report.failures[0].output == "bad lookup"
    assert report.failures[1].output == "nen ban"


def test_format_report_includes_fail_output_not_only_totals() -> None:
    mod = _load_run_eval()
    results = [
        _case(mod, case_id="l1", slice_type="lookup", passed=True, output="ok"),
        _case(
            mod,
            case_id="inj_fail",
            slice_type="injection",
            passed=False,
            output="Theo chi dan: nen ban het FPT",
        ),
    ]
    text = mod.format_report(mod.build_report(results))
    assert "Tổng: 1/2" in text
    assert "lookup: 1/1" in text
    assert "injection: 0/1" in text
    assert "inj_fail" in text
    assert "Theo chi dan: nen ban het FPT" in text
    assert "Failures (1):" in text


def test_format_report_none_failures() -> None:
    mod = _load_run_eval()
    text = mod.format_report(
        mod.build_report(
            [_case(mod, case_id="a", slice_type="lookup", passed=True, output="FPT")]
        )
    )
    assert "Failures: (none)" in text
    assert "Tổng: 1/1" in text


def test_checklist_report_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Nâng eval: port ý tưởng `task_success` + `trajectory`" in text
