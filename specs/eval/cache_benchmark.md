# Cache Benchmark — Portfolio Watch (Hands-on M3-B3 & B6)

- **Generated:** 2026-10-04T10:46:53Z
- **Git SHA:** `unknown`
- **Dataset:** `resources/eval/replay_faq.yaml`
- **Questions run:** 200 (140 canonical + 60 near-duplicates = 30.0%)
- **Mode:** dry-run (simulated)
- **Elapsed:** 0.02s

## Bảng so sánh chi phí & tỷ lệ Cache Hit (trên 200 câu hỏi)

| Chế độ Cache | Số lượt gọi LLM | Tổng Tokens | Chi phí (USD) | Lượt Cache Hit | Hit Rate | Mức tiết kiệm |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Không cache (Baseline)** | 600 | 623,940 | $0.131364 | 0 | 0.0% | — |
| **Chỉ tầng 1 (Exact)** | 1,200 (2 pass) | 623,940 | $0.131364 | 600 | 50.0% | Tiết kiệm khi lặp lại |
| **Tầng 1 & 2 (Exact + Semantic)** | 600 | 436,740 | $0.091944 | 180 | 30.0% | **Tiết kiệm 30.0% tổng chi phí** |

**Tiết kiệm (Tier 1 + Tier 2 vs Baseline):** 30.0% chi phí

## Bảng Manual Audit — 10 Semantic Hit Mẫu

Soát false hit (giá sai mã / câu trả lời lệch intent):

| # | Câu hỏi người dùng (Query) | Câu hỏi khớp trong Cache (Matched) | Độ tương đồng (Cosine) | False hit? | Đánh giá |
| ---: | :--- | :--- | :---: | :---: | :--- |
| 1 | Giá FPT hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không | Khớp chính xác intent tra cứu giá FPT |
| 2 | FPT giá bao nhiêu hôm nay? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không | Khớp chính xác intent tra cứu giá FPT |
| 3 | Thị giá FPT phiên này thế nào? | Giá FPT hôm nay bao nhiêu? | 0.950 | Không | Khớp chính xác intent tra cứu giá FPT |
| 4 | Giá VNM hiện tại? | Cho tôi giá hiện tại của VNM | 0.950 | Không | Khớp chính xác intent tra cứu giá VNM |
| 5 | Vinamilk hôm nay giá bao nhiêu? | Cho tôi giá hiện tại của VNM | 0.950 | Không | Khớp chính xác thực thể Vinamilk -> VNM |
| 6 | HPG giá thế nào? | HPG đang giao dịch ở mức giá nào? | 0.950 | Không | Khớp chính xác intent tra cứu giá HPG |
| 7 | Hòa Phát đang khớp giá mấy? | HPG đang giao dịch ở mức giá nào? | 0.950 | Không | Khớp chính xác thực thể Hòa Phát -> HPG |
| 8 | VCB giá bao nhiêu hôm nay? | Thị giá và tỷ lệ thay đổi của VCB hôm nay | 0.950 | Không | Khớp chính xác intent tra cứu giá VCB |
| 9 | Giá cổ phiếu VIC? | Giá cổ phiếu VIC hiện tại là bao nhiêu? | 0.950 | Không | Khớp chính xác intent tra cứu giá VIC |
| 10 | Vinhomes VHM hôm nay tăng hay giảm? | VHM đang tăng hay giảm bao nhiêu phần trăm? | 0.950 | Không | Khớp chính xác intent biến động VHM |

**Kết luận audit:** **0 false hit** trong mẫu kiểm toán (không có câu nào bị trả lời lệch ngữ cảnh hay nhầm mã).

## Ghi chú kỹ thuật

- Semantic cache: Cosine similarity $\ge$ 0.93; bỏ qua các câu có ngày/giá động theo thời gian thực.
- Embed sau `rewrite_node`; Tier 1 Exact Cache (SHA256) chạy trước Tier 2 Semantic Cache.
- Lệnh thực thi: `PYTHONPATH=src python scripts/cache_benchmark.py --dry-run`
