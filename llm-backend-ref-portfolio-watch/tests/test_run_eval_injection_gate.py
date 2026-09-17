"""Phase 9 — injection gate cứng (100%, no tolerance)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    name = "run_eval_injection_gate"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _res(mod, *, case_id: str, slice_type: str, passed: bool):
    return mod.CaseEvalResult(
        case_id=case_id,
        slice_type=slice_type,
        question="q",
        output="ok" if passed else "nên bán hết",
        rule=mod.RuleBasedScore(passed=passed, missing=[] if passed else ["x"]),
        judge=mod.LlmJudgeResult(skipped=True, skip_reason="t"),
        passed=passed,
    )


def test_injection_gate_pass_when_all_injection_ok() -> None:
    mod = _load_run_eval()
    results = [
        _res(mod, case_id="l1", slice_type="lookup", passed=False),  # lookup fail OK
        _res(mod, case_id="i1", slice_type="injection", passed=True),
        _res(mod, case_id="i2", slice_type="injection", passed=True),
        _res(mod, case_id="i3", slice_type="injection", passed=True),
    ]
    gate = mod.check_injection_gate(results)
    assert gate.passed is True
    assert gate.total == 3
    assert gate.failed_ids == []
    assert "100%" in gate.message


def test_injection_gate_fail_on_any_injection_fail_no_tolerance() -> None:
    mod = _load_run_eval()
    results = [
        _res(mod, case_id="i1", slice_type="injection", passed=True),
        _res(mod, case_id="i2", slice_type="injection", passed=False),
        _res(mod, case_id="i3", slice_type="injection", passed=True),
    ]
    gate = mod.check_injection_gate(results)
    assert gate.passed is False
    assert gate.failed_ids == ["i2"]
    assert "no tolerance" in gate.message


def test_injection_gate_empty_run_skipped() -> None:
    mod = _load_run_eval()
    gate = mod.check_injection_gate(
        [_res(mod, case_id="l1", slice_type="lookup", passed=True)]
    )
    assert gate.passed is True
    assert gate.total == 0


def test_eval_gates_passed_requires_injection() -> None:
    mod = _load_run_eval()
    results = [
        _res(mod, case_id="l1", slice_type="lookup", passed=True),
        _res(mod, case_id="i1", slice_type="injection", passed=False),
    ]
    report = mod.build_report(results)
    # lookup pass, injection fail → report.failed > 0 anyway
    reg = mod.RegressionResult(
        compared=False,
        passed=True,
        current_rate=report.rate,
        baseline_rate=None,
        drop=None,
        tolerance=0.05,
        message="skip",
    )
    assert mod.eval_gates_passed(report, results, reg) is False

    # Chỉ injection fail nhưng giả sử overall rate vẫn trong tolerance:
    # gate injection vẫn chặn.
    only_inj_fail = [
        _res(mod, case_id="l1", slice_type="lookup", passed=True),
        _res(mod, case_id="l2", slice_type="lookup", passed=True),
        _res(mod, case_id="i1", slice_type="injection", passed=False),
    ]
    # Force: check_injection_gate alone fails even if we ignore report.failed
    assert mod.check_injection_gate(only_inj_fail).passed is False


def test_checklist_injection_gate_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert (
        "- [x] Regression gate cứng riêng cho slice `injection`:"
        in text
    )
