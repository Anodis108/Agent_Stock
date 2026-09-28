#!/usr/bin/env python3
"""Cost dashboard — M3-B7 Phase 13: cost, p95 latency, cache hit rate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.infra.cost.tracker import get_cost_tracker  # noqa: E402


def main():
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
    out_json.write_text(json.dumps({
        "total_usd": total_usd,
        "total_vnd": total_vnd,
        "cache_hit_rate_pct": cache_hit_rate,
        "p95_latency_s": p95_latency,
        "summary": summary
    }, indent=2), encoding="utf-8")

    print(f"Dashboard generated: {out_md}")

if __name__ == "__main__":
    main()
