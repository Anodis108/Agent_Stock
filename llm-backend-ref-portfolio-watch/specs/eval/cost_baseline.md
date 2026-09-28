# Cost Baseline — Portfolio Watch (Phase 7–8)

- **Generated:** 2026-09-28T15:00:39Z
- **Git SHA:** `792fa34`
- **Dataset:** `resources/eval/replay_faq.yaml` (50 FAQ, ~30% near-duplicate)
- **Mode:** exact cache tier1 (2 passes) dry-run
- **Passes:** 2
- **Questions run:** 5
- **Elapsed:** 0.0s

## Tổng hợp

| Metric | Value |
| :--- | :--- |
| LLM requests | 30 |
| Total tokens | 15,540 |
| Total cost (USD) | $0.003249 |
| Total cost (VND) | 83 |
| Cache hits | 15 (rate 50%) |

## Theo feature

| Feature | Requests | Tokens | Cost USD |
| :--- | ---: | ---: | ---: |
| chat_replay | 30 | 15,540 | $0.003249 |

## Ghi chú

- Chạy **2 pass** cùng dataset; pass 2 kỳ vọng `cache_hit > 0` trên câu trùng.
- Exact cache key: `prompt_name` + `prompt_version` + `model` + `normalized_question`.
- Chạy: `PYTHONPATH=src python scripts/cost_baseline.py --with-cache tier1`.
