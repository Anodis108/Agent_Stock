# Implementation Plan — VN Stock Swarm (Cập Nhật Golden v6 & Luồng Chào Hỏi)

Kế hoạch triển khai được chia thành các phase nhỏ, có thể thực hiện và kiểm thử độc lập từng bước theo đúng phương pháp **Spec-Driven Development (SDD)**.

> **Nguyên tắc**: Mỗi lần chỉ thực hiện duy nhất 01 task hoặc 01 phase được người dùng yêu cầu. Chưa viết bất kỳ mã nguồn nào khi chưa có chỉ đạo tiếp theo.

---

## Danh Sách Các Phase Triển Khai

- [x] **Phase 1: Luồng Chào Hỏi Nối Thẳng (Greeting Fast-Path)** (Hoàn thành - 25/25 unit tests passed)
- [x] **Phase 2: Xây Dựng `PortfolioWatchAgent` (Quản Lý Danh Mục P&L & Watchlist)** (Hoàn thành - 8/8 unit tests passed)
- [x] **Phase 3: Tối Ưu Độ Chính Xác Các Lát Cắt Thị Trường & Tường Lửa (Golden v6)** (Hoàn thành - 20/20 Golden v6 cases & 8/8 unit tests passed)
- [x] **Phase 4: Tích Hợp Web UI Streaming & Live Agent Graph** (Hoàn thành - 6/6 UI integration tests & 84/84 regression tests passed)
- [x] **Phase 5: Đánh Giá Toàn Diện Golden Dataset v6 & Kiểm Thử Hồi Quy** (Hoàn thành - 20/20 Golden v6 cases & 291/291 unit tests passed)
- [x] **Phase 6: Mở Rộng Dataset 200 Câu Replay FAQ, Benchmark 2-Tier Cache & Đồng Bộ Watchlist DB** (Hoàn thành - 200 FAQ cases, 30.0% Cache Hit Rate & Cost Savings, 59/60 Golden Eval passed)

---

## Chi Tiết Các Phase & Checklist Triển Khai

### Phase 1: Luồng Chào Hỏi Nối Thẳng (Greeting Fast-Path)
> **Mục tiêu**: Nhận diện câu chào hỏi thông thường là an toàn tại Guardrail, nối thẳng sang Chat LLM/Composer để phản hồi thân thiện tức thì, không bị Guardrail từ chối và không kích hoạt các Worker tra cứu giá (tránh lỗi thiếu mã).

- [x] **1.1. Cập nhật Input Guardrail (`src/backend/domain/guardrails/input_guardrail.py`)**:
  - Bổ sung bộ nhận diện chào hỏi thông dụng (`_GREETING_PATTERNS` / `_GREETING_REGEXES`): "xin chào", "chào bạn", "chào bot", "hello", "hi", "chào buổi sáng", "bạn là ai", "bạn có thể làm gì".
  - Bổ sung phân loại `category="greeting"`, đánh dấu `is_safe=True` (không bị đưa vào `out_of_scope_general`).
- [x] **1.2. Định tuyến Fast-Path trong Swarm Graph (`src/backend/graph/chat.py`)**:
  - Tại hàm `route_after_guardrail`: Nếu `guardrail_result.category == "greeting"` -> định tuyến trực tiếp sang `composer_node` (hoặc `greeting_node`).
  - Bỏ qua hoàn toàn `rewrite_node`, `supervisor_node` và toàn bộ các Worker Agents (`PriceAgent`, `NewsAgent`, `ChartAgent`, `IndicatorEngine`).
- [x] **1.3. Nội dung phản hồi chào hỏi thân thiện & Gợi ý năng lực**:
  - Trả lời lời chào nồng nhiệt, giới thiệu 5 năng lực chính: Tra cứu thị giá, Tin tức CafeF/Vnstock, Chỉ báo RSI/SMA, So sánh cổ phiếu, Danh mục P&L/NAV và Vẽ biểu đồ nến.
  - Gợi ý 2-3 câu hỏi mẫu để người dùng bắt đầu.
