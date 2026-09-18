"""Phase 5 — Eval policy: không nới scorer; fail → blocked + Phase 3c."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_eval.py"
BLOCKED = ROOT / "specs" / "eval" / "blocked_cases.yaml"


def _load():
    spec = importlib.util.spec_from_file_location("run_eval", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_eval"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_scorer_locks_reject_relaxed_tolerance_and_judge():
    mod = _load()
    mod.assert_scorer_locks()
    with pytest.raises(ValueError, match="tolerance|nới"):
        mod.assert_scorer_locks(tolerance=mod.REGRESSION_TOLERANCE_MAX + 0.2)
    with pytest.raises(ValueError, match="JUDGE|nới|sàn"):
        mod.assert_scorer_locks(judge_threshold=2.0)
    assert mod.JUDGE_PASS_THRESHOLD >= mod.JUDGE_PASS_THRESHOLD_MIN
    assert mod.REGRESSION_TOLERANCE <= mod.REGRESSION_TOLERANCE_MAX


def test_blocked_cases_file_loads_and_requires_fields(tmp_path):
    mod = _load()
    assert BLOCKED.is_file()
    empty = mod.load_blocked_cases(BLOCKED)
    assert empty == []

    bad = tmp_path / "blocked.yaml"
    bad.write_text(
        "blocked:\n  - id: lookup_01\n    reason: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="phase3c_task"):
        mod.load_blocked_cases(bad)

    good = tmp_path / "blocked_ok.yaml"
    good.write_text(
        "blocked:\n"
        "  - id: lookup_99\n"
        "    reason: nguồn giá chết\n"
        "    phase3c_task: retry price source\n"
        "    since: 2026-09-18\n",
        encoding="utf-8",
    )
    rows = mod.load_blocked_cases(good)
    assert len(rows) == 1
    assert rows[0].id == "lookup_99"
    assert "retry" in rows[0].phase3c_task


def test_fail_policy_guidance_mentions_fix_or_block():
    mod = _load()
    data = mod.load_golden_dataset()
    case = next(c for c in data["cases"] if c["id"] == "lookup_01")
    results = mod.run_eval(
        [case],
        answer_fn=lambda _q: "thiếu",
        skip_judge=True,
        skip_agent_eval=True,
    )
    report = mod.build_report(results)
    text = mod.format_fail_policy_guidance(report.failures, [])
    assert "Phase 3c" in text or "3c" in text
    assert "lookup_01" in text
    assert "CHƯA blocked" in text
