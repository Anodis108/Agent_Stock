#!/usr/bin/env python3
"""SSE / LLM concurrency benchmark — M3-B4 Phase 10.

Đo p50/p95 thời gian chờ slot LLM_SEMAPHORE với 50 request đồng thời (simulated).

    PYTHONPATH=src python scripts/benchmark_sse.py
    PYTHONPATH=src python scripts/benchmark_sse.py --requests 50 --job-ms 200
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

from backend.eval.history import get_git_sha  # noqa: E402
from backend.infra.llm.semaphore import (  # noqa: E402
    get_llm_semaphore_limit,
    llm_semaphore_slot,
    reset_llm_semaphore_for_tests,
)

REPORT_MD = ROOT / "specs" / "eval" / "sse_benchmark.md"
REPORT_JSON = ROOT / "specs" / "eval" / "sse_benchmark.json"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def run_semaphore_benchmark(
    *,
    semaphore: int,
    requests: int,
    job_ms: float,
) -> dict:
    os.environ["LLM_SEMAPHORE"] = str(semaphore)
    reset_llm_semaphore_for_tests()

    latencies: list[float] = []
    active = 0
    peak_active = 0
    lock = threading.Lock()

    def job() -> float:
        nonlocal active, peak_active
        t0 = time.perf_counter()
        with llm_semaphore_slot():
            with lock:
                active += 1
                peak_active = max(peak_active, active)
            try:
                time.sleep(job_ms / 1000.0)
            finally:
                with lock:
                    active -= 1
        return time.perf_counter() - t0

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=requests) as pool:
        futures = [pool.submit(job) for _ in range(requests)]
        for fut in as_completed(futures):
            latencies.append(fut.result())
    wall_sec = time.perf_counter() - t_wall0

    return {
        "llm_semaphore": get_llm_semaphore_limit(),
        "requests": requests,
        "job_ms": job_ms,
        "wall_sec": round(wall_sec, 3),
        "peak_concurrent": peak_active,
        "p50_sec": round(_percentile(latencies, 50), 4),
        "p95_sec": round(_percentile(latencies, 95), 4),
        "max_sec": round(max(latencies) if latencies else 0.0, 4),
    }


def format_report_md(results: dict[str, dict], *, git_sha: str) -> str:
    lines = [
        "# SSE / LLM Concurrency Benchmark — Portfolio Watch (Phase 10)",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Git SHA:** `{git_sha}`",
        f"- **Method:** Simulated LLM job ({results['sem5']['job_ms']:.0f}ms) × "
        f"{results['sem5']['requests']} concurrent requests",
        "",
        "## p50 / p95 theo LLM_SEMAPHORE",
        "",
        "| LLM_SEMAPHORE | Requests | Peak concurrent | Wall (s) | p50 (s) | p95 (s) | max (s) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in (("sem5", "5"), ("sem20", "20")):
        r = results[key]
        lines.append(
            f"| {label} | {r['requests']} | {r['peak_concurrent']} | {r['wall_sec']} | "
            f"{r['p50_sec']} | {r['p95_sec']} | {r['max_sec']} |"
        )
    lines.extend(
        [
            "",
            "## Ghi chú",
            "",
            "- Semaphore 5 giới hạn peak concurrent ≤ 5; semaphore 20 cho phép cao hơn → p95 thấp hơn.",
            "- Benchmark này mô phỏng slot LLM; live SSE cần `docker compose up` + API key.",
            "- Chạy: `PYTHONPATH=src python scripts/benchmark_sse.py`",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(
    *,
    requests: int = 50,
    job_ms: float = 200.0,
    output_md: Path = REPORT_MD,
    output_json: Path = REPORT_JSON,
) -> dict:
    sem5 = run_semaphore_benchmark(semaphore=5, requests=requests, job_ms=job_ms)
    sem20 = run_semaphore_benchmark(semaphore=20, requests=requests, job_ms=job_ms)
    git_sha = get_git_sha()
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git_sha,
        "sem5": sem5,
        "sem20": sem20,
    }
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(format_report_md(payload, git_sha=git_sha), encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {output_md}")
    print(f"JSON:   {output_json}")
    print(
        f"sem5  p50={sem5['p50_sec']}s p95={sem5['p95_sec']}s peak={sem5['peak_concurrent']}"
    )
    print(
        f"sem20 p50={sem20['p50_sec']}s p95={sem20['p95_sec']}s peak={sem20['peak_concurrent']}"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="SSE/LLM semaphore benchmark")
    parser.add_argument("--requests", type=int, default=50, help="Số request đồng thời")
    parser.add_argument("--job-ms", type=float, default=200.0, help="Thời gian mô phỏng mỗi LLM call (ms)")
    args = parser.parse_args()
    run_benchmark(requests=args.requests, job_ms=args.job_ms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