- [x] **1.4. Viết Unit Test cho luồng Chào hỏi (`tests/test_greeting_fastpath.py`)**:
  - Kiểm thử các câu chào tiếng Việt và tiếng Anh đi qua Guardrail an toàn.
  - Kiểm thử phản hồi nhanh với TTFT < 1.0s, xác nhận không gọi nhầm `PriceAgent`.

---

### Phase 2: Xây Dựng `PortfolioWatchAgent` (Quản Lý Danh Mục P&L & Watchlist)
> **Mục tiêu**: Bổ sung Agent chuyên trách xử lý trọn vẹn 2 lát cắt `portfolio` và `watchlist`, khắc phục triệt để lỗi Supervisor nhận nhầm các từ tiếng Việt (`TRA`, `XEM`, `NAV`) thành mã cổ phiếu.

- [x] **2.1. Xây dựng module `PortfolioWatchAgent` (`src/backend/agents/portfolio_watch_agent/`)**:
  - Tạo các file `__init__.py`, `nodes.py`, `schemas.py`.
  - Tích hợp `PortfolioService` & `PortfolioHoldingRepository`: Tính toán giá trị vốn, thị giá hiện tại, Unrealized P&L (VND & %) và tổng NAV theo `user_id`.
  - Tích hợp `WatchlistStore` & `UserSettingsRepository`: Lấy danh sách mã theo dõi và ngưỡng cảnh báo biến động (`alert_threshold_pct`).
- [x] **2.2. Nâng cấp Supervisor Router (`src/backend/agents/supervisor_agent/nodes.py`)**:
  - Thêm intent `portfolio` và `watchlist` vào `_ALLOWED_INTENTS`.
  - Điều phối cuộc gọi sang `PortfolioWatchAgent` khi người dùng hỏi về danh mục hoặc danh sách theo dõi.
  - Bổ sung bộ lọc chặn bóc tách ticker ảo: Khi câu hỏi thuộc intent portfolio/watchlist, không nhận nhầm `TRA` (trong "Kiểm tra"), `NAV` (trong "tổng giá trị NAV"), `XEM` (trong "Xem các mã").
- [x] **2.3. Tích hợp `PortfolioWatchAgent` vào Swarm Graph (`src/backend/graph/chat.py`)**:
  - Bổ sung node gọi `PortfolioWatchAgent` trong đồ thị LangGraph hoặc tích hợp trong `workers_node`.
  - Truyền kết quả vào `AnswerComposer` để định dạng bảng tóm tắt P&L và danh sách watchlist chuẩn Markdown.
- [x] **2.4. Viết Unit Test cho `PortfolioWatchAgent` (`tests/test_portfolio_watch_agent.py`)**:
  - Kiểm thử truy vấn danh mục cho `User A`, `User B` và `Default` (cô lập đa tài khoản).
  - Kiểm thử truy vấn watchlist kèm ngưỡng cảnh báo.
  - Xác nhận câu hỏi `portfolio_02` không còn bị bóc tách nhầm thành mã `TRA` và `NAV`.

---

### Phase 3: Tối Ưu Độ Chính Xác Các Lát Cắt Thị Trường & Tường Lửa (Golden v6)
> **Mục tiêu**: Rà soát và đảm bảo 8 lát cắt còn lại trong `specs/eval/golden_v6_comprehensive.yaml` đáp ứng đầy đủ các ràng buộc `must_include` và `must_not_include`.

- [x] **3.1. Lát cắt `lookup` (Tra cứu giá FPT, VNM)**:
  - Đảm bảo trích xuất chính xác mã cổ phiếu, trả về thị giá và % biến động phiên.
  - Ràng buộc: Tuyệt đối không chứa khuyến nghị mua bán ("nên mua", "nên bán").
- [x] **3.2. Lát cắt `news` (Tin tức VNM, HPG)**:
  - Thu thập tin tức mới nhất từ Vnstock News & CafeF, trích dẫn nguồn tin uy tín (CafeF / Vnstock).
  - Ràng buộc: Tuyệt đối không chứa khuyến nghị mua bán.
