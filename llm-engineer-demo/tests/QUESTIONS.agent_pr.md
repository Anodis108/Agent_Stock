# Bộ câu hỏi khai thác agent_pr (multiagent hoàn thiện)

Chỉ bám `README.agent_pr.md` và `swarm-handoff-map_6.html`. Mỗi câu là thứ user gõ vào hệ thống sau khi multiagent hoàn thiện; cột **Cần thấy** là chức năng cần bị kích hoạt, không phải đáp án.

Mã test mặc định trong tài liệu: **HPG, VNM, FPT, VCB**. Sàn: HOSE / HNX / UPCOM, không whitelist.

Không dùng pytest để “chạy app”. File này là kịch bản hỏi tay / qua `POST /pr/ask`.

---

## Cách dùng

1. Gửi lần lượt vào `POST /pr/ask` với `{ "question": "..." }`.
2. Khi cần nhớ phiên: thêm `thread_id`. Khi cần nhớ dài hạn: thêm `user_id`.
3. Sau mỗi câu, đối chiếu `used_agents`, `plan_reasoning`, `trace` — worker nào được bật, worker nào **không** được bật.
4. Câu đánh dấu **API** không phải chat thuần: gọi đúng endpoint.

Thứ tự worker đúng thiết kế: **Price / News / DB song song → Eval (khi đã có tin + giá) → Synthesis (khi đã có Eval) → chỉ Coordinator nói với user.**

---

## 1. Coordinator — parse ticker, intent, lập plan

Hub phải tách mã, đoán intent, chọn đúng worker; không tự crawl / không tự chấm tin.

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 1.1 | Tại sao giá HPG giảm hôm nay? | Parse `HPG`, intent nguyên nhân biến động → bật đủ Price + News + DB → Eval → Synthesis. Đây là câu vàng của sơ đồ. |
| 1.2 | Tại sao HPG giảm? | Cùng intent, không có “hôm nay” — vẫn đủ worker. |
| 1.3 | HPG hôm nay thế nào? | Intent tổng quan, không chỉ “tại sao”. |
| 1.4 | Hòa Phát hôm nay giảm vì sao? | Tách ticker từ **tên công ty**, không có mã. |
| 1.5 | Vinamilk đang ra sao? | Tên công ty → `VNM`. |
| 1.6 | FPT | Câu cực ngắn; hub tự hỏi đủ worker (tương đương body `{"symbol":"FPT"}`). |
| 1.7 | Cho tôi biết về VCB. | Intent rộng; plan phải nêu lý do bật từng worker. |
| 1.8 | VN-Index hôm nay thế nào? | Không phải 1 mã CP — hub không gán nhầm 1 ticker, hoặc nói rõ không match mã. |
| 1.9 | Thị trường hôm nay ra sao? | Tin vĩ mô / tin chung, không ép 1 mã. |
| 1.10 | HPG và FPT mã nào mạnh hơn hôm nay? | Hai ticker — plan không gộp thành 1 mã. |
| 1.11 | So sánh Hòa Phát với FPT tuần này. | Hai tên công ty. |
| 1.12 | Cổ phiếu thép hôm nay thế nào? | Tin ngành, có thể match **nhiều mã** (hợp lệ, không phải lỗi). |
| 1.13 | Hello, bạn làm được gì? | Không có ticker — không bật crawl giá/tin nếu plan không cần. |
| 1.14 | Giải thích giúp tôi thuật ngữ P/E. | Câu kiến thức, không phải hỏi–đáp mã. |
| 1.15 | XYZABC hôm nay giảm vì sao? | Mã không tồn tại HOSE/HNX/UPCOM — parse xong phải báo không hợp lệ, không bịa. |

**API — chỉ mã, không câu hỏi**

```json
{"symbol": "HPG"}
```

Hub tự sinh câu phân tích đủ worker.

---

## 2. PriceAgent — giá, % biến động, cache 15 phút, Swarm giá

