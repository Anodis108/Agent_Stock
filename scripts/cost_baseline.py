#!/usr/bin/env python3
"""Cost baseline — M3-B3 Phase 7–8: replay FAQ, ghi token/cost.

    PYTHONPATH=src python scripts/cost_baseline.py
    PYTHONPATH=src python scripts/cost_baseline.py --limit 5
    PYTHONPATH=src python scripts/cost_baseline.py --dry-run
    PYTHONPATH=src python scripts/cost_baseline.py --with-cache tier1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from backend.eval.history import get_git_sha  # noqa: E402
from backend.infra.cost.tracker import (  # noqa: E402
    get_cost_tracker,
    reset_cost_tracker,
    set_cost_context,
)

REPLAY_PATH = ROOT / "resources" / "eval" / "replay_faq.yaml"
REPORT_MD = ROOT / "specs" / "eval" / "cost_baseline.md"
REPORT_JSON = ROOT / "specs" / "eval" / "cost_baseline.json"


def load_replay_faq(path: Path | None = None) -> list[dict]:
    p = path or REPLAY_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    questions = data.get("questions") or []
    if len(questions) != 50:
        raise ValueError(f"replay_faq cần 50 câu, có {len(questions)}")
    dups = sum(1 for q in questions if q.get("near_duplicate_of"))
    if dups < 14:
        raise ValueError(f"Cần ~30% near-duplicate, có {dups}")
    return questions


def format_report_md(
    summary: dict,
    *,
    questions_run: int,
    elapsed_sec: float,
    git_sha: str,
    dry_run: bool,
    with_cache: str | None = None,
    passes: int = 1,
) -> str:
    if with_cache == "tier1":
        mode = "exact cache tier1 (2 passes)" + (" dry-run" if dry_run else "")
    elif dry_run:
        mode = "dry-run (no LLM)"
    else:
        mode = "live (no cache)"
    lines = [
        "# Cost Baseline — Portfolio Watch (Phase 7–8)",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Git SHA:** `{git_sha}`",
        f"- **Dataset:** `resources/eval/replay_faq.yaml` (50 FAQ, ~30% near-duplicate)",
        f"- **Mode:** {mode}",
        f"- **Passes:** {passes}",
        f"- **Questions run:** {questions_run}",
        f"- **Elapsed:** {elapsed_sec:.1f}s",
        "",
        "## Tổng hợp",
        "",
        f"| Metric | Value |",
        f"| :--- | :--- |",
        f"| LLM requests | {summary['requests']} |",
        f"| Total tokens | {summary['total_tokens']:,} |",
        f"| Total cost (USD) | ${summary['total_cost_usd']:.6f} |",
        f"| Total cost (VND) | {summary['total_cost_vnd']:,.0f} |",
        f"| Cache hits | {summary['cache_hits']} (rate {summary['cache_hit_rate']:.0%}) |",
        "",
        "## Theo feature",
        "",
        "| Feature | Requests | Tokens | Cost USD |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for feat, stats in sorted(summary.get("by_feature", {}).items()):
        lines.append(
            f"| {feat} | {stats['requests']} | {stats['tokens']:,} | "
            f"${stats['cost_usd']:.6f} |"
        )
    notes = [
        "",
        "## Ghi chú",
        "",
    ]
    if with_cache == "tier1":
        notes.extend(
            [
                "- Chạy **2 pass** cùng dataset; pass 2 kỳ vọng `cache_hit > 0` trên câu trùng.",
                "- Exact cache key: `prompt_name` + `prompt_version` + `model` + `normalized_question`.",
                "- Chạy: `PYTHONPATH=src python scripts/cost_baseline.py --with-cache tier1`.",
            ]
        )
    else:
        notes.extend(
            [
                "- Baseline này đo **trước cache** (`cache_hit=false` trên mọi request).",
                "- So sánh sau khi bật cache: `--with-cache tier1`.",
                "- Chạy đầy đủ: `PYTHONPATH=src python scripts/cost_baseline.py` (cần API key).",
            ]
        )
    notes.append("")
    lines.extend(notes)
    return "\n".join(lines)


def run_baseline(
    *,
    limit: int | None = None,
    dry_run: bool = False,
    with_cache: str | None = None,
    output_md: Path = REPORT_MD,
    output_json: Path = REPORT_JSON,
) -> dict:
    questions = load_replay_faq()
    if limit is not None:
        questions = questions[:limit]

    passes = 2 if with_cache == "tier1" else 1
    if with_cache == "tier1":
        os.environ["EXACT_CACHE_ENABLED"] = "true"
        from backend.infra.cache.exact import get_exact_cache

        get_exact_cache().clear()
    else:
        os.environ["EXACT_CACHE_ENABLED"] = "false"

    reset_cost_tracker()
    tracker = get_cost_tracker()
    t0 = time.perf_counter()

    if dry_run:
        llm_calls_per_question = 3  # rewrite + supervisor + answer (ước lượng)
        for pass_num in range(passes):
            for i, item in enumerate(questions):
                for _ in range(llm_calls_per_question):
                    is_hit = with_cache == "tier1" and pass_num >= 1
                    set_cost_context(
                        feature="chat_replay",
                        prompt_version="production",
                        cache_hit=is_hit,
                    )
                    tracker.record_cost(
                        feature="chat_replay",
                        model="gpt-4o-mini",
                        prompt_version="production",
                        cache_hit=is_hit,
                        prompt_tokens=0 if is_hit else 800 + (i % 5) * 50,
                        completion_tokens=0 if is_hit else 120 + (i % 3) * 20,
                    )
    else:
        from backend.eval.run import make_answer_fn

        answer_fn = make_answer_fn(user_id="cost-baseline")
        for pass_num in range(passes):
            for item in questions:
                q = str(item.get("question") or "")
                set_cost_context(
                    feature="chat_replay",
                    prompt_version="production",
                )
                try:
                    answer_fn(q)
                except Exception as exc:
                    label = f"pass{pass_num + 1}:{item.get('id')}"
                    print(f"WARN [{label}]: {exc}", file=sys.stderr)

    elapsed = time.perf_counter() - t0
    summary = tracker.summary()
    git_sha = get_git_sha()
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git_sha,
        "dry_run": dry_run,
        "with_cache": with_cache,
        "passes": passes,
        "questions_run": len(questions),
        "elapsed_sec": round(elapsed, 2),
        "summary": summary,
        "records": [r.as_dict() for r in tracker.records],
    }

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(
        format_report_md(
            summary,
            questions_run=len(questions),
            elapsed_sec=elapsed,
            git_sha=git_sha,
            dry_run=dry_run,
            with_cache=with_cache,
            passes=passes,
        ),
        encoding="utf-8",
    )
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Report: {output_md}")
    print(f"JSON:   {output_json}")
    print(
        f"Total: {summary['total_tokens']:,} tokens, "
        f"${summary['total_cost_usd']:.6f} USD "
        f"({summary['total_cost_vnd']:,.0f} VND)"
    )
    os.environ.pop("EXACT_CACHE_ENABLED", None)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Cost baseline replay")
    parser.add_argument("--limit", type=int, default=None, help="Chỉ chạy N câu đầu")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate token/cost (không gọi LLM) — tạo report cấu trúc",
    )
    parser.add_argument(
        "--with-cache",
        choices=["tier1"],
        default=None,
        help="Bật exact cache tier1; chạy 2 pass cùng dataset",
    )
    args = parser.parse_args()
    run_baseline(
        limit=args.limit,
        dry_run=args.dry_run,
        with_cache=args.with_cache,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
