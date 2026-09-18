"""Phase 9 — regression gate: baseline + tolerance."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"


def _load_run_eval():
    name = "run_eval_regression"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _report(mod, *, total: int, passed: int):
    results = []
    for i in range(total):
        ok = i < passed
        rule = mod.RuleBasedScore(passed=ok, missing=[] if ok else ["X"])
        results.append(
            mod.CaseEvalResult(
                case_id=f"c{i}",
                slice_type="lookup",
                question=f"q{i}",
                output="ok" if ok else "bad",
                rule=rule,
                judge=mod.LlmJudgeResult(skipped=True, skip_reason="t"),
                passed=ok,
            )
        )
    return mod.build_report(results)


def test_save_and_load_baseline(tmp_path: Path) -> None:
    mod = _load_run_eval()
    report = _report(mod, total=10, passed=9)
    path = tmp_path / "baseline.json"
    saved = mod.save_baseline(report, path, tolerance=0.05)
    assert saved == path
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["total"] == 10
    assert data["passed"] == 9
    assert abs(data["rate"] - 0.9) < 1e-9
    assert data["tolerance"] == 0.05
    loaded = mod.load_baseline(path)
    assert loaded["rate"] == data["rate"]


def test_check_regression_pass_within_tolerance() -> None:
    mod = _load_run_eval()
    baseline = {"rate": 0.90, "tolerance": 0.05}
    # drop 0.04 ≤ 0.05
    current = _report(mod, total=100, passed=86)
    reg = mod.check_regression(current, baseline, tolerance=0.05)
    assert reg.compared is True
    assert reg.passed is True
    assert abs(reg.drop - 0.04) < 1e-9


def test_check_regression_fail_when_drop_exceeds_tolerance() -> None:
    mod = _load_run_eval()
    baseline = {"rate": 0.90, "tolerance": 0.05}
    # drop 0.10 > 0.05
    current = _report(mod, total=10, passed=8)
    reg = mod.check_regression(current, baseline)
    assert reg.compared is True
    assert reg.passed is False
    assert "FAIL" in reg.message


def test_check_regression_no_baseline_skips() -> None:
    mod = _load_run_eval()
    report = _report(mod, total=5, passed=5)
    reg = mod.check_regression(report, None)
    assert reg.compared is False
    assert reg.passed is True
    assert "Chưa có baseline" in reg.message


def test_tolerance_constant_defined() -> None:
    mod = _load_run_eval()
    assert mod.REGRESSION_TOLERANCE == 0.05


def test_checklist_regression_gate_checked() -> None:
    text = (ROOT / "specs" / "implementation-plan.md").read_text(encoding="utf-8")
    assert "- [x] Chạy baseline eval hiện tại" in text
    assert "baseline_debug.json" in text