PriceAgent chỉ tìm giá + tính %; **không giải thích nguyên nhân, không nói với News/DB**.

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 2.1 | Giá HPG hiện tại là bao nhiêu? | Chỉ Price (và DB đọc độ mới nếu plan tắt News). |
| 2.2 | HPG hôm nay tăng hay giảm bao nhiêu % so với đóng cửa hôm qua? | Tính % đúng công thức sơ đồ: `(close − prev_close) / prev_close`. |
| 2.3 | HPG đóng cửa phiên trước bao nhiêu? | `prev_close`. |
| 2.4 | VNM đang tăng hay giảm? | Cùng pipeline, mã khác. |
| 2.5 | FPT biến động trong phiên hôm nay ra sao? | Intraday / % trong phiên. |
| 2.6 | VCB giá real-time lúc này? | Ưu tiên nguồn API (SSI/TCBS `/api/`, JSON) — **ApiAgent**. |
| 2.7 | Lấy bảng giá HPG trên SSI iBoard. | Trang JS-nặng → **RenderAgent** (Playwright) nếu Scout thấy SPA rỗng. |
| 2.8 | Giá HPG trên TCBS. | RenderAgent hoặc ApiAgent tùy path. |
| 2.9 | Hỏi giá HPG lần nữa ngay sau câu 2.1 (cùng `thread_id`). | Giá **cùng mã không crawl lại** (cache phiên / DB tươi < 15 phút). |
| 2.10 | Đợi > 15 phút rồi hỏi lại: Giá HPG còn đúng không? | DB cũ → gọi Swarm crawl mới. |
| 2.11 | Một mã HNX (ví dụ CEO hoặc SHS, tùy lúc test): Giá … hôm nay? | Sàn HNX, không whitelist. |
| 2.12 | Một mã UPCOM: Giá … hôm nay? | Sàn UPCOM. |
| 2.13 | HPG tăng vì sao? | Vẫn bật Price (hướng tăng, không chỉ giảm). |
| 2.14 | HPG đứng giá hôm nay phải không? | % ≈ 0 — Price vẫn chạy, Eval có thể trung lập. |

**API — giá, không qua hub, không cần OpenAI**

```http
POST /pr/price
{"symbol": "HPG"}
```

Lặp với `VNM`, `FPT`, `VCB`.

---

## 3. NewsAgent — chỉ search tin, match mã, không chấm tốt/xấu

NewsAgent crawl → ContentRouter → Sink Router match ticker. Báo cáo tin thô. **Không sentiment.**

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 3.1 | Tin tức HPG 24 giờ qua. | News + match `HPG` / Hòa Phát → **Tin theo mã**. |
| 3.2 | Có tin gì về Hòa Phát hôm nay? | Match bằng tên công ty. |
| 3.3 | Tóm tắt tin VNM trên CafeF. | Nguồn `cafef.vn`, ScoutAgent HTML. |
| 3.4 | Tin FPT trên Vietstock. | Nguồn `vietstock.vn`. |
| 3.5 | Có bài nào nói về HPG trên cả CafeF và Vietstock không? | Hai domain, Scout tự chia. |
| 3.6 | Tin ngành ngân hàng hôm nay. | Có thể match **nhiều mã** (VCB và mã khác) — hợp lệ. |
| 3.7 | Fed tăng lãi suất ảnh hưởng thế nào tới thị trường Việt Nam? | Không match mã → **Tin chung**, không mất dữ liệu. |
| 3.8 | Lịch họp ĐHĐCĐ HPG. | Tin trung lập về sự kiện — News trả thô, Eval mới gắn “trung lập”. |
| 3.9 | Khối ngoại có bán ròng HPG không? | Tin có từ khóa tiêu cực; News **không** được tự kết luận tốt/xấu. |
| 3.10 | Có khuyến nghị mua FPT gần đây không? | Từ khóa tích cực — vẫn để Eval chấm. |
| 3.11 | Tin HPG tuần này, không chỉ 24h. | Cửa sổ thời gian khác 24h mặc định. |
| 3.12 | Cùng `thread_id`, hỏi lại tin HPG. | Tin cùng mã **không crawl lại**. |

