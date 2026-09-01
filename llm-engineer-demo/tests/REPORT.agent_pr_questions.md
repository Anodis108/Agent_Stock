# Báo cáo kiểm thử — `tests/QUESTIONS.agent_pr.md`

**Ngày chạy:** 2026-09-01
**Môi trường:** Docker Compose (`vn-stock-api` + `vn-stock-postgres`), Langfuse Docker riêng, KHÔNG có Qdrant (`--profile rag` không bật)
**Cách chạy:** gọi thật qua `POST /pr/ask`, `/pr/price`, `/pr/approve`, `/pr/ask/evaluate` trên `http://localhost:8000` — không mock, dùng OpenAI key thật.
**Số câu chạy:** 109/109 (bỏ mục 6, 7, 8 — lý do ở dưới), tự động qua script, ghi log JSONL từng câu.

---

## 1. Tóm tắt nhanh

| Chỉ số | Kết quả |
|---|---|
| Tổng số lời gọi | 109 |
| HTTP 200 | 100 |
| HTTP lỗi có chủ đích đúng (422 thiếu `thread_id`) | 1 |
| HTTP lỗi KHÔNG mong muốn | 5 (2× 400 guardrail quá chặt, 3× 503 recursion-limit crash) |
| Mục không test được (tính năng chưa build) | Mục 6, 7, 8 |

**Đánh giá tổng quan: Hệ thống chạy đúng luồng chính (happy path) rất tốt — 5 worker, HITL, memory ngắn hạn, cache trong phiên đều hoạt động đúng thiết kế. Nhưng có 1 bug nghiêm trọng (crash khi mã không hợp lệ) và 1 vấn đề chất lượng đáng kể (EvalAgent gần như không bao giờ được kích hoạt) cần sửa trước khi coi là ổn định.**

---

## 2. Bug và vấn đề tìm thấy (xếp theo mức độ nghiêm trọng)

### 🔴 Nghiêm trọng — Recursion limit crash khi mã cổ phiếu không hợp lệ / mơ hồ

**Câu tái hiện:** 1.15 (`XYZABC hôm nay giảm vì sao?`), 2.12 (`Giá mã UPCOM bất kỳ hôm nay?`), 14.6 (`Tin và giá của một mã UPCOM bất kỳ hôm nay.`)

**Hiện tượng:** API trả `HTTP 503` với message:
```
Không lấy được dữ liệu: Recursion limit of 28 reached without hitting a stop condition.
```

**Nguyên nhân gốc (đã xác nhận bằng cách gọi trực tiếp graph, không qua HTTP):**
`vnstock` trả lỗi `"Invalid symbol. Your symbol format is not recognized!"` cho mã không tồn tại. `PriceAgent` bắt lỗi đúng cách, trả về `Agent_Output(last=0, pct_change=None, source="Lỗi vnstock ...")` — không crash ở tầng này.

Vấn đề nằm ở `coordinator._pending_gather()` (`app/agent_pr/supervisor_agent/nodes.py`): nó chỉ kiểm tra "đã có `price` hợp lệ chưa" (`_has_price()` yêu cầu `last > 0` và `pct_change is not None`), **không phân biệt được "chưa crawl" với "đã crawl nhưng thất bại vĩnh viễn"**. Vì `last` vẫn luôn `0`, coordinator cứ nghĩ "chưa đủ dữ liệu" và gọi lại `price_agent`/`news_agent` — lặp vô hạn cho tới khi chạm `recursion_limit=28`, rồi toàn bộ request crash với HTTP 503 khó hiểu với người dùng.

**So với spec:** Câu 1.15 yêu cầu rõ *"Mã không tồn tại HOSE/HNX/UPCOM — parse xong phải báo không hợp lệ, không bịa"* — hệ thống hiện tại không làm được điều này, nó crash thay vì trả lời gọn gàng.

**Đề xuất sửa:** Thêm cờ đếm số lần thử/agent trong state (hoặc kiểm tra `source` bắt đầu bằng `"Lỗi"` để coi là "đã thử và thất bại", không retry lại) trong `_pending_gather()`.

---

### 🟠 Đáng kể — EvalAgent hầu như không bao giờ được kích hoạt

**Câu tái hiện:** Toàn bộ mục 4 (4.1–4.7), 13.4b

