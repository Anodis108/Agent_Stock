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


# ==============================================================================
# 8. Prompt Lint — Phase 3 (M3-B1)
# ==============================================================================


def test_prompt_lint_passes_on_resources_prompts():
    """Mọi prompt trong resources/prompts/ phải pass lint (metadata + biến template)."""
    from backend.infra.llm.prompt_lint import lint_prompts_dir
    from backend.infra.llm.prompt_registry import resolve_prompts_dir

    issues = lint_prompts_dir(resolve_prompts_dir())
    assert not issues, "\n".join(str(i) for i in issues)


def test_prompt_lint_catches_missing_metadata(tmp_path: Path):
    """Lint báo lỗi khi thiếu metadata bắt buộc."""
    from backend.infra.llm.prompt_lint import lint_prompt_file

    prompt_dir = tmp_path / "demo_prompt"
    prompt_dir.mkdir()
    bad = prompt_dir / "v1.yaml"
    bad.write_text(
        "name: demo_prompt\nversion: 1\ntemplate: 'Hello $user'\n",
        encoding="utf-8",
    )
    issues = lint_prompt_file(bad, prompt_name="demo_prompt")
    messages = " ".join(i.message for i in issues)
    assert "model" in messages
    assert "owner" in messages
    assert "changelog" in messages


def test_prompt_lint_catches_variables_mismatch(tmp_path: Path):
    """Lint báo lỗi khi variables khai báo không khớp template."""
    from backend.infra.llm.prompt_lint import lint_prompt_file

    prompt_dir = tmp_path / "demo_prompt"
    prompt_dir.mkdir()
    bad = prompt_dir / "v1.yaml"
    bad.write_text(
        """
name: demo_prompt
version: 1
model: gpt-4o-mini
owner: test
created: 2026-01-01
changelog: test
variables:
  - user
  - extra
template: |
  Hello $user
""".strip(),
        encoding="utf-8",
    )
    issues = lint_prompt_file(bad, prompt_name="demo_prompt")
    assert any("variables khai báo" in i.message for i in issues)


# ==============================================================================
# 9. Golden PR Subset — Phase 4 (M3-B2)
# ==============================================================================

GOLDEN_PR_SUBSET = ROOT / "resources" / "eval" / "golden_pr_subset.yaml"


def test_golden_pr_subset_loads_20_cases():
    """PR subset phải có ~20 cases resolve từ golden_v5."""
    from backend.eval.run import load_golden_dataset

    assert GOLDEN_PR_SUBSET.is_file(), "Thiếu golden_pr_subset.yaml"
    data = load_golden_dataset(GOLDEN_PR_SUBSET, validate_rules=True)
    cases = data["cases"]
    assert len(cases) == 20, f"PR subset cần 20 cases, có {len(cases)}"
    ids = {c["id"] for c in cases}
    assert len(ids) == 20, "case_id trùng lặp trong subset"
    for c in cases:
        assert c.get("expected"), f"{c['id']} thiếu expected"
        assert (c.get("slice") or {}).get("type"), f"{c['id']} thiếu slice"


def test_golden_pr_subset_priority_slices():
    """Subset ưu tiên injection, out_of_scope, comparison, session_memory."""
    from backend.eval.run import load_golden_dataset

    data = load_golden_dataset(GOLDEN_PR_SUBSET)
    by_slice: dict[str, int] = {}
    for c in data["cases"]:
        st = (c.get("slice") or {}).get("type", "unknown")
        by_slice[st] = by_slice.get(st, 0) + 1
    assert by_slice.get("injection") == 3
    assert by_slice.get("out_of_scope") == 4
    assert by_slice.get("comparison", 0) >= 4
    assert by_slice.get("session_memory") == 3


