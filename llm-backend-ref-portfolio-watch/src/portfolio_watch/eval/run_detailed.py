#!/usr/bin/env python3
"""Detailed evaluation runner for golden_v3.yaml with token and cost tracking.

Captures for each case:
- Case ID & Slice
- Question
- Answer / Output
- Pass / Fail (Rule-based, LLM Judge, Task Success, Trajectory)
- Pipeline Trace Agent (sequence of agents/nodes executed)
- Token counts (Prompt tokens, Completion tokens, Total tokens)
- Cost (USD and VND based on model pricing)
- Latency (seconds)

Outputs results to:
- specs/eval/eval_results_golden_v3.md (Markdown table & summary)
- specs/eval/eval_results_golden_v3.json (Full machine-readable JSON)
"""

from __future__ import annotations

import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import yaml
from openai.types.chat import ChatCompletion

from src.portfolio_watch.eval.run import (
    BASELINE_PATH,
    GOLDEN_V3_PATH,
    CaseEvalResult,
    build_report,
    check_injection_gate,
    check_regression,
    check_regression_by_slice,
    eval_one_case,
    format_report,
    load_baseline,
    load_golden_dataset,
    make_answer_fn,
    save_baseline,
)
from src.portfolio_watch.infra.llm import completion as completion_mod
from src.portfolio_watch.infra.llm.params import GenerationParams
from src.portfolio_watch.shared.settings import settings

# Pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "default": {"prompt": 0.15, "completion": 0.60},
}
VND_PER_USD = 25400


@dataclass
class TokenRecord:
    stage: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class TokenTracker:
    def __init__(self):
        self.active_stage: str = "app"
        self.records: list[TokenRecord] = []

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int):
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1_000_000.0
        self.records.append(
            TokenRecord(
                stage=self.active_stage,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
            )
        )

    def reset(self):
        self.records.clear()
        self.active_stage = "app"

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self.records)

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_cost_vnd(self) -> float:
        return self.total_cost_usd * VND_PER_USD


# Global tracker instance
_tracker = TokenTracker()

# Hook completion functions to track tokens
_original_chat = completion_mod.chat
_original_chat_parsed = completion_mod.chat_parsed
_original_chat_with_tools = completion_mod.chat_with_tools


def _hooked_chat(messages, params=None):
    from src.portfolio_watch.infra.llm.client import get_client, mark_current_key_limited
    from src.portfolio_watch.infra.llm.resilience import retry_with_backoff

    params = params or GenerationParams()
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            **params.to_openai_kwargs(),
        )

    response = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    if hasattr(response, "usage") and response.usage:
        _tracker.record_usage(
            settings.llm_model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
        )
    return response.choices[0].message.content or ""


def _hooked_chat_parsed(messages, schema, params=None):
    from src.portfolio_watch.infra.llm.client import get_client, mark_current_key_limited
    from src.portfolio_watch.infra.llm.resilience import retry_with_backoff

    params = params or GenerationParams()
    client = get_client()

    def _call():
        return client.chat.completions.parse(
            model=settings.llm_model,
            messages=messages,
            response_format=schema,
            **params.to_openai_kwargs(),
        )

    completion = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    if hasattr(completion, "usage") and completion.usage:
        _tracker.record_usage(
            settings.llm_model,
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
            completion.usage.total_tokens,
        )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Model không trả về output khớp schema.")
    return parsed


def _hooked_chat_with_tools(messages, tools, params=None):
    from src.portfolio_watch.infra.llm.client import get_client, mark_current_key_limited
    from src.portfolio_watch.infra.llm.resilience import retry_with_backoff

    params = params or GenerationParams()
    client = get_client()

    def _call() -> ChatCompletion:
        return client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            **params.to_openai_kwargs(),
        )

    completion = retry_with_backoff(
        _call,
        max_retries=settings.llm_max_retries,
        on_rate_limit=lambda: mark_current_key_limited(client),
    )
    if hasattr(completion, "usage") and completion.usage:
        _tracker.record_usage(
            settings.llm_model,
            completion.usage.prompt_tokens,
            completion.usage.completion_tokens,
            completion.usage.total_tokens,
        )
    return completion


# Install monkey patches
completion_mod.chat = _hooked_chat
completion_mod.chat_parsed = _hooked_chat_parsed
completion_mod.chat_with_tools = _hooked_chat_with_tools


def extract_pipeline_trace(steps: list[dict]) -> str:
    """Format the list of step tools into an intuitive pipeline trace."""
    if not steps:
        return "direct"
    names = []
    for s in steps:
        name = s.get("tool") or s.get("name") or "step"
        if name not in names:
            names.append(name)
    return " ➔ ".join(names) if names else "direct"