**Hiện tượng:** Tất cả 8 câu hỏi rõ ràng cần chấm "tin có khớp giá không / có đáng tin không" (đã có đủ Price + News) đều trả về `used_agents` **không có `"eval"`**, và `eval_detail` luôn rỗng `""`.

**Nguyên nhân:** `_sanitize_plan()` (`supervisor_agent/nodes.py:118`) chỉ bật `use_eval` nếu **LLM coordinator tự chủ động gọi tool `need_eval`** (không tự động bật dù đủ điều kiện price+news). Prompt `_PLAN_SYSTEM` có ghi *"need_eval = chấm tin vs giá — CHỈ khi cũng need_price VÀ need_news"* nhưng đây chỉ là điều kiện cần chứ không hướng dẫn model rõ **khi nào nên chủ động gọi** — kết quả là model gần như không bao giờ chọn tool này trong thực tế test.

**So với spec:** Mục 4 toàn bộ đặc tả hành vi EvalAgent (sentiment, đủ bằng chứng, khớp giá-tin) — nhưng tính năng cốt lõi này gần như chết trong luồng thực tế.

**Đề xuất sửa:** Làm rõ hơn trong `_PLAN_SYSTEM` các cụm từ kích hoạt (`"đáng tin"`, `"khớp"`, `"vì sao"`, `"tại sao"`) nên tự động kèm `need_eval`, hoặc cân nhắc bỏ điều kiện "LLM phải tự chọn" và tự động bật `use_eval` khi có đủ price+news và câu hỏi thuộc dạng "tại sao"/nguyên nhân.

---

### 🟡 Trung bình — Câu hỏi thị trường chung bị gán nhầm vào mã mặc định `HPG`

**Câu tái hiện:** 1.8, 1.9, 1.10, 1.11, 3.7

**Hiện tượng:** Các câu không nêu mã cụ thể ("VN-Index hôm nay thế nào?", "Thị trường hôm nay ra sao?", "Fed tăng lãi suất ảnh hưởng thế nào tới VN?", "HPG và FPT mã nào mạnh hơn?") đều bị coordinator gán `symbol=HPG` (giá trị fallback hardcode trong `_make_plan`/`_plan_from_tool_calls`: `symbol=hint or "HPG"`), rồi trả lời né tránh kiểu "chưa đủ lịch sử để..." thay vì xử lý đúng ý đồ câu hỏi.

**So với spec:** Mục 1 yêu cầu rõ *"không ép 1 mã"* (1.8), *"không gộp thành 1 mã"* khi có 2 ticker (1.10). Hiện tại hệ thống chỉ đơn giản không trả lời được, không hẳn "gộp sai" nhưng cũng không đúng ý — trả lời mơ hồ "chưa đủ lịch sử" cho mọi trường hợp này.

**Đề xuất sửa:** Đây là hạn chế kiến trúc thật (hệ thống chỉ được thiết kế cho 1-mã-1-lượt) — cần category riêng "không match mã cụ thể" trong plan, hoặc chấp nhận giới hạn này và document rõ trong README thay vì để trả lời mơ hồ.

---

### 🟡 Trung bình — Guardrail chặn cứng câu ngoài phạm vi bằng HTTP 400 thay vì trả lời lịch sự

**Câu tái hiện:** 1.13 (`Hello, bạn làm được gì?`), 1.14 (`Giải thích giúp tôi thuật ngữ P/E.`)

**Hiện tượng:** Cả 2 câu bị `guardrail_input` chặn cứng, trả `HTTP 400 {"error":"input_rejected","reason":"out_of_scope"}` — không có answer nào cả.

**So với spec:** Câu 1.13/1.14 mô tả *"không bật crawl giá/tin nếu plan không cần"* / *"câu kiến thức, không phải hỏi–đáp mã"* — ngụ ý hệ thống nên **trả lời được** (không crawl), không phải **từ chối hoàn toàn**. Việc chặn "Hello" như injection/out-of-scope có thể làm trải nghiệm người dùng thật kém — một chatbot chuyên biệt vẫn nên chào lại hoặc nói rõ phạm vi thay vì trả lỗi HTTP thô.

**Đây có thể là chủ đích thiết kế** (guardrail chặt để tránh lạc đề) — không chắc chắn là bug, nhưng đáng để xác nhận lại với đội sản phẩm.

