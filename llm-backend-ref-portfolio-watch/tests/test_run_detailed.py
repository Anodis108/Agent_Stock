"""Unit tests for backend/eval/run_detailed.py with golden_v4.yaml."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_run_detailed_imports_and_paths():
    """Kiểm tra import run_detailed và các cấu hình đường dẫn v4."""
    from backend.eval.run_detailed import (
        GOLDEN_V4_PATH,
        TokenTracker,
        extract_pipeline_trace,
        generate_markdown_report,
    )

    assert GOLDEN_V4_PATH.is_file(), f"GOLDEN_V4_PATH không tồn tại: {GOLDEN_V4_PATH}"

    # Test pipeline trace extraction
    steps = [
        {"tool": "rewrite"},
        {"tool": "supervisor"},
        {"tool": "price_agent"},
        {"tool": "composer"},
    ]
    trace = extract_pipeline_trace(steps)
    assert trace == "rewrite ➔ supervisor ➔ price_agent ➔ composer"

    # Test empty trace
    assert extract_pipeline_trace([]) == "direct"


def test_token_tracker_cost_calculation():
    """Kiểm tra tính toán token và quy đổi chi phí USD / VNĐ."""
    from backend.eval.run_detailed import TokenTracker

    tracker = TokenTracker()
    tracker.record_usage(
        model="gpt-4o-mini",
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
    )

    # Prompt: 1000 * 0.15 / 1M = 0.00015
    # Completion: 500 * 0.60 / 1M = 0.00030
    # Total: 0.00045 USD
    assert tracker.total_prompt_tokens == 1000
    assert tracker.total_completion_tokens == 500
    assert tracker.total_tokens == 1500
    assert pytest.approx(tracker.total_cost_usd, rel=1e-4) == 0.00045
    assert pytest.approx(tracker.total_cost_vnd, rel=1e-2) == 0.00045 * 25400

    tracker.reset()
    assert tracker.total_tokens == 0
    assert tracker.total_cost_usd == 0.0


def test_generate_markdown_report_formatting():
    """Kiểm tra sinh nội dung báo cáo Markdown v4."""
    from backend.eval.run import SliceScore, EvalReport
    from backend.eval.run_detailed import generate_markdown_report

    mock_report = EvalReport(
        total=1,
        passed=1,
        by_slice=[SliceScore(slice_type="lookup", total=1, passed=1)],
        failures=[],
    )

    mock_detailed = [
        {
            "index": 1,
            "case_id": "lookup_01",
            "slice": "lookup",
            "question": "Giá FPT hôm nay bao nhiêu?",
            "expected": "Trả lời có FPT",
            "answer": "Giá FPT hiện tại là 135.0.",
            "status": "PASS",
            "passed": True,
            "pipeline_trace": "price_agent ➔ composer",
            "steps": [],
            "latency_s": 0.5,
            "tokens": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "app_tokens": 150,
                "judge_tokens": 0,
            },
            "cost": {"usd": 0.0001, "vnd": 2.54},
            "scoring": {
                "rule_based": {"passed": True, "missing": [], "forbidden_found": []},
                "llm_judge": {"skipped": True},
                "task_success": None,
                "trajectory": None,
            },
            "error": None,
        }
    ]

    md = generate_markdown_report(
        dataset_name="golden_v4.yaml",
        detailed_results=mock_detailed,
        report=mock_report,
        total_tokens=150,
        total_app_tokens=150,
        total_judge_tokens=0,
        total_cost_usd=0.0001,
        total_cost_vnd=2.54,
        total_duration=0.5,
    )

    assert "# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v4.yaml" in md
    assert "lookup_01" in md
    assert "price_agent ➔ composer" in md
    assert "PASS" in md
