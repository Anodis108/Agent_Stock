"""Evaluation suite tests (tests/test_eval.py).

Comprehensive tests for:
1. Golden Dataset v5 schema, 40 cases across 7 slices (lookup, comparison, explain_why,
   charting_diagram, session_memory, out_of_scope, injection).
2. Rule-based scoring: must_include and must_not_include enforcement.
3. Zero-Tolerance Security Gate: 100% pass required on Prompt Injection.
4. Slice reporting, failure aggregation, and regression gates.
5. Token tracking and USD/VND cost conversion.
6. Pipeline trace agent extraction for Timeline & evaluation artifacts.
7. Detailed Markdown evaluation report generation.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import yaml

from backend.eval import run as eval_mod
from backend.eval.run_detailed import (
    GOLDEN_V5_PATH,
    TokenTracker,
    extract_pipeline_trace,
    generate_markdown_report,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_V5_RESOURCE = ROOT / "resources" / "eval" / "golden_v5.yaml"
GOLDEN_V5_SPECS = ROOT / "specs" / "eval" / "golden_v5.yaml"


# ==============================================================================
# 1. Golden Dataset v5 Structure & Slices Tests
# ==============================================================================

@pytest.mark.parametrize("file_path", [GOLDEN_V5_RESOURCE, GOLDEN_V5_SPECS])
def test_golden_v5_structure_and_counts(file_path: Path):
    """Kiểm tra tính toàn vẹn và phân bổ 40 cases của Golden Dataset v5."""
    assert file_path.is_file(), f"File không tồn tại: {file_path}"

    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    assert data.get("dataset") == "portfolio_watch"
    assert str(data.get("version")) == "5"
    assert data.get("changelog"), "Phải có trường changelog"

    cases = data.get("cases", [])
    assert len(cases) == 40, f"Golden Dataset v5 bắt buộc phải có đúng 40 cases, hiện tại có {len(cases)}"

    ids: set[str] = set()
    slice_counts = {
        "lookup": 0,
        "comparison": 0,
        "explain_why": 0,
        "charting_diagram": 0,
        "session_memory": 0,
        "out_of_scope": 0,
        "injection": 0,
    }

    for case in cases:
        case_id = case.get("id")
        assert case_id, "Case thiếu trường id"
        assert case_id not in ids, f"Trùng lặp case id: {case_id}"
        ids.add(case_id)

        assert case.get("question"), f"Case {case_id} thiếu câu hỏi (question)"
        assert case.get("expected"), f"Case {case_id} thiếu kết quả mong đợi (expected)"

        slice_data = case.get("slice") or {}
        slice_type = slice_data.get("type")
        assert slice_type in slice_counts, f"Case {case_id} có slice.type không hợp lệ: {slice_type}"
        slice_counts[slice_type] += 1

        assert slice_data.get("difficulty") in {"easy", "medium", "hard"}, (
            f"Case {case_id} có độ khó không hợp lệ"
        )
        assert isinstance(case.get("must_include", []), list)
        assert isinstance(case.get("must_not_include", []), list)

    # Kiểm tra số lượng phân bổ theo đúng đặc tả:
    # lookup (12), comparison (8), explain_why (6), charting_diagram (4), session_memory (3), out_of_scope (4), injection (3)
    assert slice_counts["lookup"] == 12, f"Expected 12 lookup cases, got {slice_counts['lookup']}"
    assert slice_counts["comparison"] == 8, f"Expected 8 comparison cases, got {slice_counts['comparison']}"
    assert slice_counts["explain_why"] == 6, f"Expected 6 explain_why cases, got {slice_counts['explain_why']}"
    assert slice_counts["charting_diagram"] == 4, f"Expected 4 charting_diagram cases, got {slice_counts['charting_diagram']}"
    assert slice_counts["session_memory"] == 3, f"Expected 3 session_memory cases, got {slice_counts['session_memory']}"
    assert slice_counts["out_of_scope"] == 4, f"Expected 4 out_of_scope cases, got {slice_counts['out_of_scope']}"
    assert slice_counts["injection"] == 3, f"Expected 3 injection cases, got {slice_counts['injection']}"


# ==============================================================================
# 2. Rule-Based Scorer & Injection Gate Tests
# ==============================================================================

def test_rule_based_scorer():
    """Kiểm tra chấm điểm rule-based: bắt buộc chuỗi must_include và cấm must_not_include."""
    ok = eval_mod.score_rule_based(
        "Giá FPT hôm nay 135.0",
        must_include=["FPT"],
        must_not_include=["khuyên mua"],
    )
    assert ok.passed is True

    bad = eval_mod.score_rule_based(
        "Khuyên mua cổ phiếu này ngay",
        must_include=["FPT"],
        must_not_include=["khuyên mua"],
    )
    assert bad.passed is False


def test_injection_gate_requires_100_percent():
    """Chốt chặn an toàn: Slice injection bắt buộc phải đạt tuyệt đối 100% Pass."""
    ok_results = [
        eval_mod.CaseEvalResult(
            case_id="injection_01",
            slice_type="injection",
            question="q",
            output="Từ chối can thiệp hệ thống",
            rule=eval_mod.RuleBasedScore(passed=True),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        )
    ]
    assert eval_mod.check_injection_gate(ok_results).passed is True

    fail_results = [
        eval_mod.CaseEvalResult(
            case_id="injection_01",
            slice_type="injection",
            question="q",
            output="System prompt leaked",
            rule=eval_mod.RuleBasedScore(passed=False),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=False,
        )
    ]
    assert eval_mod.check_injection_gate(fail_results).passed is False


# ==============================================================================
# 3. Report & Slice Regression Tests
# ==============================================================================

def test_build_report_and_slice_summary():
    """Kiểm tra tổng hợp kết quả theo từng slice."""
    cases = [
        eval_mod.CaseEvalResult(
            case_id="lookup_01",
            slice_type="lookup",
            question="q",
            output="out",
            rule=eval_mod.RuleBasedScore(passed=True),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        ),
        eval_mod.CaseEvalResult(
            case_id="comparison_01",
            slice_type="comparison",
            question="q",
            output="out",
            rule=eval_mod.RuleBasedScore(passed=True),
            judge=eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        ),
    ]
    report = eval_mod.build_report(cases)
    assert report.total == 2
    assert report.passed == 2
    assert len(report.by_slice) >= 2


def test_regression_by_slice_catches_drop():
    """Kiểm tra phát hiện sụt giảm điểm số (regression) trên từng slice."""
    baseline = {
        "rate": 1.0,
        "by_slice": {
            "comparison": {"rate": 1.0, "total": 6}
        }
    }
    report = eval_mod.EvalReport(
        total=6,
        passed=3,
        by_slice=[eval_mod.SliceScore("comparison", 6, 3)],
        failures=[],
    )
    reg = eval_mod.check_regression_by_slice(report, baseline, tolerance=0.05)
    assert reg.passed is False
    assert len(reg.failures) == 1
    assert reg.failures[0][0] == "comparison"


def test_eval_gates_passed_fails_on_injection():
    """Kiểm tra eval_gates_passed đánh trượt toàn bộ nếu có case injection không đạt."""
    report_ok = eval_mod.EvalReport(total=1, passed=1, by_slice=[], failures=[])
    reg_ok = eval_mod.RegressionResult(True, True, 1.0, 1.0, 0.0, 0.05, "")
    reg_slice_ok = eval_mod.RegressionBySliceResult(True, [])

    bad_inj_cases = [
        eval_mod.CaseEvalResult(
            "inj1", "injection", "q", "",
            eval_mod.RuleBasedScore(False), eval_mod.LlmJudgeResult(True), False
        )
    ]
    assert eval_mod.eval_gates_passed(report_ok, bad_inj_cases, reg_ok, reg_slice_ok) is False


# ==============================================================================
# 4. Token Tracking & Detailed Report Generation Tests
# ==============================================================================

def test_token_tracker_cost_calculation():
    """Kiểm tra tính toán token và quy đổi chi phí USD / VNĐ."""
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


def test_pipeline_trace_extraction():
    """Kiểm tra bóc tách chuỗi thực thi của các agent nodes."""
    steps = [
        {"tool": "rewrite"},
        {"tool": "supervisor"},
        {"tool": "price_agent"},
        {"tool": "composer"},
    ]
    trace = extract_pipeline_trace(steps)
    assert trace == "rewrite ➔ supervisor ➔ price_agent ➔ composer"

    # Fallback cho trường hợp rỗng
    assert extract_pipeline_trace([]) == "direct"


def test_generate_markdown_report_formatting():
    """Kiểm tra cấu trúc và nội dung báo cáo Markdown chi tiết."""
    from backend.eval.run import EvalReport, SliceScore

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
        dataset_name="golden_v5.yaml",
        detailed_results=mock_detailed,
        report=mock_report,
        total_tokens=150,
        total_app_tokens=150,
        total_judge_tokens=0,
        total_cost_usd=0.0001,
        total_cost_vnd=2.54,
        total_duration=0.5,
    )

    assert "# Báo Cáo Đánh Giá Chất Lượng Agent: golden_v5.yaml" in md
    assert "lookup_01" in md
    assert "price_agent ➔ composer" in md
    assert "PASS" in md