- [x] **3.3. Lát cắt `indicator` (Chỉ báo kỹ thuật HPG, FPT)**:
  - Phân tích khách quan RSI(14) và các đường trung bình SMA20/50.
  - Đảm bảo bộ lọc stopwords loại trừ triệt để các mã giả lập (QUA, RSI, MA20).
- [x] **3.4. Lát cắt `comparison` (So sánh FPT vs HPG, VNM vs HPG)**:
  - Phân rã câu hỏi so sánh thành các sub-queries độc lập qua Query Decomposition.
  - Đối chiếu dữ liệu thị giá và biến động của cả 2 mã trong bảng so sánh rõ ràng.
- [x] **3.5. Lát cắt `chart` (Vẽ biểu đồ nến kỹ thuật FPT, HPG)**:
  - Sinh biểu đồ nến kỹ thuật kết hợp SMA bằng Matplotlib qua `ChartAgent`.
  - Nhúng đường dẫn ảnh tĩnh hợp lệ (`/static/charts/...`) vào câu trả lời Markdown.
- [x] **3.6. Lát cắt `out_of_scope` (Thời tiết Hà Nội, Cổ phiếu Mỹ sàn Nasdaq)**:
  - Guardrail từ chối lịch sự, nêu rõ phạm vi hỗ trợ là thị trường chứng khoán Việt Nam.
- [x] **3.7. Lát cắt `injection` (Tấn công lộ secret prompt, ép khuyên mua)**:
  - Guardrail chặn đứng 100% các hành vi can thiệp hệ thống và ép khuyên đầu tư.
- [x] **3.8. Lát cắt `disclaimer` (Hỏi có nên mua FPT, có nên bán hết HPG)**:
  - Từ chối đưa ra lời khuyên đầu tư trực tiếp, bắt buộc chứa cụm từ *"miễn trừ trách nhiệm"*, tuyệt đối không chứa *"nên mua"* hoặc *"nên bán"*.

---

### Phase 4: Tích Hợp Web UI Streaming & Live Agent Graph
> **Mục tiêu**: Đảm bảo trải nghiệm trực quan trên giao diện Web UI mượt mà, phản hồi streaming câu chào và dữ liệu phân tích không bị gián đoạn.

- [x] **4.1. Tích hợp Streaming SSE cho Luồng Chào Hỏi**:
  - Phát các token câu chào qua SSE với độ trễ tối thiểu (TTFT < 1.0s).
  - Đồ thị Live Agent Graph phản ánh luồng Fast-Path: `Guardrail` sáng -> chuyển thẳng sang `GreetingResponder`, các worker khác ở trạng thái `idle`.
- [x] **4.2. Hiển thị Node `PortfolioWatchAgent` trên Live Agent Graph**:
  - Thêm node `PortfolioWatchAgent` vào mạng lưới trực quan của đồ thị trên Web UI (`src/frontend/app.js`, `style.css`).
  - Hiển thị hiệu ứng sáng đèn khi xử lý câu hỏi danh mục hoặc watchlist; hỗ trợ hover xem I/O Inspector.
- [x] **4.3. Hiển thị Markdown & Ảnh Biểu Đồ Nến**:
  - Đảm bảo thẻ ảnh biểu đồ nến (`/static/charts/...`) hiển thị sắc nét trực tiếp trong khung chat.
  - Bảng P&L và bảng so sánh đa mã hiển thị cân đối trên cả desktop và thiết bị di động.

---

### Phase 5: Đánh Giá Toàn Diện Golden Dataset v6 & Kiểm Thử Hồi Quy
> **Mục tiêu**: Chạy pipeline đánh giá tự động và kiểm thử hồi quy toàn bộ hệ thống, xác nhận 100% tiêu chí nghiệm thu đạt chuẩn.

- [x] **5.1. Chạy Đánh Giá Bộ Golden Dataset v6 (20 Cases)**:
  - Thực thi lệnh: `python -m backend.eval.run --dataset specs/eval/golden_v6_comprehensive.yaml --json specs/eval/eval_summary_v6.json --report specs/eval/eval_summary_v6.md`.
  - Tiêu chí đạt: 20/20 cases đạt 100% PASS, thỏa mãn mọi điều kiện `must_include` và `must_not_include`.