Đối chiếu tay: [Simplize HPG](https://simplize.vn/co-phieu/HPG), [CafeF HPG](https://cafef.vn/du-lieu/hose/hpg-cong-ty-co-phan-tap-doan-hoa-phat.chn).

---

## 4. EvalAgent — sentiment, đủ bằng chứng, giá khớp tin

Eval **không crawl, không ghi DB**. Chỉ chạy khi hub đã có tin + giá.

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 4.1 | Tại sao HPG giảm hôm nay? Tin đó có đáng tin không? | Sentiment từng bài + **đủ bằng chứng?** (nguồn, số bài, cửa sổ 24h). |
| 4.2 | Giá HPG giảm như vậy thì tin tức có khớp không? | Nhánh **khớp**: giá giảm + tin tiêu cực. |
| 4.3 | HPG giảm nhưng tin toàn tích cực thì sao? | (Ngày lệch, hoặc giả lập) nhánh **lệch** — Eval phải báo mâu thuẫn, không bịa nguyên nhân. |
| 4.4 | Chấm từng tin VNM hôm nay: tốt, xấu hay trung lập? | Ba nhãn: tiêu cực (xả hàng, bán ròng, giảm sàn, cắt lỗ) / tích cực (tăng trưởng, lợi nhuận, khuyến nghị mua) / trung lập (ĐHĐCĐ, lịch sự kiện). |
| 4.5 | Chỉ có 1 bài về HPG thì có đủ để kết luận không? | Đủ bằng chứng = không. |
| 4.6 | FPT tăng, tin trung lập hết — có giải thích được không? | Eval: không đủ / không khớp; Synthesis không bịa. |
| 4.7 | So tin xấu và tin tốt của VCB hôm nay, bên nào chiếm ưu? | Tổng hợp sentiment, không crawl thêm. |

Câu **không** được kích Eval: “Giá HPG là bao nhiêu?” (không có tin) — `used_agents` không có Eval.

---

## 5. DBAgent — đọc tự động, ghi bắt buộc HITL, sub-swarm schema

Ba sub-agent: `PriceDataSub` (OHLCV, khóa symbol+ts), `NewsDataSub` (title, url, published_at, tickers[]), `SymbolMetaSub` (HPG ↔ Hòa Phát Group). Đọc: auto. Ghi/sửa: người duyệt rồi mới Sink Router COMMIT; từ chối → chỉ log.

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 5.1 | 5 phiên gần nhất của HPG trong DB ra sao? | Đọc `PriceDataSub`, không HITL. |
| 5.2 | Lịch sử giá VNM tuần trước trong hệ thống. | Đọc time-series. |
| 5.3 | Hệ thống đang lưu những tin nào về FPT? | Đọc `NewsDataSub`. |
| 5.4 | HPG tên công ty đầy đủ là gì? Mã có hợp lệ không? | `SymbolMetaSub`. |
| 5.5 | Lưu tin HPG vừa crawl vào DB. | Soạn INSERT → **HITL hiện diff** → Duyệt → COMMIT **Tin theo mã**. |
| 5.6 | (Cùng luồng 5.5) Người chọn **Từ chối**. | Không ghi DB, chỉ log; báo cáo hub: từ chối. |
| 5.7 | Cập nhật giá HPG mới vào DB. | Ghi giá time-series — vẫn HITL; PriceAgent **không** tự INSERT. |
| 5.8 | Sửa tin đã lưu của VCB. | Ghi/sửa = HITL bắt buộc. |
| 5.9 | Lưu bài “Fed tăng lãi suất” (không có mã). | Sau duyệt → Sink **Tin chung**. |
| 5.10 | Lưu tin ngành thép (HPG + mã khác). | `tickers[]` nhiều mã — hợp lệ. |
| 5.11 | HPG hôm nay giảm có phải đột ngột không, nhìn lịch sử DB. | Đọc 5 phiên + giá hôm nay (kết hợp Price). |

---

## 6. DocumentAgent — PDF BCTC / công bố thông tin

Pre-fetch: URL đuôi `.pdf`. Post-fetch: Content-Type PDF ngoài dự đoán. Nguồn: IR công ty, `hnx.vn` / `hsx.vn`. **Không** dùng khi chỉ hỏi bảng giá.

| # | Câu hỏi | Cần thấy |
|---|---------|----------|
| 6.1 | Báo cáo tài chính quý gần nhất của HPG nói gì? | DocumentAgent, PDF IR / HSX / HNX. |
| 6.2 | Tóm tắt BCTC năm của VNM từ file PDF công bố. | Trích text PDF (pypdf). |
| 6.3 | Công bố thông tin mới nhất của FPT trên HSX. | `hsx.vn`. |
| 6.4 | FPT có công bố gì trên HNX không? | `hnx.vn` (nếu có). |
| 6.5 | Lấy PDF cáo bạch / báo cáo thường niên VCB và tóm tắt. | Đuôi `.pdf` định tuyến trước fetch. |
| 6.6 | Trang IR Hòa Phát có file BCTC nào? | IR công ty, không phải CafeF HTML. |

---

## 7. Swarm dị chủng — handoff (gián tiếp qua câu hỏi)

User không gọi Scout/Render/Api/Stealth trực tiếp. Câu hỏi phải **ép đúng loại URL / tín hiệu**.

| # | Câu hỏi | Handoff kỳ vọng |
|---|---------|-----------------|
| 7.1 | Bảng giá HPG trên CafeF. | ScoutAgent mặc định (HTML). |
| 7.2 | Giá HPG từ API SSI. | Pre-fetch path `/api/` → **ApiAgent** (JSON, pagination, Retry-After, token). |
| 7.3 | Giá VNM từ API TCBS. | ApiAgent. |
| 7.4 | Mở bảng giá JS SSI iBoard cho FPT. | Scout thấy SPA rỗng → **RenderAgent**. |
| 7.5 | Bảng giá TCBS (web JS) của VCB. | RenderAgent. |
| 7.6 | Tải BCTC PDF HPG. | Pre-fetch `.pdf` → **DocumentAgent**. |
| 7.7 | (Site chặn bot / 403–429 lặp) Lấy tin HPG từ nguồn đang chặn. | Scout bị chặn N lần → **StealthAgent** nhận **cả domain** (proxy, pacing, header). |
| 7.8 | Scout fetch ra JSON dù URL không có `/api/`. | Post-fetch Content-Type JSON → handoff ApiAgent. |
| 7.9 | Scout fetch ra PDF dù URL không đuôi `.pdf`. | Post-fetch Content-Type PDF → DocumentAgent. |

Link mới tìm được khi crawl phải quay lại frontier (gossip) — kiểm tra bằng câu follow-up về URL/tin vừa xuất hiện, không hỏi lại từ đầu.

---

## 8. ContentRouter + Sink Router

Hai tầng sau crawl: loại nội dung rồi mới đích DB.

| # | Câu hỏi | Đích |
|---|---------|------|
| 8.1 | Giá HPG (HTML hoặc API). | ContentRouter → Html hoặc Json → Sink **Giá CP time-series**. |
| 8.2 | Tin “Khối ngoại xả hàng HPG”. | HtmlHandler → match HPG → **Tin theo mã**. |
| 8.3 | Tin vĩ mô không nêu mã. | **Tin chung**. |
| 8.4 | Tin nêu cả HPG và FPT. | Nhiều mã trong `tickers[]`. |
| 8.5 | Sitemap / trang không phải bài tin. | ContentRouter: Sitemap (không nhét vào tin theo mã). |
| 8.6 | File binary không đọc được. | Binary fallback, không mất pipeline. |

---

## 9. SynthesisAgent — câu có cấu trúc + trace

Chỉ chạy khi hub đã có Eval. Không crawl, không ghi DB, không gửi thẳng user.

| # | Câu hỏi | Câu trả lời cần có |
|---|---------|-------------------|
| 9.1 | Tại sao giá HPG giảm hôm nay? | (1) Số liệu giá từ Price (2) Nguyên nhân đã được Eval chốt (3) Bối cảnh 5 phiên DB. Tiếng Việt, nêu nguồn từng ý. |
| 9.2 | Giải thích biến động VNM hôm nay, kèm nhật ký các bước. | `trace`: parse → đợt 1 → Swarm/Router/HITL → Eval → Synthesis → Coordinator. |
| 9.3 | FPT hôm nay — tóm tắt ngắn cho người không chuyên. | Cấu trúc vẫn 3 khối, không bịa ngoài 4 báo cáo. |
| 9.4 | Nếu thiếu tin hoặc thiếu giá, hãy giải thích VCB hôm nay. | Synthesis không chạy / hub báo thiếu; không bịa. |

`trace` là nhật ký hub, không phải chat ẩn giữa worker.

---

## 10. Bộ hội thoại — short-term memory (`thread_id`)

Giữ nguyên `thread_id`. Nút **Phiên mới** = đổi `thread_id`.

### Kịch bản A — cùng mã, không crawl lại

1. Tại sao HPG giảm hôm nay?
2. % giảm chính xác là bao nhiêu? *(dùng giá đã có)*
3. Tin tiêu cực nào vừa nêu? *(dùng tin đã có)*
4. 5 phiên trước đã yếu sẵn chưa? *(dùng DB đã đọc)*

### Kịch bản B — đổi mã trong cùng phiên

1. Giá HPG hôm nay?
2. Còn FPT thì sao? *(crawl mã mới; HPG không crawl lại)*
3. So hai mã vừa hỏi.

### Kịch bản C — phiên mới quên hội thoại

1. `thread_id=sess-1`: Tôi đang theo HPG.
2. Đổi `thread_id` (Phiên mới): Mã tôi đang theo là gì?

Không được nhớ câu 1.

### Kịch bản D — server cấp uuid

Gửi `{"question":"Giá VNM?"}` không `thread_id` → response có `thread_id`; gửi tiếp cùng id thì nhớ.

---

## 11. Long-term memory (`user_id` + Qdrant `user_memory`)

Không `user_id` → không recall/store. Cần `docker compose --profile rag up` (hoặc fallback in-memory nếu không embed).

### User `alice`

1. `user_id=alice`: Tôi chỉ đầu tư bluechip ngân hàng, ưu tiên VCB.
2. (Lượt sau, có thể khác `thread_id`): Gợi ý mã phù hợp với tôi.

Recall sự thật dài hạn đã store.

3. Tôi không thích cổ phiếu thép.
4. HPG hôm nay có đáng xem với khẩu vị của tôi không?

### Đối chứng

- Cùng câu với `user_id=bob` → không được trộn memory của alice.
- Không gửi `user_id`: Tôi thích VNM. → lượt sau không recall.

Ví dụ body:

```json
{
  "question": "Tại sao HPG giảm?",
  "thread_id": "sess-1",
  "user_id": "alice"
}
```

---

## 12. HITL — luồng người duyệt (không phải câu chat thuần)

Sau các câu làm phát sinh ghi DB (5.5–5.10, hoặc “lưu tin vừa tìm”):

1. Màn hình diff: số lệnh INSERT/UPDATE, url, title, ticker.
2. **Duyệt** → Sink Router COMMIT đúng bucket (Giá / Tin theo mã / Tin chung).
3. **Từ chối** → DB không đổi; câu hỏi lại “tin nào đang lưu?” phải khớp.
4. Ghi đồng thời giá + tin → HITL từng loại, sub-agent không báo thẳng hub.

---

## 13. Plan chọn subset worker (không phải lúc nào cũng 5)

| # | Câu hỏi | Plan kỳ vọng |
|---|---------|----------------|
| 13.1 | Chỉ cho số giá VCB. | Price (± DB freshness). Tắt News, Eval, Synthesis nếu không cần. |
| 13.2 | Chỉ liệt kê headline FPT, đừng đánh giá. | News, **tắt Eval**. |
| 13.3 | Chỉ đọc DB, đừng crawl. | DB đọc; Price không gọi Swarm nếu không yêu cầu giá mới. |
| 13.4 | Đánh giá tin HPG tôi vừa hỏi (cùng thread). | Tái dùng tin/giá đúng mã; bật Eval. |
| 13.5 | Viết lại câu trả lời HPG cho sếp. | Synthesis (tái dùng báo cáo), không crawl. |

---

## 14. Sàn, mã, nguồn — phủ phạm vi

| # | Câu hỏi |
|---|--------|
| 14.1 | HPG (HOSE) hôm nay. |
| 14.2 | VNM hôm nay. |
| 14.3 | FPT hôm nay. |
| 14.4 | VCB hôm nay. |
| 14.5 | Một mã HNX: … hôm nay giảm vì sao? |
| 14.6 | Một mã UPCOM: tin và giá … |
| 14.7 | Mã mới niêm yết gần đây (không nằm list ví dụ) — giá + tin. |

---

## 15. API & quan sát hệ thống (không phải câu hỏi nghiệp vụ)

| # | Việc làm | Cần thấy |
|---|----------|----------|
| 15.1 | `POST /pr/ask` + câu 1.1 | `answer`, `trace`, `used_agents`, `plan_reasoning`, `thread_id`, `user_id`. |
| 15.2 | `POST /pr/price` `{"symbol":"HPG"}` | Giá, **không** hub, không OpenAI. |
| 15.3 | `POST /pr/ask/evaluate` `{"question":"Tại sao HPG giảm?"}` | `task_success` + `trajectory` (`efficiency`, `logical_order`, `tool_correctness`, `recovery`) + `trajectory_steps`. **Không** gộp vào `/pr/ask`. |
| 15.4 | Bật `MONITORING_ENABLED=true`, chạy `/pr/ask` | LangFuse: span cha `agent_pr_ask`, con `coordinator`, `craw_*`, `news_*`, `db_*`, `eval_score`, `synth_compose`, `reply`. |
| 15.5 | `POST /pr/price` khi monitoring | Span `agent_pr_price`. |

Ví dụ `curl` (Git Bash / Linux):

```bash
curl -s -X POST http://localhost:8000/pr/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Tại sao HPG giảm?"}'
```

---

## 16. Bộ “ngày demo” — 12 câu chạy hết kiến trúc

Chạy theo thứ tự, cùng `user_id=demo`, `thread_id=demo-1`:

1. Tại sao giá HPG giảm hôm nay?
2. % đó tính từ giá nào, nguồn nào?
3. Liệt kê từng tin, chưa cần chấm.
4. Chấm tốt/xấu và cho biết giá có khớp tin không.
5. 5 phiên trong DB đã yếu sẵn chưa?
6. Lưu hai tin vừa tìm vào DB. *(HITL: Duyệt)*
7. Báo cáo tài chính quý gần nhất của HPG nói gì?
8. Giá real-time HPG từ API SSI/TCBS.
9. Bảng giá JS SSI iBoard HPG.
10. Thị trường chung hôm nay, không riêng HPG.
11. Tôi ưu tiên VCB, không thích thép — nhớ giúp.
12. Phiên mới (`thread_id` khác): Mã tôi ưu tiên là gì? *(phải nhớ nhờ `user_id`, không nhờ thread)*

Sau câu 1, gọi thêm `POST /pr/ask/evaluate` với cùng câu hỏi để chấm trajectory.

---

## Checklist đối chiếu sau mỗi câu

- Worker **không nói với nhau**; mọi việc đi qua Coordinator.
- News không chấm sentiment; Eval không crawl.
- Synthesis không trả thẳng UI.
- Ghi DB không COMMIT trước HITL.
- Cùng phiên + cùng mã: không crawl lại giá/tin.
- Không `user_id`: không store/recall.
- Tin không match mã → Tin chung, không drop.
- Tin nhiều mã → nhiều ticker, không lỗi.
- Trace đủ để lần về từng agent đợt 1.

Đó là đủ bề mặt chức năng mà hai tài liệu mô tả: Hierarchical 5 worker, Swarm 5 loại crawl, 2 tầng Router, HITL, memory ngắn/dài, và 3 endpoint `/pr/ask`, `/pr/price`, `/pr/ask/evaluate`.