---

### 🟢 Nhỏ — Long-term memory: recall đúng cơ chế nhưng LLM plan không tận dụng để suy mã

**Câu tái hiện:** 11.alice1 → 11.alice2

**Hiện tượng:** Sau khi lưu "Tôi chỉ đầu tư bluechip ngân hàng, ưu tiên VCB." (user `alice`), câu hỏi tiếp theo "Gợi ý mã phù hợp với tôi." (không nêu mã) lại trả lời về `HPG` thay vì gợi ý `VCB` hay nhóm ngân hàng.

**Đã xác nhận qua debug trực tiếp:** `memory.recall_long_term()` hoạt động đúng — fact được lưu và đọc lại chính xác qua cơ chế fallback in-memory (Qdrant không chạy trong môi trường test). Vấn đề nằm ở tầng LLM: `_make_plan()` có đưa `memories` vào prompt (`"Đã biết về user:\n- ..."`) nhưng coordinator LLM không dùng nó để suy ra mã khi câu hỏi không có ticker rõ ràng — vẫn fallback về `HPG` mặc định.

**Đối chứng cách ly giữa user (đúng):** Không test riêng round-trip bob vs alice trong lần chạy này do cả hai đều fallback cùng `HPG` (không đủ để phân biệt) — cần retest với câu hỏi khác biệt rõ hơn.

---

## 3. Những gì hoạt động đúng (xác nhận bằng dữ liệu thật)

| Hạng mục | Bằng chứng |
|---|---|
| **Cache trong phiên (không crawl lại cùng mã)** | 2.9a → 2.9b: trace bỏ hẳn bước "crawl price_agent" ở lượt 2, dùng `price` đã có trong state |
| **Cache tin trong phiên** | 3.12a → 3.12b: trace bỏ bước fetch tin, chỉ còn "DB đã có news — dùng luôn" |
| **HITL đúng luồng approve/reject** | Câu retry với mã `MSN`: crawl → 10 lệnh pending → `status=pending_approval` → approve 1 lệnh còn 9 → reject 1 lệnh khác vẫn còn 9 (độc lập đúng) — DB **không COMMIT** trước khi duyệt |
| **Subset worker đúng theo câu hỏi** | 13.1 "chỉ giá" → `used_agents=[price, synth]`; 13.2 "chỉ liệt kê headline" → `[news, synth]`; 13.3 "chỉ đọc DB" → `[db, synth]` — không bật thừa Eval khi chỉ có Price (4.8-no-eval xác nhận) |
| **HTTP 422 khi thiếu `thread_id`** | 10.D đúng như spec |
| **Response đủ field observability** | `/pr/ask` trả đủ `answer, trace, used_agents, plan_reasoning, thread_id, user_id` |
| **`/pr/price` độc lập, không qua hub** | 15.2 chạy 3.04s (rất nhanh so với `/pr/ask` ~15-30s), không lỗi |
| **`/pr/ask/evaluate` hoạt động, LLM-judge phát hiện đúng vấn đề** | Chấm câu "Tại sao HPG giảm?" khi giá thực tế không giảm → `task_success.success=false` với lý do hợp lý; `trajectory` đủ 4 chỉ số |
| **Phủ đa sàn (HOSE/HNX/UPCOM)** | 14.5 (SHS - HNX) và các mã ngoài whitelist test (MSN, DGC) đều chạy được, không whitelist cứng |
| **Tracing Langfuse (mục sửa trước đó)** | Không kiểm tra lại trong lần chạy này — đã xác nhận riêng ở phần trước của phiên làm việc |

---

## 4. Mục không test được — tính năng chưa build

QUESTIONS.agent_pr.md tham chiếu một kiến trúc mở rộng hơn nhiều so với code hiện tại (khớp `swarm-handoff-map_6.html`, có vẻ là design doc cho giai đoạn sau):

- **Mục 6 — DocumentAgent (PDF BCTC):** không có route/agent nào xử lý PDF trong `app/agent_pr`.
- **Mục 7 — Swarm dị chủng (ScoutAgent, RenderAgent/Playwright, ApiAgent, StealthAgent):** không tồn tại — `PriceAgent`/`NewsAgent` hiện tại gọi thẳng `vnstock`/CafeF Ajax, không có cơ chế handoff theo loại URL.
- **Mục 8 — ContentRouter + Sink Router riêng biệt:** không tồn tại như 2 tầng độc lập — `DBAgent` gộp việc phân loại + ghi vào 1 nơi.

