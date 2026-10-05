# Cost Baseline — Portfolio Watch (Phase 7–8)

- **Generated:** 2026-10-04T10:46:46Z
- **Git SHA:** `unknown`
- **Dataset:** `resources/eval/replay_faq.yaml` (200 FAQ, ~30% near-duplicate)
- **Mode:** dry-run (no LLM)
- **Passes:** 1
- **Questions run:** 200
- **Elapsed:** 0.0s

## Tổng hợp

| Metric | Value |
| :--- | :--- |
| LLM requests | 600 |
| Total tokens | 623,940 |
| Total cost (USD) | $0.131364 |
| Total cost (VND) | 3,337 |
| Cache hits | 0 (rate 0%) |

## Theo feature

| Feature | Requests | Tokens | Cost USD |
| :--- | ---: | ---: | ---: |
| chat_replay | 600 | 623,940 | $0.131364 |

## Ghi chú

- Baseline này đo **trước cache** (`cache_hit=false` trên mọi request).
- So sánh sau khi bật cache: `--with-cache tier1`.
- Chạy đầy đủ: `PYTHONPATH=src python scripts/cost_baseline.py` (cần API key).