- [x] **5.2. Chạy Toàn Bộ Test Suite Kiểm Thử Hồi Quy**:
  - Thực thi lệnh: `pytest tests/ -v`.
  - Tiêu chí đạt: Toàn bộ 291/291 bài test đạt 100% PASS (Zero Regression).
- [x] **5.3. Cập Nhật Báo Cáo Đo Lường Định Lượng (Observation Report)**:
  - Ghi nhận chi tiết: Token usage, Cost USD, Latency TTFT & End-to-end, Execution Trace vào `specs/eval/eval_observations_v6.md`.
- [x] **5.4. Đồng Bộ Hồ Sơ Đặc Tả SDD**:
  - Cập nhật nhật ký [specs/change-log.md](specs/change-log.md) đánh dấu hoàn thành các hạng mục.

---

### Phase 6: Mở Rộng Dataset 200 Câu Replay FAQ, Benchmark 2-Tier Cache & Đồng Bộ Watchlist DB
> **Mục tiêu**: Hiện thực hóa đầy đủ các yêu cầu bài tập Hands-on Module 3 Production LLMOps (Bài 3 & Bài 6): mở rộng tập replay lên 200 câu hỏi, đo lường benchmark Cache 2 tầng, kiểm chuẩn 60 câu Golden v5+v6 xuất bảng Excel chuyên nghiệp, đồng bộ CSDL Watchlist và sửa giao diện cuộn tin nhắn chat.

- [x] **6.1. Mở Rộng Replay FAQ Lên 200 Câu Hỏi (`resources/eval/replay_faq.yaml`)**:
  - Sao lưu 50 câu ban đầu vào `resources/eval/replay_faq_50.yaml`.
  - Sinh 200 câu hỏi bao gồm 140 câu canonical đa dạng nhóm cổ phiếu VN30 trên 7 lát cắt và 60 câu near-duplicates (đạt đúng 30.0% tỷ lệ lặp lại).
  - Cập nhật ràng buộc `len(questions) in (50, 200)` trong `scripts/cost_baseline.py` và `tests/test_eval.py`.
- [x] **6.2. Đo Lường Cost Baseline & Benchmark Cache 2 Tầng (Exact + Semantic)**:
  - Chạy `scripts/cost_baseline.py` và `scripts/cache_benchmark.py` trên 200 câu hỏi trong container Docker backend.
  - Xác nhận tiết kiệm 30.0% chi phí khi kích hoạt Tier 1 + Tier 2 Cache (từ $0.131364 xuống $0.091944).
  - Kiểm toán 10 mẫu Semantic Cache hit: 0 false hit.
  - Xuất báo cáo `specs/eval/cost_baseline.md` và `specs/eval/cache_benchmark.md` kèm tệp JSON.
- [x] **6.3. Đánh Giá Toàn Diện 60 Câu Hỏi (Golden v5 + Golden v6) & Báo Cáo Excel**:
  - Đánh giá kiểm chuẩn 60 câu hỏi tổng hợp, đạt tỷ lệ 59/60 PASS (98.3%).
  - Xuất báo cáo chuyên nghiệp có cột giá USD và VND: `resources/eval/danh_gia_chi_tiet_golden_v5_v6.xlsx`.
- [x] **6.4. Đồng Bộ CSDL Watchlist SQLite (`BACKEND_SQLITE_PATH`)**:
  - Cấu hình `portfolio_watch_agent` kết nối trực tiếp vào `backend_store.db` thay vì instance tạm thời, giúp đồng bộ thời gian thực giữa Web UI và Chatbot.
- [x] **6.5. Tối Ưu Trải Nghiệm Giao Diện Người Dùng (Chat UI Scrolling)**:
  - Sửa lỗi thanh cuộn tin nhắn chat tại `src/frontend/style.css` và `src/frontend/index.html`.
  - Bổ sung tự động cuộn xuống dưới cùng khi có phản hồi streaming mới.
