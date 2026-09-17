"""Phase 6/7/8 — change-log ghi ngày hoàn thành từng phase + quyết định."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE_LOG = ROOT / "specs" / "change-log.md"
PLAN = ROOT / "specs" / "implementation-plan.md"


def test_change_log_has_phase_completion_dates_summary():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Ngày hoàn thành từng phase" in text
    for phase in range(1, 11):
        assert f"| {phase} |" in text or f"| {phase} " in text
    assert "2026-09-16" in text  # Phase 1–2
    assert "2026-09-17" in text  # Phase 3–10
    assert "Phase 7" in text or "| 7 |" in text
    assert "Phase 8" in text or "| 8 |" in text
    assert "Phase 9" in text or "| 9 |" in text
    assert "Phase 10" in text or "| 10 |" in text
    row7 = next(line for line in text.splitlines() if line.startswith("| 7 |"))
    row8 = next(line for line in text.splitlines() if line.startswith("| 8 |"))
    row9 = next(line for line in text.splitlines() if line.startswith("| 9 |"))
    row10 = next(line for line in text.splitlines() if line.startswith("| 10 |"))
    assert "2026-09-17" in row7 and "chưa" not in row7.lower()
    assert "2026-09-17" in row8 and "chưa" not in row8.lower()
    assert "2026-09-17" in row9 and "chưa" not in row9.lower()
    assert "2026-09-17" in row10 and "chưa" not in row10.lower()
    assert "test_product_spec_ac.py" in text
    assert "verify_clean_local.py" in text
    assert "verify_clean_docker.py" in text
    assert "test_prompt_registry.py" in text
    assert "run_eval.py" in text or "baseline.json" in text
    assert "draw_agent_graph.py" in text


def test_change_log_records_docker_decisions_and_phase7_date():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "python:3.12-slim" in text
    assert "8000" in text
    assert "APP_HOST_PORT" in text
    assert "portfolio-watch-sqlite" in text
    assert "/app/data" in text
    assert "Ngày hoàn thành Phase 7" in text or "Phase 7 hoàn thành" in text
    assert "**2026-09-17**" in text


def test_change_log_records_phase8_prompt_decisions_and_date():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Ngày hoàn thành Phase 8" in text or "Phase 8 hoàn thành" in text
    assert "string.Template" in text
    assert "gpt-4o-mini" in text
    assert "event_classification" in text
    assert "news_agent_react" in text
    assert "eval_severity" in text
    assert "synthesis_alert" in text
    assert "supervisor_routing" in text
    assert "rewrite_question" in text
    assert "answer_compose" in text
    assert "DETERMINISTIC" in text or "temperature=0" in text


def test_change_log_records_phase9_baseline_and_date():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Ngày hoàn thành Phase 9" in text or "Phase 9 hoàn thành" in text
    assert "baseline" in text.lower()
    assert "30/30" in text
    assert "specs/eval/baseline.json" in text
    assert "0.05" in text
    baseline = ROOT / "specs" / "eval" / "baseline.json"
    assert baseline.is_file()
    raw = baseline.read_text(encoding="utf-8")
    assert '"rate": 1.0' in raw or '"rate": 1' in raw
    assert '"passed": 30' in raw
    assert '"total": 30' in raw


def test_change_log_and_readme_phase10_complete():
    text = CHANGE_LOG.read_text(encoding="utf-8")
    assert "Ngày hoàn thành Phase 10" in text or "Phase 10 hoàn thành" in text
    assert "draw_agent_graph.py" in text
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/draw_agent_graph.py" in readme
    assert "--verify" in readme
    assert "docs/agent_graph.mmd" in readme
    assert "Sắp tới — chưa implement (Phase 8-10)" not in readme


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
    end = plan.index("## Phase 8")
    block = plan[start:end]
    assert "- [ ]" not in block
    assert "quyết định Docker" in block or "image base" in block


def test_implementation_plan_phase8_fully_checked():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 8")
    end = plan.index("## Phase 9")
    block = plan[start:end]
    assert "- [ ]" not in block
    assert "Prompt Registry" in block or "prompt_registry" in block
    assert "change-log.md" in block


def test_implementation_plan_phase9_fully_checked():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 9")
    end = plan.index("## Phase 10")
    block = plan[start:end]
    assert "- [ ]" not in block
    assert "golden_dataset.yaml" in block
    assert "run_eval.py" in block
    assert "baseline" in block.lower()
    assert "change-log.md" in block


def test_implementation_plan_phase10_fully_checked():
    plan = PLAN.read_text(encoding="utf-8")
    start = plan.index("## Phase 10")
    block = plan[start:]
    assert "- [ ]" not in block
    assert "draw_agent_graph.py" in block
    assert "README.md" in block
    assert "change-log.md" in block
