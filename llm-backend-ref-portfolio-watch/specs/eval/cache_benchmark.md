# Cache Benchmark — Portfolio Watch (Phase 9)

- **Generated:** 2026-09-28T15:03:47Z
- **Git SHA:** `792fa34`
- **Dataset:** `resources/eval/replay_faq.yaml`
- **Questions run:** 50
- **Mode:** dry-run (simulated)
- **Elapsed:** 0.01s

## Bảng so sánh cost (cùng tập replay)

| Chế độ | LLM requests | Total tokens | Cost USD | Cache hits | Hit rate |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Không cache | 150 | 155,940 | $0.032814 | 0 | 0% |
| Chỉ tầng 1 (exact) | 300 | 155,940 | $0.032814 | 150 | 50% |
| Tầng 1 + 2 (exact + semantic) | 150 | 109,140 | $0.022959 | 45 | 30% |

**Tiết kiệm (tier1+tier2 vs none):** 30.0% cost

## Manual audit — 10 semantic hit mẫu

Soát false hit (giá sai mã / câu trả lời lệch intent):

| # | Query | Matched | Similarity | False hit? |
| ---: | :--- | :--- | ---: | :--- |
| 1 | Giá FPT hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không |
| 2 | FPT giá bao nhiêu hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không |
| 3 | Giá VNM hiện tại? | Cho tôi giá hiện tại của VNM | 0.950 | Không |
| 4 | HPG giá thế nào? | HPG đang giao dịch ở mức giá nào? | 0.950 | Không |
| 5 | Tin FPT mới nhất? | Tin gần đây về FPT là gì? | 0.950 | Không |
| 6 | Tin HPG hôm nay? | Có tin gì mới về HPG không? | 0.950 | Không |
| 7 | VNM tin tức? | Tin tức VNM hôm nay | 0.950 | Không |
| 8 | FPT hôm nay tăng hay giảm? | FPT tăng hay giảm hôm nay? | 0.950 | Không |
| 9 | So sánh VNM với HPG | So sánh VNM và HPG tuần này | 0.950 | Không |
| 10 | FPT vs VNM giá hôm nay | So sánh giá FPT và VNM hôm nay | 0.950 | Không |

**Kết luận audit:** 0 false hit nghiêm trọng trong mẫu dry-run/simulated.

## Ghi chú

- Semantic cache: cosine ≥ 0.93; bỏ qua câu có ngày/giá động.
- Embed sau `rewrite_node`; tier 1 exact chạy trước tier 2.
- Chạy: `PYTHONPATH=src python scripts/cache_benchmark.py --dry-run`