def run_detailed_evaluation(dataset_path: Path | None = None, case_delay_sec: float = 0.5):
    p = dataset_path or GOLDEN_V3_PATH
    print(f"\n========================================================")
    print(f"  BẮT ĐẦU ĐÁNH GIÁ DATASET: {p.name}")
    print(f"  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"========================================================\n")

    golden_data = load_golden_dataset(p)
    cases = golden_data.get("cases", [])
    total_cases = len(cases)
    print(f"Tổng số case cần chạy: {total_cases}\n")

    detailed_results: list[dict] = []
    eval_results: list[CaseEvalResult] = []

    start_all = time.perf_counter()

    for idx, case in enumerate(cases, 1):
        cid = case.get("id", f"case_{idx}")
        slice_type = (case.get("slice") or {}).get("type", "unknown")
        question = case.get("question", "")

        print(f"[{idx}/{total_cases}] Chạy case: {cid} (slice: {slice_type}) | Q: '{question[:50]}...'")

        # Reset token tracker for this case
        _tracker.reset()
        t0 = time.perf_counter()

        # Step 1: Run App answering
        _tracker.active_stage = "app"
        fn = make_answer_fn(user_id=f"eval-{cid}")

        # Step 2: Run Evaluation (app + scorers)
        # Note: eval_one_case calls answer_fn, then score_case_llm_judge, score_case_task_success, score_case_trajectory
        # We can switch active_stage inside if needed, or track combined
        def tracked_answer_fn(q: str) -> str:
            _tracker.active_stage = "app"
            out = fn(q)
            tracked_answer_fn.last_steps = getattr(fn, "last_steps", [])
            return out

        tracked_answer_fn.last_steps = []

        def tracked_chat_parsed(*args, **kwargs):
            _tracker.active_stage = "eval_judge"
            return _hooked_chat_parsed(*args, **kwargs)

        res = eval_one_case(
            case,
            answer_fn=tracked_answer_fn,
            chat_parsed_fn=tracked_chat_parsed,
            agent_eval_parsed_fn=tracked_chat_parsed,
            skip_judge=False,
            skip_agent_eval=False,
        )

        elapsed = time.perf_counter() - t0
        eval_results.append(res)

        # Pipeline trace
        trace_str = extract_pipeline_trace(res.steps)

        # App vs Judge tokens
        app_tokens = sum(r.total_tokens for r in _tracker.records if r.stage == "app")
        judge_tokens = sum(r.total_tokens for r in _tracker.records if r.stage == "eval_judge")

        status_str = "PASS" if res.passed else "FAIL"

        case_data = {
            "index": idx,
            "case_id": cid,
            "slice": slice_type,
            "question": question,
            "expected": case.get("expected", ""),
            "answer": res.output,
            "status": status_str,
            "passed": res.passed,
            "pipeline_trace": trace_str,
            "steps": res.steps,
            "latency_s": round(elapsed, 2),
            "tokens": {
                "prompt_tokens": _tracker.total_prompt_tokens,
                "completion_tokens": _tracker.total_completion_tokens,
                "total_tokens": _tracker.total_tokens,
                "app_tokens": app_tokens,
                "judge_tokens": judge_tokens,
            },
            "cost": {
                "usd": round(_tracker.total_cost_usd, 6),
                "vnd": round(_tracker.total_cost_vnd, 2),
            },
            "scoring": {
                "rule_based": {
                    "passed": res.rule.passed,
                    "missing": res.rule.missing,
                    "forbidden_found": res.rule.forbidden_found,
                },
                "llm_judge": res.judge.as_dict(),
                "task_success": res.task_success.as_dict() if res.task_success else None,
                "trajectory": res.trajectory.as_dict() if res.trajectory else None,
            },
            "error": res.error,
        }
        detailed_results.append(case_data)

        # Print concise case summary
        print(
            f"   ➔ Status: {status_str} | Trace: [{trace_str}] | "
            f"Tokens: {_tracker.total_tokens} (App: {app_tokens}, Judge: {judge_tokens}) | "
            f"Cost: ${_tracker.total_cost_usd:.5f} ({_tracker.total_cost_vnd:.0f} VND) | Time: {elapsed:.2f}s"
        )
        if not res.passed:
            print(f"      [FAIL REASON] Rule: {res.rule.passed} (Missing: {res.rule.missing}, Forbidden: {res.rule.forbidden_found})")
            if not res.judge.skipped:
                print(f"      [FAIL REASON] Judge: {res.judge.passed} (Score: {getattr(res.judge.score, 'overall', 'N/A')})")
            if res.task_success and not res.task_success.skipped and res.task_success.result:
                print(f"      [FAIL REASON] TaskSuccess: {res.task_success.result.success} - {res.task_success.result.reasoning}")

        if case_delay_sec > 0:
            time.sleep(case_delay_sec)

    total_duration = time.perf_counter() - start_all

    # Calculate Aggregates
    report = build_report(eval_results)
    total_tokens_all = sum(c["tokens"]["total_tokens"] for c in detailed_results)
    total_app_tokens = sum(c["tokens"]["app_tokens"] for c in detailed_results)
    total_judge_tokens = sum(c["tokens"]["judge_tokens"] for c in detailed_results)
    total_cost_usd_all = sum(c["cost"]["usd"] for c in detailed_results)
    total_cost_vnd_all = sum(c["cost"]["vnd"] for c in detailed_results)
    passed_count = sum(1 for c in detailed_results if c["passed"])
    failed_count = total_cases - passed_count
    pass_rate = (passed_count / total_cases) * 100.0 if total_cases > 0 else 0.0

    print(f"\n========================================================")
    print(f"  HOÀN THÀNH ĐÁNH GIÁ TOÀN BỘ DATASET ({total_cases} CASES)")
    print(f"  Kết quả: {passed_count}/{total_cases} Passed ({pass_rate:.1f}%)")
    print(f"  Tổng Tokens: {total_tokens_all:,} (App: {total_app_tokens:,}, Judge: {total_judge_tokens:,})")
    print(f"  Tổng Chi Phí: ${total_cost_usd_all:.4f} USD (~ {total_cost_vnd_all:,.0f} VND)")
    print(f"  Tổng Thời Gian: {total_duration:.1f}s (Trung bình: {total_duration/total_cases:.2f}s/case)")
    print(f"========================================================\n")

    # Generate Markdown Table Report
    md_content = generate_markdown_report(
        dataset_name=p.name,
        detailed_results=detailed_results,
        report=report,
        total_tokens=total_tokens_all,
        total_app_tokens=total_app_tokens,
        total_judge_tokens=total_judge_tokens,
        total_cost_usd=total_cost_usd_all,
        total_cost_vnd=total_cost_vnd_all,
        total_duration=total_duration,
    )

    # Save to specs/eval/eval_results_golden_v3.md
    md_path = ROOT / "specs" / "eval" / "eval_results_golden_v3.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"Đã lưu bảng kết quả Markdown tại: {md_path}")

    # Save to specs/eval/eval_results_golden_v3.json
    json_path = ROOT / "specs" / "eval" / "eval_results_golden_v3.json"
    json_payload = {
        "dataset": p.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_count,
            "failed_cases": failed_count,
            "pass_rate_pct": round(pass_rate, 2),
            "total_tokens": total_tokens_all,
            "total_app_tokens": total_app_tokens,
            "total_judge_tokens": total_judge_tokens,
            "total_cost_usd": round(total_cost_usd_all, 6),
            "total_cost_vnd": round(total_cost_vnd_all, 2),
            "total_duration_sec": round(total_duration, 2),
            "avg_latency_per_case_sec": round(total_duration / total_cases, 2) if total_cases > 0 else 0,
            "by_slice": {s.slice_type: s.as_dict() for s in report.by_slice},
        },
        "cases": detailed_results,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã lưu chi tiết JSON tại: {json_path}")

    return detailed_results, json_payload


def generate_markdown_report(
    dataset_name: str,
    detailed_results: list[dict],
    report: Any,
    total_tokens: int,
    total_app_tokens: int,
    total_judge_tokens: int,
    total_cost_usd: float,
    total_cost_vnd: float,
    total_duration: float,
) -> str:
    total_cases = len(detailed_results)
    passed_cases = sum(1 for c in detailed_results if c["passed"])
    pass_rate = (passed_cases / total_cases) * 100.0 if total_cases > 0 else 0.0

    lines = [
        f"# Báo Cáo Đánh Giá Chất Lượng Agent: {dataset_name}",
        f"",
        f"- **Thời gian chạy**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **Model chính**: `{settings.llm_model}` | **LLM Judge**: `gpt-4o-mini`",
        f"- **Tổng số ca kiểm thử**: **{total_cases}**",
        f"- **Kết quả**: **{passed_cases}/{total_cases} Passed ({pass_rate:.1f}%)**",
        f"- **Tổng Token tiêu thụ**: **{total_tokens:,} tokens** (Pipeline: {total_app_tokens:,}, Judge: {total_judge_tokens:,})",
        f"- **Tổng chi phí ước tính**: **${total_cost_usd:.4f} USD** (~ **{total_cost_vnd:,.0f} VNĐ**)",
        f"- **Tổng thời gian thực thi**: **{total_duration:.1f}s** (Trung bình: **{total_duration/total_cases:.2f}s/case**)",
        f"",
        f"---",
        f"",
        f"## 1. Tổng Hợp Theo Từng Slice (Phân Nhóm)",
        f"",
        f"| Slice | Số Case | Passed | Failed | Pass Rate |",
        f"| :--- | :---: | :---: | :---: | :---: |",
    ]

    for s in report.by_slice:
        rate_str = f"{s.rate:.1%}" if s.rate is not None else "N/A"
        lines.append(f"| **{s.slice_type}** | {s.total} | {s.passed} | {s.total - s.passed} | **{rate_str}** |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 2. Bảng Chi Tiết Toàn Bộ 33 Test Cases",
        f"",
        f"| STT | Case ID | Slice | Câu Hỏi | Pipeline Trace Agent | Tokens (App/Judge) | Chi Phí (VNĐ) | Kết Quả | Chi Tiết / Lý Do |",
        f"| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |",
    ])

    for c in detailed_results:
        stt = c["index"]
        cid = c["case_id"]
        s_type = c["slice"]
        q = c["question"].replace("|", "\\|")
        trace = c["pipeline_trace"].replace("|", "\\|")
        t_app = c["tokens"]["app_tokens"]
        t_judge = c["tokens"]["judge_tokens"]
        cost_vnd = f"{c['cost']['vnd']:,.0f}đ"
        status_badge = "✅ **PASS**" if c["passed"] else "❌ **FAIL**"

        # Details / Notes
        reasons = []
        if not c["scoring"]["rule_based"]["passed"]:
            if c["scoring"]["rule_based"]["missing"]:
                reasons.append(f"Missing: {c['scoring']['rule_based']['missing']}")
            if c["scoring"]["rule_based"]["forbidden_found"]:
                reasons.append(f"Forbidden: {c['scoring']['rule_based']['forbidden_found']}")
        judge = c["scoring"]["llm_judge"]
        if judge and not judge.get("skipped"):
            sc = judge.get("score") or {}
            reasons.append(f"Judge: {sc.get('overall', 0):.1f}/5 ({sc.get('reasoning', '')[:60]}...)")
        ts = c["scoring"]["task_success"]
        if ts and not ts.get("skipped") and ts.get("result"):
            r = ts.get("result")
            if not r.get("success"):
                reasons.append(f"TaskFail: {r.get('reasoning', '')[:60]}...")
        if c.get("error"):
            reasons.append(f"Error: {c['error']}")

        notes = "<br>".join(reasons) if reasons else "Tất cả tiêu chí đạt chuẩn"
        notes = notes.replace("|", "\\|")

        lines.append(
            f"| {stt} | `{cid}` | `{s_type}` | {q} | `{trace}` | {t_app:,} / {t_judge:,} | {cost_vnd} | {status_badge} | {notes} |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 3. Bảng Phân Tích Câu Hỏi & Câu Trả Lời Chi Tiết",
        f"",
    ])

    for c in detailed_results:
        status_icon = "✅" if c["passed"] else "❌"
        lines.extend([
            f"### {status_icon} Case [{c['case_id']}] - {c['slice']}",
            f"- **Câu hỏi**: {c['question']}",
            f"- **Expected**: {c['expected']}",
            f"- **Pipeline Trace**: `{c['pipeline_trace']}`",
            f"- **Token & Chi phí**: {c['tokens']['total_tokens']} tokens ({c['tokens']['app_tokens']} app + {c['tokens']['judge_tokens']} judge) | **{c['cost']['vnd']:,.0f} VNĐ** (${c['cost']['usd']:.5f})",
            f"- **Thời gian phản hồi**: {c['latency_s']}s",
            f"- **Câu trả lời thực tế**:",
            f"```text",
            f"{c['answer']}",
            f"```",
        ])
        if not c["passed"]:
            lines.extend([
                f"- **Lý do không đạt**:",
                f"  - Rule-based: Missing={c['scoring']['rule_based']['missing']}, Forbidden={c['scoring']['rule_based']['forbidden_found']}",
                f"  - LLM-Judge: {json.dumps(c['scoring']['llm_judge'].get('score'), ensure_ascii=False) if not c['scoring']['llm_judge'].get('skipped') else 'Skipped'}",
            ])
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    run_detailed_evaluation()
