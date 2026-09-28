#!/usr/bin/env python3
"""Noise calibration — M3-B2 Phase 6: đo σ từ eval history.

Đọc specs/eval/history/*.json và in gợi ý drop_tolerance.

Chạy full eval 3 lần cùng commit (manual, cần API):
  PYTHONPATH=src python -m backend.eval.run --subset --json out.json --save-history
  (lặp 3 lần)

Sau đó:
  PYTHONPATH=src python scripts/eval_noise_calibration.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.eval.history import (  # noqa: E402
    calibrate_tolerance_from_history,
    compute_noise_stats,
    load_history_reports,
    resolve_history_dir,
)


def main() -> int:
    history_dir = resolve_history_dir()
    records = load_history_reports(history_dir)
    rates = []
    for rec in records:
        report = rec.get("report") or rec
        if isinstance(report, dict) and "rate" in report:
            rates.append(float(report["rate"]))

    print(f"History dir: {history_dir}")
    print(f"Files: {len(records)}")
    calibration = calibrate_tolerance_from_history(history_dir)
    print(json.dumps(calibration, ensure_ascii=False, indent=2))

    if len(rates) >= 3:
        same_sha: dict[str, list[float]] = {}
        for rec in records:
            sha = str(rec.get("git_sha") or "unknown")
            report = rec.get("report") or rec
            if isinstance(report, dict) and "rate" in report:
                same_sha.setdefault(sha, []).append(float(report["rate"]))
        for sha, sha_rates in same_sha.items():
            if len(sha_rates) >= 3:
                stats = compute_noise_stats(sha_rates)
                print(f"\nCommit {sha} — {stats['count']} runs:")
                print(f"  mean={stats['mean']:.4f} σ={stats['stdev']:.4f}")
                print(f"  recommended_drop_tolerance={stats['recommended_drop_tolerance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
