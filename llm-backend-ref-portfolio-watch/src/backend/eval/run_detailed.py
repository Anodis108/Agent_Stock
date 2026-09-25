#!/usr/bin/env python3
"""Detailed evaluation runner for golden_v4.yaml (30 cases) with token and cost tracking.

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
- specs/eval/eval_results_golden_v4.md (Markdown table & summary)
- specs/eval/eval_results_golden_v4.json (Full machine-readable JSON)
"""

from __future__ import annotations

import argparse
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

def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "specs").is_dir() or (p / "pyproject.toml").is_file():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[3]


ROOT = _find_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import yaml
from openai.types.chat import ChatCompletion

from backend.eval.run import (
    BASELINE_PATH,
    GOLDEN_V4_PATH,
    GOLDEN_V5_PATH,
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
from backend.infra.llm import completion as completion_mod
from backend.infra.llm.params import GenerationParams
from backend.shared.settings import settings

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
    from backend.infra.llm.client import get_client, mark_current_key_limited
    from backend.infra.llm.resilience import retry_with_backoff

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
    from backend.infra.llm.client import get_client, mark_current_key_limited
    from backend.infra.llm.resilience import retry_with_backoff

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
    from backend.infra.llm.client import get_client, mark_current_key_limited
    from backend.infra.llm.resilience import retry_with_backoff

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


class CachedPriceSource:
    def __init__(self, inner):
        self.inner = inner
        self.cache: dict[str, Any] = {}

    def fetch_latest_close(self, symbol: str):
        sym = (symbol or "").strip().upper()
        if sym in self.cache:
            return self.cache[sym]
        try:
            res = self.inner.fetch_latest_close(sym)
            if res.error is None and res.latest_close is not None:
                self.cache[sym] = res
            return res
        except (Exception, SystemExit) as exc:
            from backend.domain.ports import PriceQuote
            return PriceQuote(symbol=sym, latest_close=None, error=f"lỗi nguồn giá: {exc}")


class CachedNewsSource:
    def __init__(self, inner):
        self.inner = inner
        self.cache: dict[tuple, Any] = {}

    def fetch_news(self, symbol: str, days: int = 7, limit: int = 5):
        key = ((symbol or "").upper(), days, limit)
        if key in self.cache:
            return self.cache[key]
        try:
            res = self.inner.fetch_news(symbol, days=days, limit=limit)
            self.cache[key] = res
            return res
        except (Exception, SystemExit) as exc:
            return []


def run_detailed_evaluation(
    dataset_path: Path | None = None,
    output_md_path: Path | None = None,
    output_json_path: Path | None = None,
    case_delay_sec: float = 0.5,
    limit: int | None = None,
    slice_filter: str | None = None,
    case_id_filter: str | None = None,
    skip_judge: bool = False,
    skip_agent_eval: bool = False,
    save_baseline: bool = False,
):
    from backend.api.deps import get_app_deps

    save_baseline_flag = save_baseline
    p = dataset_path or (GOLDEN_V5_PATH if GOLDEN_V5_PATH.is_file() else GOLDEN_V4_PATH)
    out_md = output_md_path or (ROOT / "specs" / "eval" / "eval_results_golden_v5.md")
    out_json = output_json_path or (ROOT / "specs" / "eval" / "eval_results_golden_v5.json")

    print(f"\n========================================================")
    print(f"  BẮT ĐẦU ĐÁNH GIÁ DATASET: {p.name}")
    print(f"  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"========================================================\n")

    deps = get_app_deps()
    cached_price = CachedPriceSource(deps.price_source)
    cached_news = CachedNewsSource(deps.news_source)

    golden_data = load_golden_dataset(p)
    cases = golden_data.get("cases", [])

    if case_id_filter:
        cases = [c for c in cases if str(c.get("id")) == case_id_filter]
    elif slice_filter:
        cases = [c for c in cases if (c.get("slice") or {}).get("type") == slice_filter]

    if limit is not None and limit > 0:
        cases = cases[:limit]

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
        fn = make_answer_fn(
            price_source=cached_price,
            news_source=cached_news,
            history_store=deps.history_store,
            memory_store=deps.memory_store,
            user_id=f"eval-{cid}",
        )

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
            skip_judge=skip_judge,
            skip_agent_eval=skip_agent_eval,
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
                "llm_judge": res.judge.as_dict() if hasattr(res.judge, "as_dict") else res.judge,
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
            if hasattr(res.judge, "skipped") and not res.judge.skipped:
                print(f"      [FAIL REASON] Judge: {res.judge.passed} (Score: {getattr(res.judge.score, 'overall', 'N/A')})")
            if res.task_success and not res.task_success.skipped and res.task_success.result:
                print(f"      [FAIL REASON] TaskSuccess: {res.task_success.result.success} - {res.task_success.result.reasoning}")

        if case_delay_sec > 0 and idx < total_cases:
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
    print(f"  HOÀN THÀNH ĐÁNH GIÁ DATASET ({total_cases} CASES)")
    print(f"  Kết quả: {passed_count}/{total_cases} Passed ({pass_rate:.1f}%)")
    print(f"  Tổng Tokens: {total_tokens_all:,} (App: {total_app_tokens:,}, Judge: {total_judge_tokens:,})")
    print(f"  Tổng Chi Phí: ${total_cost_usd_all:.4f} USD (~ {total_cost_vnd_all:,.0f} VND)")
    print(f"  Tổng Thời Gian: {total_duration:.1f}s (Trung bình: {total_duration/total_cases:.2f}s/case if total_cases > 0 else 0)")
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

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md_content, encoding="utf-8")
    print(f"Đã lưu bảng kết quả Markdown tại: {out_md}")

    out_json.parent.mkdir(parents=True, exist_ok=True)
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
    out_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã lưu chi tiết JSON tại: {out_json}")

    if save_baseline_flag:
        v_num = "5" if "v5" in p.name else "4"
        baseline_obj = {
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "purpose": f"V{v_num} Product Edition — baseline đánh giá chất lượng {total_cases} cases chuẩn hóa",
            "dataset": f"resources/eval/{p.name}",
            "dataset_version": f"{v_num}.0",
            "tolerance": 0.05,
            "scorer_flags": {
                "rule_based": True,
                "must_include": True,
                "must_not_include": True,
                "llm_judge": not skip_judge,
                "agent_eval": not skip_agent_eval,
                "injection_gate_100pct": True,
            },
            "total": total_cases,
            "passed": passed_count,
            "rate": round(pass_rate / 100.0, 4),
            "by_slice": {s.slice_type: s.as_dict() for s in report.by_slice},
            "cases": [
                {
                    "id": c["case_id"],
                    "slice": c["slice"],
                    "passed": c["passed"],
                    "pipeline_trace": c["pipeline_trace"],
                    "tokens": c["tokens"]["total_tokens"],
                    "cost_usd": c["cost"]["usd"],
                }
                for c in detailed_results
            ],
        }
        target_baselines = [
            ROOT / "resources" / "eval" / f"v{v_num}_baseline.json",
            ROOT / "specs" / "eval" / f"v{v_num}_baseline.json",
        ]
        for b_path in target_baselines:
            b_path.parent.mkdir(parents=True, exist_ok=True)
            b_path.write_text(json.dumps(baseline_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Đã lưu baseline thành công tại: {b_path}")

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
        f"- **Tổng thời gian thực thi**: **{total_duration:.1f}s** (Trung bình: **{total_duration/total_cases:.2f}s/case**)" if total_cases > 0 else "- **Tổng thời gian thực thi**: 0s",
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
        f"## 2. Bảng Chi Tiết Toàn Bộ {total_cases} Test Cases",
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
        if isinstance(judge, dict) and not judge.get("skipped"):
            sc = judge.get("score") or {}
            reasons.append(f"Judge: {sc.get('overall', 0):.1f}/5 ({sc.get('reasoning', '')[:60]}...)")
        ts = c["scoring"]["task_success"]
        if isinstance(ts, dict) and not ts.get("skipped") and ts.get("result"):
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
                f"  - LLM-Judge: {json.dumps(c['scoring']['llm_judge'].get('score'), ensure_ascii=False) if isinstance(c['scoring']['llm_judge'], dict) and not c['scoring']['llm_judge'].get('skipped') else 'Skipped'}",
            ])
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detailed evaluation runner for golden_v5 with token/cost tracking"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=GOLDEN_V5_PATH if GOLDEN_V5_PATH.is_file() else GOLDEN_V4_PATH,
        help="Đường dẫn file golden dataset YAML (mặc định golden_v5.yaml)",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Đường dẫn file Markdown báo cáo (mặc định specs/eval/eval_results_golden_v5.md)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Đường dẫn file JSON chi tiết (mặc định specs/eval/eval_results_golden_v5.json)",
    )
    parser.add_argument(
        "--slice",
        type=str,
        default=None,
        help="Chỉ chạy các case thuộc slice chỉ định (ví dụ: lookup, injection)",
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="Chỉ chạy đúng 1 case theo ID (ví dụ: lookup_01)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số case cần chạy (hữu ích khi debug)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Độ trễ giữa các case (giây) để tránh rate limit (mặc định: 0.5s)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Bỏ qua chấm điểm LLM Judge",
    )
    parser.add_argument(
        "--skip-agent-eval",
        action="store_true",
        help="Bỏ qua đánh giá Task Success & Trajectory",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Lưu kết quả đánh giá thành baseline chính thức v4 (resources/eval/v4_baseline.json)",
    )

    args = parser.parse_args(argv)

    run_detailed_evaluation(
        dataset_path=args.dataset,
        output_md_path=args.output_md,
        output_json_path=args.output_json,
        case_delay_sec=args.delay,
        limit=args.limit,
        slice_filter=args.slice,
        case_id_filter=args.case_id,
        skip_judge=args.skip_judge,
        skip_agent_eval=args.skip_agent_eval,
        save_baseline=args.save_baseline,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
