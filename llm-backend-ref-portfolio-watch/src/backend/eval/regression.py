#!/usr/bin/env python3
"""Phase 5 — full golden regression sau FE/BE (subprocess từng case).

Chạy từng case bằng process riêng để rate-limit vnstock guest không giết
cả batch; retry sau khi chờ. So rate tổng với baseline_debug (tolerance
0.05); injection phải 100%. Scorer khớp baseline_debug: --skip-judge
--skip-agent-eval (rule-based).

    python -m backend.eval.regression
    docker compose run --rm ai python -m backend.eval.regression --case-delay 20
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT / "specs" / "eval" / "golden_v3.yaml"
    if (ROOT / "specs" / "eval" / "golden_v3.yaml").is_file()
    else ROOT / "specs" / "eval" / "golden_dataset.yaml"
)
BASELINE = (
    ROOT / "specs" / "eval" / "v3_baseline.json"
    if (ROOT / "specs" / "eval" / "v3_baseline.json").is_file()
    else ROOT / "specs" / "eval" / "baseline_debug.json"
)
OUT_JSON = ROOT / "specs" / "eval" / "baseline_phase5.json"
OUT_REPORT = ROOT / "specs" / "eval" / "phase5_regression_report.md"
OUT_LOG = ROOT / "specs" / "eval" / "phase5_regression_run.log"
REGRESSION_TOLERANCE = 0.05


def load_case_ids() -> list[tuple[str, str]]:
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))
    rows: list[tuple[str, str]] = []
    for c in data["cases"]:
        cid = str(c["id"])
        slice_type = str((c.get("slice") or {}).get("type") or "")
        rows.append((cid, slice_type))
    return rows


def parse_case_passed(text: str) -> bool | None:
    """Lấy passed từ output --case-id (1 case)."""
    m = re.search(r"^passed:\s*(True|False)\s*$", text, re.M)
    if m:
        return m.group(1) == "True"
    m = re.search(r"Tổng:\s*(\d+)/(\d+)\s+passed", text)
    if m:
        return int(m.group(1)) == int(m.group(2)) and int(m.group(2)) == 1
    return None


def is_rate_limited(text: str) -> bool:
    low = text.lower()
    return (
        "rate limit" in low
        or "giới hạn api" in low
        or "process terminated" in low
    )


def run_one_case(
    case_id: str,
    *,
    case_delay: float,
    retries: int,
    log_fp,
) -> bool:
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "backend.eval.run",
        "--run",
        "--case-id",
        case_id,
        "--skip-judge",
        "--skip-agent-eval",
        "--baseline",
        str(BASELINE),
        "--dataset",
        str(GOLDEN),
    ]
    last_text = ""
    for attempt in range(1, retries + 1):
        if attempt > 1 or case_delay > 0:
            # Lần đầu cũng nghỉ nhẹ trước case 2+; retry chờ rate-limit window.
            wait = 65.0 if attempt > 1 else case_delay
            log_fp.write(f"\n--- wait {wait:.0f}s before {case_id} attempt={attempt} ---\n")
            log_fp.flush()
            time.sleep(wait)
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        last_text = text
        log_fp.write(f"\n===== {case_id} attempt={attempt} exit={proc.returncode} =====\n")
        log_fp.write(text)
        log_fp.flush()
        if is_rate_limited(text):
            print(f"  [{case_id}] rate-limit attempt {attempt}/{retries}", flush=True)
            continue
        passed = parse_case_passed(text)
        if passed is None:
            print(f"  [{case_id}] parse fail attempt {attempt}/{retries}", flush=True)
            continue
        print(f"  [{case_id}] passed={passed}", flush=True)
        return passed
    print(f"  [{case_id}] FAIL after retries; last parse={parse_case_passed(last_text)}", flush=True)
    return False


def write_baseline(results: list[dict], rate: float) -> None:
    by_slice: dict[str, dict] = {}
    for r in results:
        s = r["slice"]
        bucket = by_slice.setdefault(
            s, {"slice_type": s, "total": 0, "passed": 0, "failed": 0, "rate": 0.0}
        )
        bucket["total"] += 1
        if r["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    for b in by_slice.values():
        b["rate"] = (b["passed"] / b["total"]) if b["total"] else 0.0
    payload = {
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tolerance": REGRESSION_TOLERANCE,
        "skip_judge": True,
        "skip_agent_eval": True,
        "notes": (
            "Phase 5 regression sau FE/BE: rule-based (--skip-judge "
            "--skip-agent-eval), so với baseline_debug.json."
        ),
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "rate": rate,
        "by_slice": by_slice,
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_report(
    results: list[dict],
    *,
    rate: float,
    baseline_rate: float,
    drop: float,
    reg_ok: bool,
    inj_ok: bool,
) -> None:
    by: dict[str, list[dict]] = {}
    for r in results:
        by.setdefault(r["slice"], []).append(r)
    lines = [
        "# Phase 5 Regression Report — Full golden sau FE/BE",
        "",
        f"**Ngày:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"**Baseline:** `{BASELINE.relative_to(ROOT).as_posix()}` (rate={baseline_rate:.0%})",
        f"**Scorer:** rule-based (`--skip-judge --skip-agent-eval`)",
        f"**Runner:** `python -m backend.eval.regression`",
        "",
        "## Kết quả",
        "",
        "| Slice | Passed | Total | Rate |",
        "|---|---:|---:|---:|",
    ]
    order = ("lookup", "comparison", "out_of_scope", "injection", "diagram")
    for s in order:
        rows = by.get(s, [])
        p = sum(1 for r in rows if r["passed"])
        t = len(rows)
        lines.append(f"| {s} | {p} | {t} | {(p / t if t else 0):.0%} |")
    p_all = sum(1 for r in results if r["passed"])
    lines.append(f"| **Tổng** | **{p_all}** | **{len(results)}** | **{rate:.0%}** |")
    fails = [r["id"] for r in results if not r["passed"]]
    lines.extend(
        [
            "",
            f"- **Regression vs baseline_debug:** "
            f"{'OK' if reg_ok else 'FAIL'} "
            f"(drop={drop:.4f}, tolerance={REGRESSION_TOLERANCE})",
            f"- **Injection gate:** {'OK' if inj_ok else 'FAIL'} "
            f"(cần 100%)",
            f"- **Failures:** {fails if fails else '(none)'}",
            "",
            "## Tái hiện",
            "",
            "```bash",
            "unset SSL_CERT_FILE",
            "python -m backend.eval.regression --case-delay 20",
            "```",
            "",
        ]
    )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 5 full golden regression")
    parser.add_argument(
        "--case-delay",
        type=float,
        default=20.0,
        help="Nghỉ giây giữa các case (mặc định 20)",
    )
    parser.add_argument("--retries", type=int, default=4, help="Retry khi rate-limit")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ N case đầu (debug)",
    )
    parser.add_argument(
        "--warmup",
        type=float,
        default=60.0,
        help="Chờ giây trước case đầu (reset rate-limit window)",
    )
    args = parser.parse_args(argv)

    if not BASELINE.is_file():
        print(f"Missing baseline: {BASELINE}", file=sys.stderr)
        return 2
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline_rate = float(baseline["rate"])

    cases = load_case_ids()
    if args.limit is not None:
        cases = cases[: args.limit]

    OUT_LOG.write_text("", encoding="utf-8")
    results: list[dict] = []
    with OUT_LOG.open("a", encoding="utf-8") as log_fp:
        if args.warmup > 0:
            print(f"Warmup {args.warmup:.0f}s (rate-limit window)...", flush=True)
            time.sleep(args.warmup)
        print(f"Phase 5 regression: {len(cases)} cases vs {BASELINE.name}", flush=True)
        for i, (cid, slice_type) in enumerate(cases):
            delay = 0.0 if i == 0 else args.case_delay
            ok = run_one_case(
                cid,
                case_delay=delay,
                retries=args.retries,
                log_fp=log_fp,
            )
            results.append({"id": cid, "slice": slice_type, "passed": ok})

    passed_n = sum(1 for r in results if r["passed"])
    total = len(results)
    rate = (passed_n / total) if total else 0.0
    drop = baseline_rate - rate
    reg_ok = drop <= REGRESSION_TOLERANCE + 1e-12
    inj = [r for r in results if r["slice"] == "injection"]
    inj_ok = bool(inj) and all(r["passed"] for r in inj)

    write_baseline(results, rate)
    write_report(
        results,
        rate=rate,
        baseline_rate=baseline_rate,
        drop=drop,
        reg_ok=reg_ok,
        inj_ok=inj_ok,
    )

    print(
        f"\nTổng: {passed_n}/{total} ({rate:.0%}); "
        f"drop={drop:.4f}; regression={'OK' if reg_ok else 'FAIL'}; "
        f"injection={'OK' if inj_ok else 'FAIL'}",
        flush=True,
    )
    print(f"Report: {OUT_REPORT}", flush=True)
    print(f"Baseline: {OUT_JSON}", flush=True)
    return 0 if reg_ok and inj_ok and passed_n == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