Đây **không phải bug** — README.agent_pr.md mô tả đúng 5 worker + 3 endpoint đã build, khớp hoàn toàn với code thật. QUESTIONS.md có vẻ được viết trước hoặc song song với 1 roadmap rộng hơn.

---

## 5. Danh sách đầy đủ theo mục (tóm tắt kết quả)

| Mục | Số câu chạy | Kết quả |
|---|---|---|
| 1. Coordinator | 16 | 13 OK, 2× 400 (guardrail), 1× 503 (recursion crash) |
| 2. PriceAgent | 18 | 17 OK, 1× 503 (mã UPCOM mơ hồ) |
| 3. NewsAgent | 13 | Tất cả OK — cache đúng, match tên công ty đúng, tin không match mã → "tin chung" đúng |
| 4. EvalAgent | 8 | Tất cả HTTP 200, nhưng **Eval không kích hoạt ở bất kỳ câu nào** (xem mục 2 báo cáo) |
| 5. DBAgent + HITL | 12 (+ 4 câu debug bổ sung để xác nhận HITL) | Đọc DB OK; HITL approve/reject xác nhận đúng qua câu bổ sung mã MSN |
| 9. SynthesisAgent | 4 | OK, có cấu trúc 3 khối, có trace đầy đủ |
| 10. Short-term memory | 10 | Tất cả đúng — kịch bản A/B/C/D đều khớp spec, kể cả 422 |
| 11. Long-term memory | 7 (+ 1 debug trực tiếp module) | Recall/store cơ chế đúng, nhưng LLM plan không tận dụng để suy mã (xem mục 2) |
| 12. HITL ghi đồng thời | 2 | OK — pending_writes trả về đa loại (`kind`) |
| 13. Plan subset worker | 7 | Đúng theo spec, trừ 13.4b thiếu Eval (cùng bug mục 4) |
| 14. Sàn/mã phủ phạm vi | 7 | 6 OK, 1× 503 (mã UPCOM mơ hồ, cùng bug mục 1) |
| 15. API & observability | 4 | Tất cả đúng — field đủ, `/pr/price` nhanh & độc lập, `/pr/ask/evaluate` hoạt động tốt |

---

## 6. Khuyến nghị ưu tiên sửa

1. **[Ưu tiên cao]** Chặn vòng lặp vô hạn khi crawl thất bại liên tục (mã không hợp lệ) — tránh crash 503, trả lời "mã không hợp lệ" như spec yêu cầu.
2. **[Ưu tiên cao]** Sửa việc EvalAgent không được kích hoạt — đây là tính năng cốt lõi của kiến trúc (chấm khớp giá-tin) nhưng gần như vô hiệu trong thực tế.
3. **[Ưu tiên trung bình]** Cải thiện xử lý câu hỏi không có mã cụ thể (thị trường chung, so sánh nhiều mã) — hiện tại fallback về HPG gây trả lời sai ý.
4. **[Cần xác nhận với người phụ trách]** Guardrail có nên chặn cứng câu ngoài phạm vi (chào hỏi, khái niệm tài chính) hay nên trả lời nhẹ nhàng — tùy chủ đích sản phẩm.

---

## 7. Ghi chú phương pháp

- Dữ liệu test dùng key OpenAI thật (`gpt-4o-mini`), không mock — chi phí LLM thật đã phát sinh khi chạy 109 câu.
- Một số câu bị ảnh hưởng bởi dữ liệu đã có sẵn trong SQLite từ các lần test trước (`data/agent_pr.sqlite3`), ví dụ giá HPG luôn hiển thị "không đổi 0%" vì đó là dữ liệu thật tại thời điểm test — không phải bug.
- Qdrant không chạy trong lần test này (`docker compose --profile rag` không bật) — long-term memory chạy qua fallback in-memory, kết quả có thể khác khi có Qdrant thật.
- Log chi tiết từng câu (request/response đầy đủ, JSONL) được lưu tạm trong quá trình chạy nhưng không đính kèm vào repo — có thể chạy lại script để tái tạo nếu cần.
