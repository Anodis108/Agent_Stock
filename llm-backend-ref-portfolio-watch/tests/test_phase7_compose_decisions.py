"""Phase 7 — change-log ghi quyết định compose split (port / volume / DB)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE_LOG = ROOT / "specs" / "change-log.md"
PLAN = ROOT / "specs" / "implementation-plan.md"


def test_change_log_records_split_compose_decisions_2026_09_18():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Phase 7 hoàn thành" in text or "Ngày hoàn thành Phase 7" in text
    assert "2026-09-18" in text
    assert "portfolio-watch:split" in text or "portfolio-watch:split" in text
    assert "portfolio-watch-data" in text
    assert "pw_data" in text or "/app/data" in text
    assert "8001" in text and "5173" in text
    assert "APP_HOST_PORT" in text
    assert "BACKEND_SQLITE_PATH" in text or "backend_store.db" in text
    assert "AI_BASE_URL" in text and "http://ai:8001" in text
    assert "python:3.12-slim" in text


def test_implementation_plan_phase7_compose_decision_note():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 7")
    end = plan.index("## Phase 8")
    block = plan[start:end]
    assert "- [ ]" not in block
    assert "quyết định Docker" in block or "image base" in block
    assert "portfolio-watch:split" in block or "change-log.md" in block
