# Cost Baseline — Portfolio Watch (Phase 7–8)

- **Generated:** 2026-10-05T15:28:45Z
- **Git SHA:** `31a08d3`
- **Dataset:** `resources/eval/replay_faq.yaml` (10 FAQ, ~30% near-duplicate)
- **Mode:** dry-run (no LLM)
- **Passes:** 1
- **Questions run:** 10
- **Elapsed:** 0.0s

## Tổng hợp

| Metric | Value |
| :--- | :--- |
| LLM requests | 30 |
| Total tokens | 31,140 |
| Total cost (USD) | $0.006534 |
| Total cost (VND) | 166 |
| Cache hits | 0 (rate 0%) |

## Theo feature

| Feature | Requests | Tokens | Cost USD |
| :--- | ---: | ---: | ---: |
| chat_replay | 30 | 31,140 | $0.006534 |

## Ghi chú

- Baseline này đo **trước cache** (`cache_hit=false` trên mọi request).
- So sánh sau khi bật cache: `--with-cache tier1`.
- Chạy đầy đủ: `PYTHONPATH=src python scripts/cost_baseline.py` (cần API key).
