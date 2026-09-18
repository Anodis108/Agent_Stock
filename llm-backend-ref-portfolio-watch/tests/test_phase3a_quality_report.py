"""Phase 3a — quality report có số pass + liệt kê đổi agent/prompt."""

from __future__ import annotations

from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "specs" / "eval" / "phase3a_quality_report.md"


def test_phase3a_quality_report_exists_and_covers_checklist():
    text = REPORT.read_text(encoding="utf-8")
    assert "30" in text and "100%" in text
    assert "lookup" in text and "comparison" in text
    assert "out_of_scope" in text and "injection" in text
    assert "Injection" in text or "injection" in text
    # Liệt kê thay đổi agent/prompt
    assert "news_source" in text or "CafeF" in text
    assert "symbols" in text or "đa mã" in text
    assert "rewrite_question" in text or "supervisor" in text
    assert "answer_compose" in text or "composer" in text
    assert "run_eval" in text
