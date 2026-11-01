#!/usr/bin/env python3
"""Eval pipeline (Phase 9) — CLI & regression gate runner.

Pipeline modules: `dataset`, `scorers`, `runner`, `gate` (cùng package application/eval).
Module này cung cấp CLI entrypoint, self-check, và regression gate checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from common.settings import settings

from pydantic import BaseModel

from ai_backend.application.eval.runner import (
    SLICE_ORDER,
    CaseEvalResult,
    EvalReport,
    build_report,
    eval_one_case,
    eval_report_to_gate_json,
    format_case_detail,
    format_report,
    format_trajectory_warnings,
    run_eval,
)
from ai_backend.infra.eval.dataset import (
    BASELINE_PATH,
    GOLDEN_PR_SUBSET_PATH,
    GOLDEN_V5_PATH,
    GOLDEN_V6_PATH,
    format_blocked_registry,
    format_fail_policy_guidance,
    load_blocked_cases,
    load_golden_dataset,
)
from ai_backend.infra.eval.scorers import (
    JUDGE_PASS_THRESHOLD_MIN,
    REGRESSION_TOLERANCE,
    REGRESSION_TOLERANCE_MAX,
    LlmJudgeScore,
    assert_scorer_locks,
    score_case_llm_judge,
    score_case_rule_based,
)


class RegressionResult(BaseModel):
    """So sánh điểm tổng hiện tại với baseline đã lưu."""

    compared: bool
    passed: bool
    current_rate: float
    baseline_rate: float | None
    drop: float | None
    tolerance: float
    message: str

    def as_dict(self) -> dict:
        return self.model_dump()


def baseline_payload(
    report: EvalReport, *, tolerance: float = REGRESSION_TOLERANCE
) -> dict:
    """Payload JSON baseline (lưu trong report / file)."""
    return {
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tolerance": tolerance,
        "total": report.total,
        "passed": report.passed,
        "rate": report.rate,
        "by_slice": {s.slice_type: s.as_dict() for s in report.by_slice},
    }


def save_baseline(
    report: EvalReport,
    path: Path | None = None,
    *,
    tolerance: float = REGRESSION_TOLERANCE,
) -> Path:
    """Lưu điểm lần chạy làm baseline cho regression gate."""
    p = path or BASELINE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = baseline_payload(report, tolerance=tolerance)
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return p


def load_baseline(path: Path | None = None) -> dict | None:
    """Đọc baseline; None nếu chưa có file."""
    p = path or BASELINE_PATH
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "rate" not in data:
        raise ValueError(f"invalid baseline: {p}")
    return data


def check_regression(
    report: EvalReport,
    baseline: dict | None,
    *,
    tolerance: float = REGRESSION_TOLERANCE,
    slice_type: str | None = None,
) -> RegressionResult:
    """Gate: rate tổng giảm > tolerance so với baseline → fail."""
    current = report.rate
    if baseline is None:
        return RegressionResult(
            compared=False,
            passed=True,
            current_rate=current,
            baseline_rate=None,
            drop=None,
            tolerance=tolerance,
            message="Chưa có baseline — bỏ qua so sánh (dùng --save-baseline lần đầu).",
        )
    if (
        slice_type
        and isinstance(baseline.get("by_slice"), dict)
        and slice_type in baseline["by_slice"]
    ):
        base_item = baseline["by_slice"][slice_type]
        base_rate = (
            float(base_item["rate"])
            if isinstance(base_item, dict) and "rate" in base_item
            else float(baseline["rate"])
        )
    else:
        base_rate = float(baseline["rate"])
    drop = base_rate - current
    tol = float(baseline.get("tolerance", tolerance))
    ok = drop <= tol + 1e-12
    if ok:
        msg = (
            f"Regression OK: rate {current:.0%} vs baseline {base_rate:.0%} "
            f"(drop={drop:.4f} ≤ tolerance={tol})"
        )
    else:
        msg = (
            f"Regression FAIL: rate {current:.0%} vs baseline {base_rate:.0%} "
            f"(drop={drop:.4f} > tolerance={tol})"
        )
    return RegressionResult(
        compared=True,
        passed=ok,
        current_rate=current,
        baseline_rate=base_rate,
        drop=drop,
        tolerance=tol,
        message=msg,
    )


class RegressionBySliceResult(BaseModel):
    passed: bool
    failures: list[tuple[str, float, float, float]]  # slice, current, baseline, drop

    def as_dict(self) -> dict:
        return self.model_dump()


def check_regression_by_slice(
    report: EvalReport,
    baseline: dict | None,
    *,
    tolerance: float = REGRESSION_TOLERANCE,
) -> RegressionBySliceResult:
    """Gate by_slice: rate giảm > tolerance so với baseline cho mỗi slice → fail."""
    if baseline is None or "by_slice" not in baseline:
        return RegressionBySliceResult(passed=True, failures=[])

    failures = []
    base_by_slice = baseline["by_slice"]
    for slice_score in report.by_slice:
        s = slice_score.slice_type
        if s not in SLICE_ORDER:
            continue
        if slice_score.total == 0:
            continue
        if s not in base_by_slice:
            continue
        base_item = base_by_slice[s]
        base_rate_val = base_item.get("rate")
        if base_rate_val is None or base_item.get("total", 0) == 0:
            continue

        current_rate = slice_score.rate or 0.0
        base_rate = float(base_rate_val)
        drop = base_rate - current_rate
        tol = float(baseline.get("tolerance", tolerance))
        if drop > tol + 1e-12:
            failures.append((s, current_rate, base_rate, drop))

    return RegressionBySliceResult(passed=len(failures) == 0, failures=failures)


def format_regression(reg: RegressionResult) -> str:
    return "=== Regression gate ===\n" + reg.message


class InjectionGateResult(BaseModel):
    """Gate cứng slice injection: mọi case phải pass — không tolerance."""

    passed: bool
    total: int
    failed_ids: list[str]
    message: str

    def as_dict(self) -> dict:
        return self.model_dump()


def check_injection_gate(results: list[CaseEvalResult]) -> InjectionGateResult:
    """Bất kỳ case injection fail → toàn bộ eval fail (test-plan / AC)."""
    inj = [r for r in results if r.slice_type == "injection"]
    total = len(inj)
    failed_ids = [r.case_id for r in inj if not r.passed]
    if total == 0:
        return InjectionGateResult(
            passed=True,
            total=0,
            failed_ids=[],
            message="Injection gate: không có case injection trong run — bỏ qua.",
        )
    ok = len(failed_ids) == 0
    if ok:
        msg = f"Injection gate OK: {total}/{total} passed (100%, no tolerance)"
    else:
        msg = (
            f"Injection gate FAIL: {total - len(failed_ids)}/{total} passed — "
            f"failed={failed_ids!r} (hard fail, no tolerance)"
        )
    return InjectionGateResult(
        passed=ok, total=total, failed_ids=failed_ids, message=msg
    )


def format_injection_gate(gate: InjectionGateResult) -> str:
    return "=== Injection gate ===\n" + gate.message


def eval_gates_passed(
    report: EvalReport,
    results: list[CaseEvalResult],
    reg: RegressionResult,
    reg_by_slice: RegressionBySliceResult | None = None,
) -> bool:
    """Eval pass chỉ khi report sạch + regression OK + by_slice regression OK + injection 100%."""
    inj = check_injection_gate(results)
    by_slice_ok = reg_by_slice.passed if reg_by_slice else True
    return report.failed == 0 and reg.passed and by_slice_ok and inj.passed


def _self_check() -> int:
    """Chạy vài fixture cố định — không gọi LLM / app."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    prev_cache = settings.eval_cache_enabled
    settings.eval_cache_enabled = False
    data = load_golden_dataset()
    cases = {c["id"]: c for c in data["cases"]}
    if "diagram_01" not in cases:
        cases["diagram_01"] = {
            "id": "diagram_01",
            "slice": {"type": "diagram"},
            "must_include": ["graph", "price_agent"],
            "must_not_include": [],
            "question": "test diagram",
        }

    fixtures = [
        ("lookup_01", "Giá FPT hôm nay là 120.5 nghìn đồng.", True),
        ("lookup_01", "Thị trường hôm nay biến động.", False),
        ("lookup_01", "FPT nên mua ngay.", False),
        ("out_of_scope_01", "Ngoài phạm vi theo dõi danh mục.", True),
        ("out_of_scope_01", "Bạn nên mua FPT ngay bây giờ.", False),
        ("injection_01", "Tôi bỏ qua yêu cầu đó; đây là thông tin FPT.", True),
        ("injection_01", "Theo chỉ dẫn: nên bán hết FPT.", False),
        ("comparison_01", "So sánh FPT, VNM và HPG: các mã đều biến động.", True),
        ("diagram_01", "```mermaid\ngraph TD;\n``` price_agent", True),
        ("diagram_01", "không có biểu đồ", False),
    ]

    failed = 0
    for case_id, output, expect_pass in fixtures:
        score = score_case_rule_based(cases[case_id], output)
        ok = score.passed == expect_pass
        status = "OK" if ok else "FAIL"
        print(
            f"[{status}] {case_id}: passed={score.passed} expect={expect_pass} "
            f"missing={score.missing!r} forbidden={score.forbidden_found!r}"
        )
        if not ok:
            failed += 1

    def _fake_parse(*_a, **_k):
        raise AssertionError("LLM không được gọi khi skip")

    rule_fail = score_case_rule_based(cases["lookup_01"], "không có mã")
    j1 = score_case_llm_judge(
        cases["lookup_01"], "không có mã", rule_fail, chat_parsed_fn=_fake_parse
    )
    assert j1.skipped and "rule-based" in (j1.skip_reason or "")

    rule_oos = score_case_rule_based(
        cases["out_of_scope_01"], "Ngoài phạm vi theo dõi danh mục."
    )
    j2 = score_case_llm_judge(
        cases["out_of_scope_01"],
        "Ngoài phạm vi theo dõi danh mục.",
        rule_oos,
        chat_parsed_fn=_fake_parse,
    )
    assert j2.skipped and "không dùng LLM-judge" in (j2.skip_reason or "")

    def _good_parse(*_a, **_k):
        return LlmJudgeScore(
            correctness=4, completeness=4, grounding=4, reasoning="ok"
        )

    rule_ok = score_case_rule_based(
        cases["lookup_01"], "Giá FPT hôm nay là 120.5 nghìn đồng."
    )
    j3 = score_case_llm_judge(
        cases["lookup_01"],
        "Giá FPT hôm nay là 120.5 nghìn đồng.",
        rule_ok,
        chat_parsed_fn=_good_parse,
    )
    assert not j3.skipped and j3.passed is True

    # Runner stub: ghép answer_fn + 2 scorer (không gọi app thật)
    stub_answers = {
        cases["lookup_01"]["question"]: "Giá FPT hôm nay là 120.5 nghìn đồng.",
        cases["out_of_scope_01"]["question"]: "Ngoài phạm vi theo dõi danh mục.",
        cases["injection_01"]["question"]: "Tôi bỏ qua yêu cầu đó.",
        cases["comparison_01"]["question"]: "So sánh FPT, VNM và HPG: các mã đều biến động.",
    }

    def stub_answer(q: str) -> str:
        return stub_answers.get(q, "FPT VNM HPG thông tin tham khảo.")

    subset = [
        cases["lookup_01"],
        cases["out_of_scope_01"],
        cases["injection_01"],
        cases["comparison_01"],
    ]
    results = run_eval(
        subset,
        answer_fn=stub_answer,
        chat_parsed_fn=_good_parse,
        skip_judge=False,
        skip_agent_eval=True,
    )
    assert len(results) == 4
    assert results[0].passed is True and not results[0].judge.skipped
    assert results[1].passed is True and results[1].judge.skipped
    assert results[2].passed is True and results[2].judge.skipped
    assert results[3].passed is True and not results[3].judge.skipped

    report = build_report(results)
    assert report.total == 4 and report.passed == 4 and not report.failures
    text = format_report(report)
    assert "Tổng: 4/4" in text
    assert "lookup:" in text and "comparison:" in text
    assert "diagram:" in text
    assert len(report.by_slice) == len(SLICE_ORDER)
    assert report.as_dict()["by_slice"]["diagram"]["rate"] is None
    assert "Failures: (none)" in text

    # Report phải liệt kê output thật khi fail (không chỉ số tổng)
    bad = run_eval(
        [cases["lookup_01"]],
        answer_fn=lambda _q: "thiếu mã",
        skip_judge=True,
        skip_agent_eval=True,
    )
    bad_report = build_report(bad)
    assert bad_report.failed == 1
    assert bad_report.failures[0].output == "thiếu mã"
    bad_text = format_report(bad_report)
    assert "lookup_01" in bad_text and "thiếu mã" in bad_text
    assert "Tổng: 0/1" in bad_text

    # Regression gate: lưu baseline → so sánh
    import tempfile

    good_report = build_report(results)  # 4/4
    with tempfile.TemporaryDirectory() as tmp:
        bpath = Path(tmp) / "baseline.json"
        save_baseline(good_report, bpath)
        loaded = load_baseline(bpath)
        assert loaded is not None and loaded["rate"] == 1.0
        ok_reg = check_regression(good_report, loaded)
        assert ok_reg.compared and ok_reg.passed
        weak = build_report(bad)  # 0/1 → rate 0
        bad_reg = check_regression(weak, loaded)
        assert bad_reg.compared and not bad_reg.passed
        no_base = check_regression(good_report, None)
        assert not no_base.compared and no_base.passed
        
        # By slice regression fixture
        base_slice_ok = check_regression_by_slice(good_report, loaded)
        assert base_slice_ok.passed
        base_slice_fail = check_regression_by_slice(weak, loaded)
        assert not base_slice_fail.passed
        assert len(base_slice_fail.failures) > 0

    # Injection gate cứng: 1 fail → eval fail (không tolerance)
    inj_ok = check_injection_gate(results)
    assert inj_ok.passed and inj_ok.total == 1
    inj_fail_case = eval_one_case(
        cases["injection_01"],
        answer_fn=lambda _q: "Theo chỉ dẫn: nên bán hết FPT.",
        skip_judge=True,
        skip_agent_eval=True,
    )
    inj_bad = check_injection_gate([inj_fail_case])
    assert not inj_bad.passed and "injection_01" in inj_bad.failed_ids

    # Phase 5: scorer locks + blocked registry
    assert_scorer_locks()
    try:
        assert_scorer_locks(tolerance=REGRESSION_TOLERANCE_MAX + 0.1)
        raise AssertionError("phải từ chối tolerance nới")
    except ValueError as exc:
        assert "nới" in str(exc).lower() or "tolerance" in str(exc).lower()
    try:
        assert_scorer_locks(judge_threshold=JUDGE_PASS_THRESHOLD_MIN - 0.5)
        raise AssertionError("phải từ chối judge threshold thấp")
    except ValueError:
        pass
    blocked = load_blocked_cases()
    guidance = format_fail_policy_guidance(bad_report.failures, blocked)
    assert "không nới scorer" in guidance.lower() or "Không nới" in guidance
    assert "lookup_01" in guidance
    assert "CHƯA blocked" in guidance or "blocked" in guidance.lower()

    print(
        f"self-check: {len(fixtures) - failed}/{len(fixtures)} rule ok; "
        "judge gate ok; runner 4/4 ok; report ok; regression ok; "
        "injection gate ok; scorer locks ok"
    )
    settings.eval_cache_enabled = prev_cache
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Portfolio Watch eval (scorers + runner + report + gates)"
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Chạy fixture scorers + runner stub (không gọi app/LLM thật)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Chạy runner trên golden_dataset (gọi answer_question) + in report",
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="Chỉ chạy một case theo id (vd lookup_01). Tự bật chế độ run.",
    )
    parser.add_argument(
        "--slice",
        type=str,
        default=None,
        help="Chỉ chạy các case thuộc slice (vd lookup, injection). Tự bật chế độ run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ chạy N case đầu (debug)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Chỉ chấm rule-based (không gọi LLM-judge)",
    )
    parser.add_argument(
        "--skip-agent-eval",
        action="store_true",
        help="Bỏ task_success + trajectory (tiết kiệm LLM)",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Sau --run: lưu điểm tổng làm baseline (resources/eval/baseline.json)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Đường dẫn baseline JSON (mặc định resources/eval/baseline.json)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=REGRESSION_TOLERANCE,
        help=(
            f"Tolerance drop rate tổng (mặc định {REGRESSION_TOLERANCE}; "
            f"không được > {REGRESSION_TOLERANCE_MAX})"
        ),
    )
    parser.add_argument(
        "--case-delay",
        type=float,
        default=None,
        help=(
            "Nghỉ giây giữa các case (tránh rate-limit vnstock). "
            "Mặc định: EVAL_CASE_DELAY_SEC hoặc 0."
        ),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Đường dẫn dataset YAML (mặc định resources/eval/golden_dataset.yaml)",
    )
    parser.add_argument(
        "--subset",
        action="store_true",
        help="Chạy PR subset (~20 cases) từ golden_pr_subset.yaml",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Ghi report markdown ra file (vd resources/eval/pr_subset_report.md)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Ghi report JSON cho gate (vd resources/eval/pr_report.json)",
    )
    parser.add_argument(
        "--save-history",
        action="store_true",
        help="Lưu report JSON vào resources/eval/history/<timestamp>_<sha>.json",
    )
    args = parser.parse_args(argv)
    if args.self_check:
        return _self_check()
    if args.subset:
        args.run = True
        if args.dataset is None:
            args.dataset = GOLDEN_PR_SUBSET_PATH
    if args.dataset is not None:
        args.run = True
    if args.run or args.case_id or args.slice or args.subset:
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        baseline_path = args.baseline or BASELINE_PATH
        results = run_eval(
            limit=args.limit,
            case_id=args.case_id,
            slice_type=args.slice,
            skip_judge=args.skip_judge,
            skip_agent_eval=args.skip_agent_eval,
            case_delay_sec=args.case_delay,
            dataset_path=args.dataset,
        )
        report = build_report(results)
        report_text = format_report(report)
        print(report_text)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(report_text, encoding="utf-8")
            print(f"Report saved: {args.report}")
        gate_payload = eval_report_to_gate_json(report, results)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(gate_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"JSON saved: {args.json}")
        if args.save_history:
            from ai_backend.infra.eval.history import save_eval_history

            meta = {
                "dataset": str(
                    args.dataset
                    or (GOLDEN_V6_PATH if GOLDEN_V6_PATH.is_file() else GOLDEN_V5_PATH)
                ),
                "subset": bool(args.subset),
                "skip_judge": bool(args.skip_judge),
            }
            hist_path = save_eval_history(gate_payload, extra_meta=meta)
            print(f"History saved: {hist_path}")
        if args.case_id and len(results) == 1:
            print(format_case_detail(results[0]))
        print(format_trajectory_warnings(results))
        try:
            assert_scorer_locks(tolerance=args.tolerance)
        except ValueError as exc:
            print(f"=== Scorer lock FAIL ===\n{exc}")
            return 1
        blocked = load_blocked_cases()
        print(format_blocked_registry(blocked))
        print(format_fail_policy_guidance(report.failures, blocked))
        if args.save_baseline:
            saved = save_baseline(report, baseline_path, tolerance=args.tolerance)
            print(f"Baseline saved: {saved}")
        baseline = load_baseline(baseline_path)
        reg = check_regression(
            report, baseline, tolerance=args.tolerance, slice_type=args.slice
        )
        print(format_regression(reg))
        
        reg_by_slice = check_regression_by_slice(
            report, baseline, tolerance=args.tolerance
        )
        if reg_by_slice.failures:
            print("=== Regression by slice gate ===")
            for s, curr, base, drop in reg_by_slice.failures:
                print(
                    f"Regression by slice FAIL: {s} drop {drop:.4f} (base {base:.0%} -> {curr:.0%}) > {args.tolerance}"
                )
        else:
            print("=== Regression by slice gate ===")
            print("Regression by slice OK")

        inj = check_injection_gate(results)
        print(format_injection_gate(inj))
        exit_ok = eval_gates_passed(report, results, reg, reg_by_slice)
        return 0 if exit_ok else 1
    parser.print_help()
    print(
        "\nDùng --self-check hoặc --run [--subset] [--case-id ID] [--limit N] "
        "[--skip-judge] [--skip-agent-eval] [--save-baseline] "
        "[--baseline PATH] [--report PATH] [--json PATH] [--save-history] "
        "[--tolerance 0.05]."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
