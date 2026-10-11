# Cache Benchmark — Portfolio Watch (Phase 9)

- **Generated:** 2026-10-05T15:28:37Z
- **Git SHA:** `31a08d3`
- **Dataset:** `resources/eval/replay_faq.yaml`
- **Questions run:** 10
- **Mode:** dry-run (simulated)
- **Elapsed:** 0.0s

## Bảng so sánh cost (cùng tập replay)

| Chế độ | LLM requests | Total tokens | Cost USD | Cache hits | Hit rate |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Không cache | 30 | 31,140 | $0.006534 | 0 | 0% |
| Chỉ tầng 1 (exact) | 60 | 31,140 | $0.006534 | 30 | 50% |
| Tầng 1 + 2 (exact + semantic) | 30 | 21,330 | $0.004495 | 9 | 30% |

**Tiết kiệm (tier1+tier2 vs none):** 31.2% cost

## Manual audit — 10 semantic hit mẫu

Soát false hit (giá sai mã / câu trả lời lệch intent):

| # | Query | Matched | Similarity | False hit? |
| ---: | :--- | :--- | ---: | :--- |
| 1 | Giá FPT hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không |
| 2 | FPT giá bao nhiêu hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không |
| 3 | Thị giá FPT phiên này thế nào? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không |

**Kết luận audit:** 0 false hit nghiêm trọng trong mẫu dry-run/simulated.

## Ghi chú

- Semantic cache: cosine ≥ 0.93; bỏ qua câu có ngày/giá động.
- Embed sau `rewrite_node`; tier 1 exact chạy trước tier 2.
- Chạy: `PYTHONPATH=src python scripts/cache_benchmark.py --dry-run`
