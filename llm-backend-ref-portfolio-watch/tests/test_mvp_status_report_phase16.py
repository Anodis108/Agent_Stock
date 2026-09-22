"""Phase 16 — mvp-status-report có section V3 complete (AC 1–9)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "specs" / "mvp-status-report.md"


def test_mvp_status_report_has_v3_complete_section():
    content = REPORT.read_text(encoding="utf-8")

    assert "V3 complete" in content
    assert "AC 1-9" in content or all(f"| {i}." in content for i in range(1, 10))

    lower = content.lower()
    assert "docker compose" in lower
    assert "eval" in lower
    assert "## how to run (docker-first)" in lower
