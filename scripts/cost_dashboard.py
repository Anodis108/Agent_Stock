#!/usr/bin/env python3
"""Cost dashboard — M3-B7 Phase 13: cost, p95 latency, cache hit rate."""

from __future__ import annotations

import argparse
import json
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
    parser = argparse.ArgumentParser(description="Cost & observability dashboard")
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit 1 if cost exceeds COST_ALERT_THRESHOLD_USD or daily limit",
    )
    args = parser.parse_args()

    tracker = get_cost_tracker()
    summary = tracker.summary()
    
    p95_latency = None
    latencies = []
    
    history_dir = Path("specs/eval/history")
    if history_dir.exists():
        for file in history_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if "metrics" in item and "latency_s" in item["metrics"]:
                                latencies.append(item["metrics"]["latency_s"])
                    elif isinstance(data, dict):
                        if "results" in data:
                            for item in data["results"]:
                                if "metrics" in item and "latency_s" in item["metrics"]:
                                    latencies.append(item["metrics"]["latency_s"])
            except Exception:
                pass
    
    if latencies:
        latencies.sort()
        idx = int(len(latencies) * 0.95)
        p95_latency = latencies[idx] if idx < len(latencies) else latencies[-1]
    
    total_usd = summary.get("total_cost_usd", 0.0)
    total_vnd = summary.get("total_cost_vnd", 0.0)
    cache_hit_rate = summary.get("cache_hit_rate", 0.0) * 100
    
    if p95_latency is None:
        p95_latency = 0.0
        
    dashboard_md = f"""# Cost & Observability Dashboard

## Key Metrics
- **Total Cost**: ${total_usd:.6f} ({total_vnd:,.0f} VND)
- **Cache Hit Rate**: {cache_hit_rate:.1f}%
- **p95 Latency**: {p95_latency:.2f}s

## Details
```json
{json.dumps(summary, indent=2)}
```
"""

    out_md = Path("specs/eval/cost_dashboard.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(dashboard_md, encoding="utf-8")
    
    out_json = Path("specs/eval/cost_dashboard.json")
    budget_limit = settings.cost_daily_limit_usd
    alert_threshold = settings.cost_alert_threshold_usd
    over_alert = is_over_alert_threshold()
    over_budget = budget_limit > 0 and total_usd >= budget_limit

    out_json.write_text(json.dumps({
        "total_usd": total_usd,
        "total_vnd": total_vnd,
        "cache_hit_rate_pct": cache_hit_rate,
        "p95_latency_s": p95_latency,
        "cost_alert_threshold_usd": alert_threshold,
        "cost_daily_limit_usd": budget_limit,
        "over_alert": over_alert,
        "over_budget": over_budget,
        "summary": summary
    }, indent=2), encoding="utf-8")

    print(f"Dashboard generated: {out_md}")
    if over_budget:
        print(f"FAIL: daily budget exceeded (${total_usd:.6f} >= ${budget_limit:.4f})")
        return 1
    if args.fail_on_alert and over_alert:
        print(f"WARN: over alert threshold (${total_usd:.6f} >= ${alert_threshold:.4f})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
