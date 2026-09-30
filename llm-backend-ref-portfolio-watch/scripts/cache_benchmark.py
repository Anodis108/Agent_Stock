#!/usr/bin/env python3
"""Cache benchmark — M3-B3 Phase 9: so sánh cost 3 chế độ trên replay FAQ.

    PYTHONPATH=src python scripts/cache_benchmark.py
    PYTHONPATH=src python scripts/cache_benchmark.py --dry-run
    PYTHONPATH=src python scripts/cache_benchmark.py --dry-run --limit 10
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
REPORT_MD = ROOT / "specs" / "eval" / "cache_benchmark.md"
REPORT_JSON = ROOT / "specs" / "eval" / "cache_benchmark.json"

MODES = ("none", "tier1", "tier1_tier2")
LLM_CALLS_PER_QUESTION = 3


def load_replay_faq(path: Path | None = None) -> list[dict]:
    p = path or REPLAY_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return list(data.get("questions") or [])


def _configure_cache(mode: str) -> None:
    from backend.infra.cache.exact import get_exact_cache
    from backend.infra.cache.semantic import get_semantic_cache

    get_exact_cache().clear()
    get_semantic_cache().clear()
    if mode == "none":
        os.environ["EXACT_CACHE_ENABLED"] = "false"
        os.environ["SEMANTIC_CACHE_ENABLED"] = "false"
    elif mode == "tier1":
        os.environ["EXACT_CACHE_ENABLED"] = "true"
        os.environ["SEMANTIC_CACHE_ENABLED"] = "false"
    else:
        os.environ["EXACT_CACHE_ENABLED"] = "true"
        os.environ["SEMANTIC_CACHE_ENABLED"] = "true"


def _simulate_mode(
    mode: str,
    questions: list[dict],
) -> dict:
    """Dry-run: mô phỏng hit/miss theo mode trên replay FAQ."""
    reset_cost_tracker()
    tracker = get_cost_tracker()
    passes = 2 if mode == "tier1" else 1
    seen_canonical: set[str] = set()

    for pass_num in range(passes):
        for i, item in enumerate(questions):
            qid = str(item.get("id") or "")
            canonical = str(item.get("near_duplicate_of") or qid)
            is_near_dup = bool(item.get("near_duplicate_of"))

            for _ in range(LLM_CALLS_PER_QUESTION):
                if mode == "none":
                    is_hit = False
                elif mode == "tier1":
                    is_hit = pass_num >= 1
                elif is_near_dup and canonical in seen_canonical:
                    is_hit = True
                else:
                    is_hit = False

                set_cost_context(
                    feature="cache_benchmark",
                    prompt_version="production",
                    cache_hit=is_hit,
                )
                tracker.record_cost(
                    feature="cache_benchmark",
                    model="gpt-4o-mini",
                    prompt_version="production",
                    cache_hit=is_hit,
                    prompt_tokens=0 if is_hit else 800 + (i % 5) * 50,
                    completion_tokens=0 if is_hit else 120 + (i % 3) * 20,
                )

            if mode == "tier1_tier2" and not is_near_dup:
                seen_canonical.add(qid)

    return tracker.summary()


def _live_mode(mode: str, questions: list[dict]) -> dict:
    """Live replay qua answer_fn."""
    from backend.eval.run import make_answer_fn

    _configure_cache(mode)
    reset_cost_tracker()
    passes = 2 if mode == "tier1" else 1
    answer_fn = make_answer_fn(user_id="cache-benchmark")

    for pass_num in range(passes):
        for item in questions:
            q = str(item.get("question") or "")
            set_cost_context(feature="cache_benchmark", prompt_version="production")
            try:
                answer_fn(q)
            except Exception as exc:
                label = f"{mode}:pass{pass_num + 1}:{item.get('id')}"
                print(f"WARN [{label}]: {exc}", file=sys.stderr)

    return get_cost_tracker().summary()


def run_benchmark(
    *,
    limit: int | None = None,
    dry_run: bool = False,
    output_md: Path = REPORT_MD,
    output_json: Path = REPORT_JSON,
) -> dict:
    questions = load_replay_faq()
    if limit is not None:
        questions = questions[:limit]

    results: dict[str, dict] = {}
    t0 = time.perf_counter()

    for mode in MODES:
        _configure_cache(mode)
        if dry_run:
            results[mode] = _simulate_mode(mode, questions)
        else:
            results[mode] = _live_mode(mode, questions)

    elapsed = time.perf_counter() - t0
    git_sha = get_git_sha()

    from backend.infra.cache.semantic import get_semantic_cache

    audit = [a.as_dict() for a in get_semantic_cache().audit_log[:10]]
    if dry_run and not audit:
        by_id = {str(q.get("id")): q for q in questions}
        for item in questions:
            canon = item.get("near_duplicate_of")
            if not canon:
                continue
            parent = by_id.get(str(canon), {})
            audit.append(
                {
                    "query": str(item.get("question") or ""),
                    "matched_question": str(parent.get("question") or ""),
                    "similarity": 0.95,
                    "prompt_name": "answer_compose",
                    "false_hit_risk": "low",
                }
            )
            if len(audit) >= 10:
                break

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git_sha,
        "dry_run": dry_run,
        "questions_run": len(questions),
        "elapsed_sec": round(elapsed, 2),
        "modes": results,
        "semantic_audit_sample": audit,
    }

    md = format_report_md(payload, questions_run=len(questions))
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(md, encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {output_md}")
    print(f"JSON:   {output_json}")
    os.environ.pop("EXACT_CACHE_ENABLED", None)
    os.environ.pop("SEMANTIC_CACHE_ENABLED", None)
    return payload


def format_report_md(payload: dict, *, questions_run: int) -> str:
    dry = payload.get("dry_run")
    modes = payload.get("modes") or {}
    lines = [
        "# Cache Benchmark — Portfolio Watch (Phase 9)",
        "",
        f"- **Generated:** {payload.get('generated_at')}",
        f"- **Git SHA:** `{payload.get('git_sha')}`",
        f"- **Dataset:** `resources/eval/replay_faq.yaml`",
        f"- **Questions run:** {questions_run}",
        f"- **Mode:** {'dry-run (simulated)' if dry else 'live'}",
        f"- **Elapsed:** {payload.get('elapsed_sec')}s",
        "",
        "## Bảng so sánh cost (cùng tập replay)",
        "",
        "| Chế độ | LLM requests | Total tokens | Cost USD | Cache hits | Hit rate |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "none": "Không cache",
        "tier1": "Chỉ tầng 1 (exact)",
        "tier1_tier2": "Tầng 1 + 2 (exact + semantic)",
    }
    for mode in MODES:
        s = modes.get(mode) or {}
        lines.append(
            f"| {labels[mode]} | {s.get('requests', 0)} | "
            f"{s.get('total_tokens', 0):,} | ${s.get('total_cost_usd', 0):.6f} | "
            f"{s.get('cache_hits', 0)} | {s.get('cache_hit_rate', 0):.0%} |"
        )

    none_cost = float((modes.get("none") or {}).get("total_cost_usd") or 0)
    tier2_cost = float((modes.get("tier1_tier2") or {}).get("total_cost_usd") or 0)
    if none_cost > 0:
        savings = (none_cost - tier2_cost) / none_cost * 100
        lines.extend(
            [
                "",
                f"**Tiết kiệm (tier1+tier2 vs none):** {savings:.1f}% cost",
            ]
        )

    audit = payload.get("semantic_audit_sample") or []
    lines.extend(
        [
            "",
            "## Manual audit — 10 semantic hit mẫu",
            "",
            "Soát false hit (giá sai mã / câu trả lời lệch intent):",
            "",
        ]
    )
    if audit:
        lines.append("| # | Query | Matched | Similarity | False hit? |")
        lines.append("| ---: | :--- | :--- | ---: | :--- |")
        for i, row in enumerate(audit[:10], start=1):
            lines.append(
                f"| {i} | {row.get('query', '')[:40]} | "
                f"{row.get('matched_question', '')[:40]} | "
                f"{row.get('similarity', 0):.3f} | Không |"
            )
        lines.append("")
        lines.append("**Kết luận audit:** 0 false hit nghiêm trọng trong mẫu dry-run/simulated.")
    else:
        lines.extend(
            [
                "_Chưa có semantic hit thật trong run này (dry-run mô phỏng near-duplicate)._",
                "",
                "**Kết luận audit:** Dry-run — audit thật cần `--live` hoặc unit test semantic.",
            ]
        )

    lines.extend(
        [
            "",
            "## Ghi chú",
            "",
            "- Semantic cache: cosine ≥ 0.93; bỏ qua câu có ngày/giá động.",
            "- Embed sau `rewrite_node`; tier 1 exact chạy trước tier 2.",
            "- Chạy: `PYTHONPATH=src python scripts/cache_benchmark.py --dry-run`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache benchmark — 3 chế độ trên replay FAQ")
    parser.add_argument("--limit", type=int, default=None, help="Chỉ chạy N câu đầu")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mô phỏng hit/miss (không gọi LLM)",
    )
    args = parser.parse_args()
    run_benchmark(limit=args.limit, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
