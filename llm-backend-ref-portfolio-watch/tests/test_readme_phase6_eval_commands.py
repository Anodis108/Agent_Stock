"""Phase 6 — README lệnh eval một case và full golden."""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_phase6_eval_commands():
    text = README.read_text(encoding="utf-8")
    assert "Eval (Phase 6)" in text
    assert "Một case" in text
    assert "Full golden" in text
    assert "python scripts/run_eval.py --run --case-id lookup_01" in text
    assert "python scripts/run_eval.py --run --skip-judge" in text
    assert "python scripts/run_eval.py --self-check" in text
    assert "golden_dataset.yaml" in text
    assert "phase5_regression.py" in text or "--case-delay" in text
