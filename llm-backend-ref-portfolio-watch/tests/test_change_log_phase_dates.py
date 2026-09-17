"""Phase 6/7 — change-log ghi ngày hoàn thành từng phase + quyết định Docker."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE_LOG = ROOT / "specs" / "change-log.md"
PLAN = ROOT / "specs" / "implementation-plan.md"


def test_change_log_has_phase_completion_dates_summary():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Ngày hoàn thành từng phase" in text
    for phase in range(1, 8):
        assert f"| {phase} |" in text or f"| {phase} " in text
    assert "2026-09-16" in text  # Phase 1–2
    assert "2026-09-17" in text  # Phase 3–7
    assert "Phase 7" in text or "| 7 |" in text
    # Hàng Phase 7 trong bảng tóm tắt đã có ngày (không còn placeholder)
    row7 = next(
        line for line in text.splitlines() if line.startswith("| 7 |")
    )
    assert "2026-09-17" in row7
    assert "chưa" not in row7.lower()
    assert "test_product_spec_ac.py" in text
    assert "verify_clean_local.py" in text
    assert "verify_clean_docker.py" in text


def test_change_log_records_docker_decisions_and_phase7_date():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "python:3.12-slim" in text
    assert "8000" in text
    assert "APP_HOST_PORT" in text
    assert "portfolio-watch-sqlite" in text
    assert "/app/data" in text
    assert "Ngày hoàn thành Phase 7" in text or "Phase 7 hoàn thành" in text
    assert "**2026-09-17**" in text


def test_implementation_plan_phase6_fully_checked():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 6")
    end = plan.index("## Phase 7")
    block = plan[start:end]
    assert "- [ ]" not in block
    assert "ngày hoàn thành từng phase" in block.lower() or "change-log.md" in block


def test_implementation_plan_phase7_fully_checked():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 7")
    block = plan[start:]
    assert "- [ ]" not in block
    assert "quyết định Docker" in block or "image base" in block