def test_golden_pr_subset_runner_stub():
    """Runner chạy subset với answer_fn stub — không cần API."""
    from backend.eval.run import build_report, load_golden_dataset, run_eval

    cases = load_golden_dataset(GOLDEN_PR_SUBSET)["cases"]

    def stub_answer(q: str) -> str:
        if "mua" in q.lower() or "bán" in q.lower() or "ignore" in q.lower():
            return "Không thể tư vấn mua/bán. Thông tin tham khảo."
        if "thời tiết" in q.lower() or "AAPL" in q or "TSLA" in q:
            return "Ngoài phạm vi theo dõi danh mục chứng khoán VN."
        return "FPT VNM HPG thông tin giá tham khảo."

    results = run_eval(
        cases,
        answer_fn=stub_answer,
        skip_judge=True,
        skip_agent_eval=True,
    )
    report = build_report(results)
    assert report.total == 20
    assert report.rate >= 0.5


# ==============================================================================
# 10. Eval Gate — Phase 5 (M3-B2)
# ==============================================================================


def _gate_report(
    *,
    rate: float = 0.90,
    rule_pass_rate: float = 0.96,
    injection_rate: float = 1.0,
    out_of_scope_rate: float = 1.0,
) -> dict:
    return {
        "total": 20,
        "passed": int(rate * 20),
        "rate": rate,
        "rule_pass_rate": rule_pass_rate,
        "by_slice": {
            "injection": {
                "total": 3,
                "passed": int(injection_rate * 3),
                "rate": injection_rate,
            },
            "out_of_scope": {
                "total": 4,
                "passed": int(out_of_scope_rate * 4),
                "rate": out_of_scope_rate,
            },
        },
        "failures": [],
    }


def test_eval_report_to_gate_json_includes_rule_pass_rate():
    """JSON export cho gate phải có rule_pass_rate và by_slice."""
    from backend.eval.run import eval_report_to_gate_json

    results = [
        eval_mod.CaseEvalResult(
            "lookup_01", "lookup", "q", "out",
            eval_mod.RuleBasedScore(passed=True),
            eval_mod.LlmJudgeResult(skipped=True),
            passed=True,
        ),
        eval_mod.CaseEvalResult(
            "lookup_02", "lookup", "q", "bad",
            eval_mod.RuleBasedScore(passed=False),
            eval_mod.LlmJudgeResult(skipped=True),
            passed=False,
        ),
    ]
    report = eval_mod.build_report(results)
    payload = eval_report_to_gate_json(report, results)
    assert payload["rule_pass_rate"] == 0.5
    assert payload["rule_passed"] == 1
    assert "by_slice" in payload
    assert payload["failures"][0]["output"] == "bad"


def test_gate_passes_good_report():
    """Gate pass khi overall, rule, injection, out_of_scope đạt ngưỡng."""
    from backend.eval.gate import check_gates

    result = check_gates(_gate_report())
    assert result.passed is True
    assert all(c.passed for c in result.checks)


def test_gate_fails_injection_slice():
    """Gate exit fail khi slice injection tụt (product-spec #9)."""
    from backend.eval.gate import check_gates

    result = check_gates(_gate_report(injection_rate=0.6667))
    assert result.passed is False
    inj = next(c for c in result.checks if c.name == "slice:injection")
    assert inj.passed is False


def test_gate_fails_overall_and_rule_rate():
    """Gate fail khi overall hoặc rule_pass_rate dưới ngưỡng."""
    from backend.eval.gate import check_gates

    low_overall = check_gates(_gate_report(rate=0.80))
    assert low_overall.passed is False

    low_rule = check_gates(_gate_report(rule_pass_rate=0.90))
    assert low_rule.passed is False


def test_gate_cli_exit_code(tmp_path: Path):
    """CLI gate trả exit 0/1 đúng."""
    from backend.eval.gate import main

    good = tmp_path / "good.json"
    good.write_text(json.dumps(_gate_report()), encoding="utf-8")
    assert main(["--run", str(good)]) == 0

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_gate_report(injection_rate=0.0)), encoding="utf-8")
    assert main(["--run", str(bad)]) == 1


# ==============================================================================
# 11. Eval History + Gate Drill — Phase 6 (M3-B2)
# ==============================================================================


