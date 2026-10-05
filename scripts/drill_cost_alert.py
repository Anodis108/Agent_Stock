#!/usr/bin/env python3
"""Drill: cost budget alert — exit 1 nếu vượt ngưỡng."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.infra.cost.tracker import (  # noqa: E402
    get_cost_tracker,
    is_over_alert_threshold,
)
from backend.shared.settings import settings  # noqa: E402


def main() -> int:
    tracker = get_cost_tracker()
    total = tracker.total_cost_usd
    alert = settings.cost_alert_threshold_usd
    limit = settings.cost_daily_limit_usd
    print(f"Total cost: ${total:.6f}")
    print(f"Alert threshold: ${alert:.4f}")
    print(f"Daily limit: ${limit:.4f}" + (" (unlimited)" if limit <= 0 else ""))
    if limit > 0 and total >= limit:
        print("FAIL: daily budget exceeded")
        return 1
    if is_over_alert_threshold():
        print("WARN: over alert threshold")
        return 1
    print("OK: within budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