def test_save_eval_history_writes_timestamped_file(tmp_path: Path):
    """History lưu vào <timestamp>_<sha>.json."""
    from backend.eval.history import load_history_reports, save_eval_history

    payload = _gate_report()
    path = save_eval_history(
        payload,
        history_dir=tmp_path,
        sha="abc1234",
    )
    assert path.is_file()
    assert path.name.endswith("_abc1234.json")
    records = load_history_reports(tmp_path)
    assert len(records) == 1
    assert records[0]["report"]["rate"] == payload["rate"]


def test_compute_noise_stats_three_runs():
    """3 runs cùng commit → tính σ và gợi ý tolerance."""
    from backend.eval.history import compute_noise_stats

    stats = compute_noise_stats([0.90, 0.92, 0.91])
    assert stats["count"] == 3
    assert stats["stdev"] is not None
    assert stats["stdev"] >= 0.0
    assert stats["recommended_drop_tolerance"] >= 0.03


def test_gate_drill_bad_then_good(tmp_path: Path):
    """Drill: injection tụt → exit 1; revert → exit 0."""
    from backend.eval.gate import check_gates, main as gate_main

    bad = {
        "rate": 0.85,
        "rule_pass_rate": 0.90,
        "by_slice": {
            "injection": {"total": 3, "passed": 0, "rate": 0.0},
            "out_of_scope": {"total": 4, "passed": 4, "rate": 1.0},
        },
    }
    good = _gate_report()
    assert check_gates(bad).passed is False
    assert check_gates(good).passed is True

    bad_path = tmp_path / "bad.json"
    good_path = tmp_path / "good.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    good_path.write_text(json.dumps(good), encoding="utf-8")
    assert gate_main(["--run", str(bad_path)]) == 1
    assert gate_main(["--run", str(good_path)]) == 0


def test_gate_accepts_v5_baseline_format():
    """Legacy v5_baseline.json (thiếu rule_pass_rate) vẫn chạy gate."""
    from backend.eval.gate import load_gate_report, check_gates

    baseline_path = ROOT / "specs" / "eval" / "v5_baseline.json"
    if not baseline_path.is_file():
        pytest.skip("v5_baseline.json not found")
    report = load_gate_report(baseline_path)
    result = check_gates(report)
    assert result.checks
    inj = next(c for c in result.checks if c.name == "slice:injection")
    assert inj.passed is True


# ==============================================================================
# 12. Cost Baseline — Phase 7 (M3-B3)
# ==============================================================================

REPLAY_FAQ = ROOT / "resources" / "eval" / "replay_faq.yaml"


def test_cost_tracker_record_and_summary():
    """record_cost ghi tag feature/model/prompt_version/cache_hit."""
    from backend.infra.cost.tracker import get_cost_tracker, record_cost, reset_cost_tracker

    reset_cost_tracker()
    record_cost(
        feature="chat",
        model="gpt-4o-mini",
        prompt_version="production",
        cache_hit=False,
        prompt_tokens=1000,
        completion_tokens=200,
    )
    summary = get_cost_tracker().summary()
    assert summary["requests"] == 1
    assert summary["total_tokens"] == 1200
    assert summary["cache_hits"] == 0
    assert summary["total_cost_usd"] > 0


def test_replay_faq_has_50_questions_and_duplicates():
    """replay_faq.yaml: 50 câu, ~30% near-duplicate."""
    import yaml

    assert REPLAY_FAQ.is_file()
    data = yaml.safe_load(REPLAY_FAQ.read_text(encoding="utf-8"))
    questions = data["questions"]
    assert len(questions) == 50
    dups = sum(1 for q in questions if q.get("near_duplicate_of"))
    assert dups >= 14


def test_cost_baseline_dry_run(tmp_path: Path):
    """cost_baseline.py --dry-run tạo report markdown + JSON."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from cost_baseline import run_baseline  # type: ignore

    md = tmp_path / "cost_baseline.md"
    js = tmp_path / "cost_baseline.json"
    payload = run_baseline(limit=10, dry_run=True, output_md=md, output_json=js)
    assert md.is_file()
    assert js.is_file()
    assert payload["summary"]["requests"] == 10
    assert "Total tokens" in md.read_text(encoding="utf-8")
