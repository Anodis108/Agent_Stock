# Change Log — VN Stock Swarm & Portfolio Watch

Nhật ký ghi nhận chi tiết mọi thay đổi, kết quả kiểm thử và tiến độ triển khai theo phương pháp **Spec-Driven Development (SDD)**.

---

## 2026-10-01 — Hoàn Thành Mục 4.2: Tích Hợp API Quản Lý Danh Mục (Portfolio API & P&L Sync)

### Chi Tiết Triển Khai
1. **Chuẩn Hóa Luồng Gọi API Portfolio Trên Web UI (`src/frontend/app.js`)**:
   - Nâng cấp hàm `loadPortfolio()` gọi đồng thời cả 2 endpoint chuẩn qua `Promise.all`:
     - `GET /api/v1/portfolio/summary`: Lấy thông tin tổng hợp NAV, Lãi/Lỗ và Tỷ suất sinh lời % (`total_nav`, `total_unrealized_pnl`, `total_pnl_pct`, `total_cost`, `count`).
     - `GET /api/v1/portfolio/holdings`: Lấy danh sách chi tiết các vị thế cổ phiếu trong danh mục (`id`, `symbol`, `quantity`, `avg_buy_price`, `current_price`, `unrealized_pnl`, `pnl_pct`, `price_error`).
     - Hỗ trợ cơ chế tự động fallback về `/api/portfolio` và `/api/portfolio/holdings` đảm bảo tính tương thích ngược 100%.
   - Cập nhật tức thì 3 thẻ tóm tắt giá trị danh mục:
     - **Tổng NAV** (`#pnl-total-nav`): Định dạng chuẩn số tiền VND (`vi-VN`).
     - **Tổng Lãi/Lỗ** (`#pnl-total-pnl`): Hiển thị số tiền lãi/lỗ kèm dấu `+`/`-` và đổi màu CSS tương ứng (`pnl-up`, `pnl-down`, `pnl-ref`).
     - **Tỷ suất sinh lời %** (`#pnl-total-pct`): Định dạng phần trăm `+X.XX%`.
   - Render bảng vị thế cổ phiếu (`#portfolio-body`):
     - Hiển thị thông báo trạng thái rỗng thân thiện khi danh mục chưa có cổ phiếu (*"Danh mục đang trống. Hãy thêm mã cổ phiếu đầu tiên của bạn!"*).
     - Định dạng rõ ràng từng vị thế kèm xử lý cảnh báo `price_error` khi không lấy được giá thị trường.
     - Tự động gắn sự kiện click cho các nút xóa vị thế (`.btn-delete-holding`) theo attribute `data-holding-id`.

2. **Hỗ Trợ Thêm/Xóa Vị Thế & Cập Nhật Tức Thời (`src/frontend/app.js`)**:
   - `doAddHolding`: Gửi yêu cầu `POST /api/v1/portfolio/holdings` (kèm fallback `/api/portfolio/holdings`). Khi thành công, lập tức gọi `loadPortfolio()` nạp lại bảng và cập nhật giá trị NAV ngay lập tức, reset form và hiển thị thông báo toast thành công.
   - `doDeleteHolding`: Gửi yêu cầu `DELETE /api/v1/portfolio/holdings/{id}` (kèm fallback `/api/portfolio/holdings/{id}`). Khi thành công, lập tức gọi `loadPortfolio()` cập nhật lại dữ liệu danh mục của user hiện tại.
   - Nút `🔄 Làm mới` (`#btn-refresh-portfolio`): Kích hoạt `loadPortfolio()` theo nhu cầu người dùng.
   - User Switcher (`#user-switcher-select`): Đồng bộ gọi `loadPortfolio()` khi người dùng chuyển đổi tài khoản, đảm bảo cô lập tuyệt đối dữ liệu giữa các user.

3. **Kiểm Thử Tự Động Toàn Diện**:
   - Bổ sung `test_phase4_portfolio_api_integration` trong `tests/test_system.py`:
     - Kiểm tra tĩnh: Xác thực mã nguồn frontend `app.js` gọi đúng các endpoint chuẩn `/api/v1/portfolio/summary`, `/api/v1/portfolio/holdings`, `POST /api/v1/portfolio/holdings`, `DELETE /api/v1/portfolio/holdings/{id}` và tham chiếu đúng các phần tử UI (`pnl-total-nav`, `pnl-total-pnl`, `pnl-total-pct`).
     - Kiểm tra chuỗi tương tác tích hợp thực tế: Thêm vị thế, kiểm tra bảng summary & holdings, cập nhật NAV tức thì, xóa vị thế, kiểm tra cô lập đa người dùng (Multi-tenant).
   - Kiểm thử toàn diện: Toàn bộ test suite đạt **204/204 tests PASS 100%** (zero regression).

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - `GET /api/v1/portfolio/summary` và `GET /api/v1/portfolio/holdings` được gọi và xử lý mượt mà.
  - Các thao tác thêm, xóa cổ phiếu phản hồi nhanh chóng và cập nhật tức thì giá trị NAV trên giao diện.
  - Dữ liệu danh mục đầu tư được cô lập hoàn toàn giữa các tài khoản người dùng theo `X-User-ID`.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Ban đầu frontend `app.js` chỉ gọi `/api/portfolio` đơn lẻ. Đã nâng cấp gọi đồng thời `/api/v1/portfolio/summary` và `/api/v1/portfolio/holdings` kèm cơ chế fallback an toàn.

---

## 2026-10-01 — Hoàn Thành Mục 4.1: Tích Hợp Luồng SSE `/chat` (SSE Streaming & Live Graph Lighting)

### Chi Tiết Triển Khai
1. **Nâng Cấp Endpoint `POST /chat` Hỗ Trợ Server-Sent Events (SSE) (`src/backend/main.py` & `src/backend/api/routers/chat.py`)**:
   - Nhận diện linh hoạt header `Accept: text/event-stream` và query parameter `stream=true`:
     - Khi client yêu cầu streaming ➔ Trả về `StreamingResponse` với `media_type="text/event-stream"`.
     - Khi client gửi yêu cầu chuẩn JSON (`Accept: application/json`) ➔ Trả về schema `ChatResponse` chuẩn (bảo toàn 100% tính tương thích ngược).
   - Bảo toàn các route alias: `POST /chat`, `POST /api/v1/chat`, `POST /api/chat`, `POST /chat/stream`, `POST /api/v1/chat/stream`.

2. **Chuẩn Hóa Đầy Đủ 5 Sự Kiện Cốt Lõi SSE (`src/backend/graph/chat.py` & `src/backend/api/routers/chat.py`)**:
   - `node_start`: Phát ra khi agent bắt đầu chạy (kèm tên node, input, timestamp).
   - `node_end`: Phát ra khi agent kết thúc (kèm duration_s, duration_ms, output), đồng thời phát kèm alias `node_finish` cho các client cũ.
   - `token`: Phát ra từng mẩu từ/token câu trả lời trực tiếp trong quá trình stream Markdown.
   - `chart_url`: Phát ra ngay khi `chart_node` hoàn thành tạo ảnh biểu đồ kỹ thuật (kèm URL, symbols, chart_type).
   - `final_answer`: Phát ra khi toàn bộ Swarm hoàn thành luồng xử lý (kèm answer, chart_path, session_id, message_id, steps, total_duration_s), đồng thời phát kèm alias `complete`.

3. **Tích Hợp Web UI & Hiệu Ứng Sáng Đèn Live Graph (`src/frontend/app.js`)**:
   - Hàm `doChat` kết nối trực tiếp endpoint `apiUrl("/chat")` với header `Accept: text/event-stream`.
   - Xây dựng hàm `mergeWithCanonicalNodes` đồng bộ tiến trình chạy thời gian thực với 9 node chuẩn của Swarm (`CANONICAL_GRAPH_NODES`).
   - Hiệu ứng sáng đèn (Live Glow Pulse):
     - Khi nhận `node_start`: Node chuyển sang trạng thái `.status-running`, kích hoạt animation `node-glow-pulse` (box-shadow xanh dương nhấp nháy, dot xanh sáng).
     - Khi nhận `node_end` / `node_finish`: Node chuyển ngay sang `.status-done` (viền xanh lá, dot xanh lá, hiển thị badge thời gian `⏱`), giải phóng trạng thái chờ.
   - Sự kiện `token`: Cập nhật văn bản phản hồi mượt mà theo thời gian thực.
   - Sự kiện `chart_url`: Thu nhận URL biểu đồ và hiển thị thẻ ảnh trực tiếp khi hoàn tất.
   - Sự kiện `final_answer` / `complete`: Trình diễn Markdown hoàn chỉnh, ghim I/O Inspector và cập nhật lịch sử chat session.

4. **Kiểm Thử Tự Động Toàn Diện**:
   - Bổ sung `test_phase4_post_chat_sse_streaming_integration` trong `tests/test_api.py`: Kiểm tra gọi `POST /chat` nhận đầy đủ chuỗi 5 sự kiện SSE (`node_start`, `node_end`, `token`, `chart_url`, `final_answer`) và kiểm tra tính tương thích ngược cho yêu cầu JSON.
   - Bổ sung `test_phase4_frontend_sse_and_live_graph_integration` trong `tests/test_system.py`: Xác thực hợp đồng Frontend gọi SSE endpoint và CSS hiệu ứng `node-glow-pulse`.
   - Kết quả: Đạt **100% PASS** trên toàn bộ 22/22 tests của `test_api.py` và 21/21 tests của `test_system.py`.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - `POST /chat` stream SSE dạng `text/event-stream` đúng chuẩn khi client yêu cầu.
  - Chuỗi sự kiện `node_start`, `node_end`, `token`, `chart_url`, `final_answer` được phát đầy đủ và chính xác.
  - Live Graph sáng đèn nhịp thở xanh dương khi node chạy và chuyển xanh lá khi node hoàn thành.
  - Hợp đồng Frontend và Backend bảo toàn 100% không phát sinh lỗi.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Ban đầu `src/backend/main.py` định nghĩa `post_chat` ghi đè router mà chưa kiểm tra header `Accept: text/event-stream`, dẫn đến yêu cầu gửi tới `/chat` luôn trả về JSON. Đã bổ sung logic phát hiện streaming tại `src/backend/main.py` và kiểm thử thành công.

---

## 2026-10-01 — Hoàn Thành Mục 3.8: Tường Lửa Guardrail & Nghiệm Thu Toàn Diện Phase 3

### Chi Tiết Triển Khai
1. **Nâng Cấp Tường Lửa Guardrail Chống Prompt Injection Đa Dạng (`src/backend/domain/guardrails/input_guardrail.py`)**:
   - Mở rộng tập luật regex `_INJECTION_REGEXES` nhận diện và ngăn chặn triệt để các kỹ thuật Prompt Injection phổ biến và nâng cao:
     - Biến thể mệnh lệnh tiếng Việt có dấu và không dấu: `bỏ qua mọi/tất cả/toàn bộ mệnh lệnh/chỉ dẫn/hướng dẫn/quy tắc`, `quên toàn bộ hướng dẫn/mệnh lệnh`, `bo qua tat ca huong dan/quy tac`.
     - Kỹ thuật trích xuất cấu hình: `system prompt`, `in ra system prompt`, `show system prompt`, `reveal instructions`, `trích xuất prompt hệ thống`.
     - Kỹ thuật Jailbreak / DAN: `đóng vai model tự do`, `bất chấp mọi quy tắc/giới hạn`, `bỏ qua giới hạn an toàn`, `jailbreak`.
   - Giữ vững tỷ lệ chặn 100% các câu hỏi phi tài chính (thơ ca, thời tiết, giải trí, lập trình game) và cổ phiếu ngoại sàn ngoài Việt Nam (AAPL, TSLA, MSFT).

2. **Tự Động Nhận Diện Câu Hỏi Mua/Bán Trực Tiếp & Đính Kèm Tuyên Bố Miễn Trừ Trách Nhiệm**:
   - Chuẩn hóa hằng số `INVESTMENT_DISCLAIMER`:
     > *"Tuyên bố miễn trừ trách nhiệm đầu tư: Mọi thông tin chỉ mang tính chất tham khảo, không phải là lời khuyên hay khuyến nghị đầu tư tài chính. Quyết định đầu tư thuộc về trách nhiệm của người dùng."*
   - Xây dựng danh mục từ khóa và mẫu regex `_ADVICE_REQUEST_PATTERNS` / `_ADVICE_REGEXES` phát hiện mọi ý định xin tư vấn giao dịch trực tiếp:
     - `tư vấn đầu tư`, `có nên đầu tư`, `lời khuyên đầu tư`, `nên mua hay bán`, `khuyến nghị mua`, `khuyến nghị bán`, `bắt đáy`, `chốt lời`, `cắt lỗ`.
   - Khi phát hiện câu hỏi xin lời khuyên mua/bán trực tiếp: Guardrail chặn việc đưa ra chỉ dẫn giao dịch mù quáng, trả về câu trả lời từ chối an toàn kết hợp tự động chèn đầy đủ tuyên bố miễn trừ trách nhiệm.
   - Khi người dùng hỏi thông tin kỹ thuật hoặc thị trường hợp lệ, câu trả lời từ hệ thống vẫn được đính kèm tuyên bố miễn trừ trách nhiệm trong phản hồi tổng hợp.

3. **Cơ Chế Ngắt Sớm Trong Swarm Chat Graph (`src/backend/graph/chat.py`)**:
   - Tại node `guardrail_node`: Nếu câu hỏi vi phạm an toàn (Prompt Injection, Out-of-scope, hoặc Direct Advice), luồng thực thi lập tức kết thúc sớm (`END`), hoàn toàn không tiêu tốn token gọi LLM bên ngoài hay kích hoạt các worker agent (`PriceAgent`, `NewsAgent`, `IndicatorEngine`).

4. **Kiểm Thử Toàn Diện & Nghiệm Thu Hệ Thống**:
   - Bổ sung 3 bài kiểm thử chuyên sâu trong `tests/test_guardrails.py`:
     - `test_chat_graph_early_exit_on_direct_advice_with_disclaimer`: Xác thực chat graph ngắt sớm, không gọi workers và trả về tuyên bố miễn trừ trách nhiệm.
     - `test_guardrail_advanced_injection_patterns_and_regex`: Xác thực chặn 100% các biến thể injection tiếng Việt có dấu/không dấu, trích xuất prompt và jailbreak.
     - `test_guardrail_advice_patterns_with_disclaimer`: Xác thực nhận diện mọi dạng thức xin tư vấn mua bán và gắn kèm disclaimer.
   - Kết quả: **10/10 tests PASSED (100%)** trong `tests/test_guardrails.py`.
   - Chạy toàn bộ test suite dự án: **203/203 tests PASSED (100%)** không một lỗi hồi quy.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Chặn 100% Prompt Injection đã biết (từ khóa và regex đa dạng).
  - Từ chối câu hỏi phi tài chính và cổ phiếu nước ngoài.
  - Tự động chèn tuyên bố miễn trừ trách nhiệm đầu tư khi có câu hỏi mua/bán trực tiếp.
  - Kiểm thử 10/10 tests `tests/test_guardrails.py` và 203/203 toàn bộ repo đạt 100% PASS.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Ban đầu regex `lệnh` không match từ ghép `mệnh lệnh`, đã bổ sung `mệnh\s*lệnh` và kiểm tra chống injection toàn diện.

---

## 2026-09-30 — Hoàn Thành Mục 3.7: Biểu Đồ Nến Kỹ Thuật (ChartAgent)

### Chi Tiết Triển Khai
1. **Tối Ưu Render Biểu Đồ Nến Kỹ Thuật (Candlestick Chart) & Đường SMA (`src/backend/agents/chart_agent.py`)**:
   - Tinh chỉnh hàm `plot_price_history`:
     - Khi `style == "candle"`: Chỉ vẽ các thanh nến kỹ thuật rõ nét (râu nến wick từ `low` đến `high`, thân nến bar từ `min(open, close)` với chiều cao `|close - open|`), tô màu xanh (`#10b981`) cho phiên tăng và đỏ (`#ef4444`) cho phiên giảm; tách biệt không vẽ đường nối giá Close đè lên nến.
     - Thêm proxy artists cho Legend biểu đồ nến: `Nến tăng ({sym})` và `Nến giảm ({sym})` giúp giao diện trực quan và chuyên nghiệp.
     - Hỗ trợ linh hoạt các đường Simple Moving Average `sma_periods` (mặc định `(5, 10, 20)` và tương thích chuẩn `(20, 50)`), tự động tính toán và vẽ đường trung bình động nét đứt khi độ dài chuỗi giá đáp ứng chu kỳ.
     - Giữ nguyên subplot khối lượng giao dịch (Volume Bar Chart) phía dưới với màu sắc tương ứng phiên tăng/giảm.
2. **Nâng Cấp Điều Phối & Tự Động Nhận Diện Ý Định Nến Kỹ Thuật (`src/backend/graph/chat.py`)**:
   - Nâng cấp `run_chart_agent` hỗ trợ tham số `sma_periods` và tự động kích hoạt `style="candle"` khi `chart_type` là `candlestick` hoặc `candle`.
   - Cập nhật `chart_node` và `workers_node`: Tự động phân tích câu hỏi người dùng; nếu chứa các từ khóa nến (*"nến"*, *"candle"*, *"candlestick"*, *"kỹ thuật"*), tự động chuyển chế độ sang `style="candle"` và `chart_type="candlestick"`.
3. **Nhúng Trực Tiếp Thẻ Markdown Ảnh Trong Phản Hồi (`src/backend/agents/answer_composer/nodes.py`)**:
   - Cập nhật `HeuristicAnswerDraftBrain`: Khi trong `evidence` xuất hiện `chart_path`, tự động đính kèm thẻ ảnh Markdown: `![Biểu đồ {sym}]({chart_path}) tại: {chart_path}.`
   - Phục vụ tĩnh ảnh PNG từ thư mục `resources/data/charts/` tương ứng qua cả 2 alias routes `/charts/` và `/static/charts/`.
4. **Kiểm Thử Tự Động & Chống Hồi Quy (`tests/test_chart.py`)**:
   - Thêm bài kiểm thử chuyên sâu: `test_phase3_candlestick_chart_generation_with_sma_and_static_cache`:
     - Kiểm tra sinh biểu đồ nến candlestick trực tiếp bằng `plot_price_history(style="candle", sma_periods=(5, 10, 20))` với 30 phiên nến.
     - Xác thực header PNG chuẩn 8 byte: `\x89PNG\r\n\x1a\n` và kích thước file `> 1000` byte.
     - Kiểm tra điều phối qua `run_chart_agent` với `chart_type="candlestick"`.
     - Kiểm tra tích hợp Swarm Chat Graph với câu hỏi *"Vẽ biểu đồ nến kỹ thuật cho FPT"*, xác nhận kết quả trả về `chart_type="candlestick"`, `chart_path` hợp lệ và câu trả lời Markdown nhúng đúng thẻ ảnh `![Biểu đồ FPT]`.
   - Tối ưu hóa các bài test trong `tests/test_chart.py` sử dụng `HeuristicAnswerDraftBrain` chạy siêu tốc offline.
   - Kết quả: Toàn bộ 14/14 tests trong `tests/test_chart.py` đạt **100% PASS**; các test suite khác `test_agents.py`, `test_indicators.py`, `test_portfolio_service.py` tiếp tục đạt **100% PASS** (49/49 tests).

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Sinh biểu đồ nến kỹ thuật OHLCV bằng Matplotlib với nến xanh (`#10b981`), nến đỏ (`#ef4444`) và râu nến chuẩn xác.
  - Các đường SMA (5, 10, 20 hoặc 20, 50) được tính toán và vẽ đè mượt mà trên biểu đồ.
  - Thư mục static cache lưu trữ ảnh PNG tĩnh tại `resources/data/charts/` và truy cập được qua URL `/charts/` và `/static/charts/`.
  - Phản hồi Markdown tự động nhúng thẻ ảnh `![Biểu đồ {symbol}]({chart_path})`.
  - Toàn bộ bài kiểm thử trong `test_chart.py` (14/14) và suite liên quan (49/49) vượt qua 100%.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây biểu đồ nến vẫn vẽ đè đường nối Close giá xanh lên thân nến làm rối mắt, thiếu legend nến tăng/giảm và thiếu cơ chế nhận diện từ khóa "nến" để tự động kích hoạt `style="candle"`. Hiện đã tối ưu hoàn chỉnh và kiểm thử thành công.

---

## 2026-09-30 — Hoàn Thành Mục 3.6: Quản Lý Danh Mục & Lãi/Lỗ (PortfolioService)

### Chi Tiết Triển Khai
1. **Chuẩn Hóa Module `PortfolioService` Tầng Dịch Vụ (`src/backend/services/portfolio_service.py`)**:
   - Xuất khẩu `PortfolioService`, `PortfolioSummary`, `PortfolioItemSummary` từ `backend.services`:
     - Đồng bộ cấu trúc thư mục kiến trúc sạch (Clean Architecture), cho phép các module khác import trực tiếp `from backend.services import PortfolioService`.
2. **Đảm Bảo Tính Toán Lãi/Lỗ Toán Học Chính Xác**:
   - `Unrealized P&L`: $(\text{current\_price} - \text{avg\_buy\_price}) \times \text{quantity}$ tính toán chuẩn xác cho các vị thế lãi, lỗ và hòa vốn.
   - `Total NAV`: $\sum (\text{current\_price} \times \text{quantity})$ phản ánh đúng giá trị thị trường ròng của danh mục.
   - `P&L %`: $\frac{\text{Unrealized P\&L}}{\text{Cost Basis}} \times 100\%$ tính toán chính xác trên quy mô danh mục và từng mã.
   - Chuẩn hóa thông minh mệnh giá: giá $\le 1000$ (nghìn VND theo quy ước HOSE/Vnstock) tự động nhân $1,000$ sang VND đầy đủ.
3. **Cô Lập Dữ Liệu Tuyệt Đối Giữa Các `user_id` (Multi-tenant Isolation)**:
   - Các phương thức `list_by_user`, `add_holding`, `delete_holding` phân tách chặt chẽ theo `user_id` trong SQLite.
   - Người dùng A cố tình gửi ID vị thế của Người dùng B để xóa sẽ bị từ chối (`False` / 404), bảo vệ an toàn dữ liệu khách hàng.
4. **Cơ Chế Fallback Giá An Toàn (Graceful Fallback)**:
   - Khi `PriceSource` gặp lỗi hoặc không tìm thấy thị giá, `market_value` tự động fallback về `cost_basis`, `unrealized_pnl = 0.0`, gắn cờ `price_error = True` chống sập hệ thống.
5. **Kiểm Thử Tự Động & Chống Hồi Quy (`tests/test_portfolio_service.py`)**:
   - Xây dựng 3 bài test chuyên sâu:
     - `test_portfolio_pnl_mathematical_precision`: Kiểm tra công thức toán học P&L, NAV, % Lời/Lỗ cho nhiều mã đồng thời.
     - `test_portfolio_multi_tenant_isolation`: Kiểm tra cô lập dữ liệu tuyệt đối giữa `investor_alice` và `investor_bob`.
     - `test_portfolio_empty_state_and_graceful_fallback`: Kiểm tra trạng thái rỗng và cơ chế fallback an toàn.
   - Kết quả: `test_portfolio_service.py` 3/3 PASS, `test_system.py` portfolio tests PASS, toàn bộ test suite đạt **199/199 tests PASS 100%**.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Unrealized P&L tính toán chuẩn xác theo công thức $(\text{current\_price} - \text{avg\_buy\_price}) \times \text{quantity}$.
  - Tổng NAV tính toán chuẩn xác theo công thức $\sum (\text{current\_price} \times \text{quantity})$.
  - Cô lập đa người dùng (Multi-tenant) hoạt động tuyệt đối trong SQLite.
  - Cơ chế Fallback an toàn bảo vệ danh mục khi mất mạng ngoài hoặc lỗi nguồn giá.
  - Toàn bộ 199 tests của hệ thống vượt qua tuyệt đối.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: `PortfolioService` trước đây chỉ nằm trong `src/backend/application/` mà thiếu module đại diện trong `src/backend/services/` tương tự `MarketService` và `TechnicalIndicatorService`. Đã tạo `services/portfolio_service.py` và cập nhật `__init__.py` chuẩn hóa.

---

## 2026-09-30 — Hoàn Thành Mục 3.5: Phân Rã Câu Hỏi Đa Ý (RewriteBrain - Query Decomposition)

### Chi Tiết Triển Khai
1. **Phân Rã Câu Hỏi So Sánh Đa Mã Thành 2 Sub-queries Độc Lập (`src/backend/agents/supervisor_agent/nodes.py`)**:
   - Tối ưu hóa hàm `_decompose_query`:
     - Nhận diện các từ khóa so sánh: `vs`, `versus`, `so sánh`, `so với`, `khác nhau`.
     - Khi người dùng so sánh trực diện 2 mã (VD: `FPT vs HPG` hoặc `So sánh FPT vs HPG`): Tách câu hỏi thành đúng **2 sub-queries độc lập** theo từng mã:
       1. `Giá và biến động gần nhất của cổ phiếu FPT là bao nhiêu?`
       2. `Giá và biến động gần nhất của cổ phiếu HPG là bao nhiêu?`
     - Khi người dùng hỏi cả khía cạnh giá và tin tức (như `DEC-01`): tiếp tục mở rộng phân rã thành 4 sub-queries chuyên biệt (2 câu về giá, 2 câu về tin tức) bảo đảm độ bao phủ thông tin.
   - Bổ sung quy tắc rewrite cho từ khóa `vs`/`versus` trong `HeuristicRewriteBrain.rewrite`.
2. **Bộ Lọc Stopword Loại Bỏ Mã Cổ Phiếu Giả Lập (`_TICKER_STOPWORDS`)**:
   - Mở rộng và áp dụng bộ lọc `_TICKER_STOPWORDS` đồng bộ cho cả `_MA_SYMBOL_RE` (`mã ...`) và `_TICKER_RE` (từ viết hoa đứng độc lập):
     - Loại bỏ triệt để các từ thông dụng tiếng Việt dễ bị nhận diện nhầm thành mã chứng khoán: `GIA` (giá), `TAI` (tại), `TIA` (tịa), `HIEN` (hiện), `TOI` (tôi), `BAO` (bao nhiêu), `ATC`, `ATO`, `SAO`, `NAY`, `HOM`, `NAO`, `CUA`, `NHE`, `VAY`.
     - Ngăn chặn hoàn toàn việc nhận nhầm mã giả khi người dùng nhập câu tiếng Việt không dấu hoặc viết hoa.
3. **Đồng Bộ Prompt Registry (`resources/prompts/rewrite_question/`)**:
   - Cập nhật quy tắc trích xuất mã và hướng dẫn phân rã sub-questions trong `v1.yaml` và `production.txt`.
   - Kiểm tra `prompt_lint` đạt 100% OK.
4. **Kiểm Thử Tự Động & Chống Hồi Quy**:
   - Bổ sung bài kiểm thử tự động `test_phase3_query_decomposition_comparison_and_stopwords` trong [`tests/test_agents.py`](../tests/test_agents.py):
     - Kiểm tra `FPT vs HPG` và `So sánh FPT vs HPG` tách thành đúng 2 sub-queries.
     - Kiểm tra câu hỏi chứa `GIA`, `HIEN`, `TAI`, `TIA`, `TOI` chỉ trích xuất duy nhất mã hợp lệ `FPT`.
     - Kiểm tra `_extract_symbols` lọc sạch toàn bộ stopword.
   - Kết quả: 40/40 tests trong `tests/test_agents.py` đạt **100% PASS**, bộ 5 test cases `DEC-01` đến `DEC-05` duy trì PASS tuyệt đối.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Câu hỏi so sánh đa mã (VD: `FPT vs HPG`) được phân rã chính xác thành 2 sub-queries độc lập theo từng mã.
  - Các từ giả mã `GIA`, `TAI`, `TIA`, `HIEN`, `TOI` bị loại bỏ 100% khỏi danh sách `symbols`.
  - Bộ kiểm thử phân rã `DEC-01` đến `DEC-05` và test case mới đều vượt qua tuyệt đối.
  - Toàn bộ 40 test cases của Swarm Agent đều PASS.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây hàm `_extract_symbols` khi quét qua regex `_MA_SYMBOL_RE` (`mã ...`) không kiểm tra `_TICKER_STOPWORDS`, dẫn đến cụm từ như "mã GIA" hoặc "mã HIEN" bị nhận nhầm thành mã cổ phiếu; hàm `_decompose_query` gộp chung `is_comparison` vào nhánh tạo 4 sub-queries thay vì trả về đúng 2 sub-queries cho câu hỏi so sánh trực tiếp 2 mã. Đã khắc phục và chuẩn hóa hoàn toàn.

---

## 2026-09-30 — Hoàn Thành Mục 3.4: Đánh Giá Rủi Ro (EvalAgent)

### Chi Tiết Triển Khai
1. **Mở Rộng Mô Hình Dữ Liệu `SeverityLevel` & `EvalSeverityOutput` (`models.py` & `schemas.py`)**:
   - Bổ sung cấp độ `NONE = "none"` vào enum `SeverityLevel` trong `src/backend/domain/entities/models.py`.
   - Cập nhật kiểu `Literal["none", "low", "medium", "high"]` cho trường `level` trong `EvalSeverityOutput` (`src/backend/shared/schemas.py`).
   - Cập nhật bảng ánh xạ `level_map` trong phương thức `to_severity()` để ánh xạ `"none"` thành `SeverityLevel.NONE`.
2. **Nâng Cấp Logic Đánh Giá Rủi Ro Định Lượng (`src/backend/agents/eval_agent/nodes.py`)**:
   - `HeuristicEvalBrain.build_severity` kết hợp đầy đủ 3 nguồn dữ liệu: biến động giá (`change_pct`), tin tức xúc tác (`news.items`), và chỉ báo kỹ thuật (`IndicatorSummary`):
     - **Cấp độ `NONE`**: Khi biến động giá không đáng kể (`abs(change) < 0.5%`), danh sách tin tức rỗng, và không có cảnh báo kỹ thuật bất thường nào.
     - **Cấp độ `LOW`**: Khi biến động giá nhỏ ($0.5\% \le |\text{change}| < 3\%$), không có tin tức tiêu cực hay rủi ro đảo chiều.
     - **Cấp độ `MEDIUM`**: Khi biến động giá từ $3\% \le |\text{change}| < 7\%$, hoặc khi xuất hiện tin tức mới (tự động nâng từ `NONE`/`LOW` lên `MEDIUM`), hoặc có tín hiệu giao cắt `death_cross`, hoặc RSI rơi vào vùng quá bán ($\le 30$).
     - **Cấp độ `HIGH`**: Khi biến động giá chạm trần/sàn biên độ ($\ge 7\%$), hoặc khi giá tăng mạnh ($\ge 3\%$) đi kèm trạng thái quá mua cực đại ($\text{RSI} \ge 70$).
   - Tạo chuỗi diễn giải nguyên nhân `reasoning` và bổ sung các bằng chứng kỹ thuật định lượng vào `evidence`.
3. **Đồng Bộ Prompt Đánh Giá Rủi Ro (`resources/prompts/eval_severity/`)**:
   - Cập nhật ràng buộc schema `level: none | low | medium | high` trong cả `v1.yaml` và `production.txt`.
   - Kiểm tra `prompt_lint` đạt 100% OK.
4. **Kiểm Thử Tự Động & Chống Hồi Quy**:
   - Bổ sung test case `test_phase3_eval_agent_four_severity_levels` trong [`tests/test_agents.py`](../tests/test_agents.py) kiểm tra đầy đủ cả 4 cấp độ rủi ro và xác thực chuyển đổi schema Pydantic.
   - Kết quả: `test_agents.py` đạt 39/39 PASS, `test_eval.py` đạt 33/33 PASS, toàn bộ test suite đạt 100% PASS không có lỗi hồi quy.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - EvalAgent phân loại chính xác 4 cấp độ rủi ro: `none`, `low`, `medium`, `high`.
  - Kết hợp chặt chẽ giữa biến động giá, tin tức đa nguồn và chỉ số kỹ thuật (RSI quá mua/quá bán, MA Cross).
  - Pydantic schema `EvalSeverityOutput` xác thực và parse chuẩn cả 4 mức độ rủi ro.
  - Toàn bộ test suite và prompt linting đều vượt qua tuyệt đối.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: `SeverityLevel` trước đây chỉ có 3 mức `LOW`, `MEDIUM`, `HIGH` thiếu mức `NONE`; `EvalSeverityOutput` giới hạn Literal không cho phép `"none"`. `HeuristicEvalBrain` mặc định trả về `LOW` ngay cả khi giá đứng yên 0.0% và không có bất kỳ tin tức nào. Đã nâng cấp và phân loại chuẩn hóa theo đặc tả.

---

## 2026-09-30 — Hoàn Thành Mục 3.3: Động Cơ Chỉ Báo Kỹ Thuật (TechnicalIndicatorService)

### Chi Tiết Triển Khai
1. **Xây Dựng Lớp Dịch Vụ `TechnicalIndicatorService` (`src/backend/services/technical_indicator_service.py`)**:
   - Thiết kế lớp dịch vụ chuẩn hóa đóng gói toàn bộ logic chỉ báo kỹ thuật:
     - `calculate_rsi(closes, period=14)`: Tính toán Relative Strength Index (RSI) theo thuật toán làm mượt Wilder (Wilder's smoothing).
     - `calculate_sma(closes, period)`: Tính toán Simple Moving Average (SMA20, SMA50).
     - `analyze(closes)`: Phân tích toàn diện trả về `IndicatorSummary` gồm giá trị RSI, trạng thái RSI (`overbought` khi >70, `oversold` khi <30, `neutral`), SMA20, SMA50, tín hiệu giao cắt `ma_cross` (`golden_cross`, `death_cross`, `none`) và xu hướng `trend` (`bullish`, `bearish`, `neutral`).
     - `analyze_bars(bars)`: Nhận mảng `PriceBar` và tự động trích xuất chuỗi giá đóng cửa để phân tích.
     - `analyze_symbol(symbol, lookback_days=60)`: Kết nối `PriceSourcePort`, nạp nến lịch sử và phân tích toàn diện.
2. **Cập Nhật Contract và Export Module (`src/backend/domain/ports.py` & `src/backend/services/__init__.py`)**:
   - Thêm phương thức `fetch_history(symbol, lookback_days)` vào giao thức `PriceSource` protocol.
   - Định nghĩa alias `PriceSourcePort = PriceSource` và `NewsSourcePort = NewsSource`.
   - Xuất khẩu `TechnicalIndicatorService` và `MarketService` từ package `backend.services`.
3. **Kiểm Thử Toàn Diện & Chống Hồi Quy (`tests/test_indicators.py`)**:
   - Xây dựng 6 bài kiểm thử chuyên biệt:
     - `test_compute_rsi_insufficient_data`: Kiểm tra trả về `None` khi chuỗi nến < 15, và trả về 50.0 khi giá không đổi.
     - `test_compute_rsi_overbought_and_oversold`: Kiểm tra nhận diện Quá mua (`RSI > 70`) khi giá tăng liên tục, Quá bán (`RSI < 30`) khi giá giảm liên tục, và vùng Trung tính (`30 <= RSI <= 70`).
     - `test_compute_sma`: Kiểm tra tính trung bình cộng chính xác cho chu kỳ 3 phiên, 5 phiên, và trả về `None` khi thiếu dữ liệu.
     - `test_crossover_golden_cross`: Kiểm tra kích hoạt `golden_cross` và xu hướng `bullish` khi SMA20 cắt lên trên SMA50.
     - `test_crossover_death_cross`: Kiểm tra kích hoạt `death_cross` và xu hướng `bearish` khi SMA20 cắt xuống dưới SMA50.
     - `test_technical_indicator_service_api`: Kiểm tra toàn diện các API của `TechnicalIndicatorService` với DummyPriceSource.
   - Kết quả: `test_indicators.py` đạt 6/6 PASS, toàn bộ test suite đạt 194/194 PASS (0 failure), `prompt_lint` đạt 100% OK.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - RSI(14) tính toán chính xác theo chuẩn Wilder smoothing, nhận diện chuẩn xác Quá mua (>70) và Quá bán (<30).
  - SMA(20) và SMA(50) tính toán chính xác.
  - Tín hiệu Golden Cross và Death Cross được phát hiện chính xác khi có giao cắt 2 phiên gần nhất.
  - Lớp `TechnicalIndicatorService` cung cấp API sạch sẽ, hỗ trợ phân tích trực tiếp theo symbol qua `PriceSourcePort`.
  - Toàn bộ 194 test cases trong dự án đều PASS tuyệt đối.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây các hàm tính toán chỉ báo nằm rải rác dưới dạng pure functions trong `domain/indicators.py` mà thiếu một lớp Service thống nhất (`TechnicalIndicatorService`) để tích hợp nạp dữ liệu lịch sử từ `PriceSourcePort`; `PriceSource` protocol trong `domain/ports.py` thiếu khai báo `fetch_history`. Đã khắc phục và chuẩn hóa hoàn toàn.

---

## 2026-09-30 — Hoàn Thành Mục 3.2: Tin Tức Tài Chính (NewsAgent)

### Chi Tiết Triển Khai
1. **Tích Hợp Nguồn Tin Đa Kênh Vnstock & CafeF (`src/backend/infra/market_data/news_source.py`)**:
   - Thêm lớp `VnstockNewsSource` kế thừa `NewsSourcePort`:
     - Sử dụng API `vnstock.Company(symbol=sym).news()` để lấy danh sách tin tức chính thống từ KBS/Vnstock.
     - Chuẩn hóa các trường: `title`, `snippet` (trích xuất từ phần mở đầu bài viết `head`), `url`, `publish_time`, và `source="Vnstock"`.
   - Cập nhật `MultiSourceNewsSource`:
     - Kết hợp luồng lấy tin tức đồng thời từ cả `CafefNewsSource` và `VnstockNewsSource`.
     - Tích hợp cơ chế khử trùng lặp thông minh (`deduplicate_news_items`) theo tiêu đề tin tức đã chuẩn hóa.
2. **Chuẩn Hóa Thuộc Tính Nguồn Tin & Trích Dẫn (`src/backend/domain/ports.py` & `src/backend/agents/answer_composer/nodes.py`)**:
   - Bổ sung trường `source: str = "CafeF"` vào cấu trúc dữ liệu `NewsItem`.
   - Cập nhật logic soạn thảo câu trả lời `_news_summary` và `HeuristicAnswerDraftBrain`:
     - Tự động bổ sung trích dẫn rõ nguồn gốc thông tin: `(nguồn: CafeF)` hoặc `(nguồn: Vnstock)` sau từng tin tức hoặc dòng điểm tin.
3. **Cấu Hình Mặc Định Trong Dependency Injection (`src/backend/api/deps.py` & `__init__.py`)**:
   - Khởi tạo mặc định `MultiSourceNewsSource(sources=[CafefNewsSource(), VnstockNewsSource()])` cho toàn bộ ứng dụng và Swarm Multi-Agent.
4. **Kiểm Thử Tự Động & Chống Hồi Quy**:
   - Bổ sung bài test `test_phase3_vnstock_news_source_and_attribution` trong [`tests/test_agents.py`](../tests/test_agents.py):
     - Kiểm tra khả năng lấy tin tức của `VnstockNewsSource` có đầy đủ `title`, `snippet`, `source == "Vnstock"`.
     - Kiểm tra `MultiSourceNewsSource` kết hợp cả 2 nguồn tin mà không lỗi.
     - Kiểm tra chuỗi phản hồi của `AnswerComposer` chứa rõ trích dẫn `(nguồn: ...)`.
   - Chạy toàn bộ test suite: 188/188 PASS, kiểm tra prompt lint: 100% OK.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - NewsAgent lấy tin tức tài chính ổn định từ cả Vnstock và CafeF.
  - Phản hồi của Swarm trích dẫn rõ tiêu đề, tóm tắt và nguồn tin tương ứng.
  - Khử trùng lặp tiêu đề hiệu quả khi cả 2 nguồn cùng có tin tức tương tự.
  - 100% test suite (188 tests) vượt qua, không gây bất kỳ tác dụng phụ (zero regression).
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây hệ thống chỉ có `CafefNewsSource` với cấu trúc `NewsItem` không lưu trữ trường `source`, dẫn đến câu trả lời tổng hợp không có trích dẫn nguồn tin (`(nguồn: CafeF)` / `(nguồn: Vnstock)`). Đã bổ sung `VnstockNewsSource`, trường `source`, cơ chế gộp `MultiSourceNewsSource` và logic trích dẫn trong `AnswerComposer`.

---

## 2026-09-30 — Hoàn Thành Mục 3.1: Dữ Liệu Thị Trường & Giá (PriceAgent & MarketService)

### Chi Tiết Triển Khai
1. **Mở Rộng `PriceAgentResult` với Biên Độ Giao Dịch Chứng Khoán VN (`src/backend/agents/price_agent/schemas.py`)**:
   - Bổ sung các thuộc tính `@property` chuẩn hóa cho sàn HOSE:
     - `reference_price`: Giá tham chiếu (chính là giá đóng cửa phiên liền trước `prev_close`).
     - `ceiling_price`: Giá trần biên độ +7% (`round(prev_close * 1.07, 2)`).
     - `floor_price`: Giá sàn biên độ -7% (`round(prev_close * 0.93, 2)`).
   - Đảm bảo tính toán chính xác % thay đổi `change_pct` và cơ chế đồng bộ tự động `_sync_price_to_market_history`.
2. **Cơ Chế Fallback Chống Sập Thông Minh (`src/backend/infra/market_data/price_source.py`)**:
   - `VnstockPriceSource` hỗ trợ biến môi trường `PRICE_FALLBACK_ON_ERROR` (mặc định cấu hình an toàn khi offline/test).
   - Tích hợp hàm `_synthesize_fallback_bars` tạo chuỗi nến ngày giả lập bám sát giá cơ sở `DEFAULT_BASE_PRICES` khi sàn đóng cửa, lỗi mạng hoặc bị giới hạn tần suất (rate-limit).
   - Giữ vững nguyên lý **Single Source of Truth (SSOT)**: Bộ nhớ đệm chia sẻ `_SHARED_QUOTE_CACHE` và `_SHARED_HISTORY_CACHE` giữa Agent Swarm và Market Watch service.
3. **Endpoint Ma Trận 10 Phiên VN30 (`src/backend/api/routers/market.py` & `market_service.py`)**:
   - Endpoint `/api/v1/market/matrix-10d` (kèm các alias `/api/market/matrix-10d`, `/market/matrix-10d`) phục vụ đầy đủ 10 mã blue-chip VN30 (`FPT`, `VNM`, `HPG`, `VHM`, `VIC`, `TCB`, `MBB`, `SSI`, `MWG`, `VCB`).
   - Cung cấp đủ mảng sparklines (10 điểm giá đóng cửa), khối lượng giao dịch tích lũy (`total_volume`), và chi tiết từng phiên nến OHLCV (`MarketSessionOut`).
4. **Kiểm Thử Tự Động & Chống Hồi Quy**:
   - Bổ sung 2 bài test tự động vào [`tests/test_market.py`](../tests/test_market.py):
     - `test_phase3_price_agent_trading_bands_and_percentage_calculation`: Kiểm tra tính toán % thay đổi, giá tham chiếu, giá trần và giá sàn.
     - `test_phase3_market_matrix_10d_sparkline_and_fallback`: Kiểm tra ma trận 10D đầy đủ 10 mã, sparkline 10 điểm, session data và cơ chế fallback khi ngắt kết nối mạng.
   - Chạy kiểm thử: `tests/test_market.py` 9/9 PASS, `test_agents.py` price tests 2/2 PASS, `prompt_lint` đạt OK.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Hàm lấy giá khớp lệnh, % biến động, giá tham chiếu, giá trần (+7%) và giá sàn (-7%) hoạt động chính xác.
  - Endpoint `/api/v1/market/matrix-10d` trả về đầy đủ 10 mã VN30 kèm mảng sparklines 10 điểm và chi tiết sessions.
  - Cơ chế fallback tự động sinh dữ liệu mẫu khi thị trường đóng cửa hoặc mất mạng ngoài hoạt động trơn tru, không gây crash hệ thống.
  - Toàn bộ các bài kiểm thử thị trường và agent price đều đạt 100% PASS.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: `PriceAgentResult` trước đây chỉ chứa `latest_close`, `prev_close`, `change_pct` mà thiếu các thuộc tính hỗ trợ tính toán biên độ trần/sàn/tham chiếu chuẩn Việt Nam; `fetch_history` trong `VnstockPriceSource` chưa tự động fallback khi bật `fallback_on_error`. Hiện đã khắc phục và bổ sung hoàn chỉnh.

---

## 2026-09-30 — Hoàn Thành Mục 2.5: Bảng Hiển Thị Danh Mục & P&L (Hoàn Tất Phase 2)

### Chi Tiết Triển Khai
1. **Kiến Trúc Bảng Danh Mục & Thẻ Tóm Tắt P&L (`src/frontend/index.html` & `style.css`)**:
   - Tab Danh mục (`#portfolio`) sở hữu giao diện chuyên nghiệp:
     - **3 Thẻ tóm tắt P&L**: `#pnl-total-nav` (Tổng NAV), `#pnl-total-pnl` (Tổng Lãi/Lỗ VND), `#pnl-total-pct` (Tỷ suất sinh lời %) với màu trạng thái trực quan (`.pnl-up` xanh lá khi lãi > 0, `.pnl-down` đỏ khi lỗ < 0, `.pnl-ref` xám khi hòa vốn).
     - **Form Thêm Cổ Phiếu Vào Danh Mục (`#portfolio-add-form`)**: 3 trường nhập dữ liệu gồm Mã cổ phiếu (`#portfolio-symbol`), Số lượng (`#portfolio-quantity`), Giá mua bình quân (`#portfolio-price`), và nút Thêm (`#portfolio-add-btn`).
     - **Bảng Danh Mục 7 Cột Chuẩn**: `Mã`, `SL`, `Giá vốn`, `Thị giá`, `Lãi/Lỗ`, `% Lời`, `Xóa`.
     - **Empty state & Error banner**: Báo trống lịch sự và thông báo lỗi rõ ràng nếu nhập liệu sai hoặc lỗi kết nối.
2. **Xử Lý Dữ Liệu & Bảo Vệ An Toàn XSS (`src/frontend/app.js`)**:
   - Hàm `loadPortfolio` nạp dữ liệu danh mục theo `getCurrentUserId()` (Header `X-User-ID`).
   - Tự động định dạng số tiền VND theo chuẩn Việt Nam (`toLocaleString("vi-VN") + " ₫"`).
   - Đảm bảo an toàn XSS tuyệt đối: toàn bộ mã chứng khoán và holding ID được khử độc qua `escapeHtml`.
   - Nút xóa cổ phiếu gắn sự kiện gọi `doDeleteHolding` với thông báo toast phản hồi tức thì.
3. **Mở Rộng Backend Router Aliases (`src/backend/api/routers/portfolio.py`)**:
   - Bổ sung các route aliases chuẩn hóa phục vụ đồng thời cho Web UI và tích hợp API Phase 4:
     - `@router.get("/api/portfolio")`, `@router.get("/api/v1/portfolio")`, `@router.get("/api/v1/portfolio/summary")`.
     - `@router.get("/api/portfolio/holdings")`, `@router.get("/api/v1/portfolio/holdings")`.
     - `@router.post("/api/portfolio/holdings")`, `@router.post("/api/v1/portfolio/holdings")`.
     - `@router.delete("/api/portfolio/holdings/{holding_id}")`, `@router.delete("/api/v1/portfolio/holdings/{holding_id}")`.
   - Đảm bảo cô lập dữ liệu 100% giữa các người dùng (`user_a`, `user_b`, `default`) tuân thủ nghiêm ngặt **AC-7**.
4. **Kiểm Thử Tự Động & Hồi Quy**:
   - Thêm bài test `test_phase2_portfolio_pnl_table_and_summary_cards` vào [`tests/test_system.py`](../tests/test_system.py).
   - Kiểm tra HTML elements, CSS classes, JavaScript logic, và API CRUD cho người dùng mới, thêm mã, xem tổng quan và xóa vị thế.
   - Chạy toàn bộ test suite: **185/185 tests PASS (100%)**, `prompt_lint` đạt OK.
   - **Chính thức hoàn thành 100% Phase 2: Core UI (các mục 2.1 đến 2.5)**.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Tab Danh mục hiển thị đầy đủ danh sách cổ phiếu nắm giữ: Mã, Số lượng, Giá vốn, Giá hiện tại, Lãi/Lỗ (VND), Tỷ suất (%) và Tổng NAV.
  - 3 thẻ tóm tắt P&L hiển thị số liệu chính xác với màu phân biệt lãi/lỗ/hòa vốn.
  - Form thêm vị thế hoạt động ổn định, xóa vị thế bằng nút thùng rác cập nhật tức thời.
  - Toàn bộ 185/185 bài kiểm thử của dự án đạt trạng thái PASS 100%.
  - Tính cô lập đa người dùng (AC-7) hoạt động tuyệt đối qua Header `X-User-ID`.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây thiếu endpoint danh sách vị thế `/api/v1/portfolio/holdings` và các route alias `/api/v1/portfolio/summary`; mã chứng khoán trong HTML bảng danh mục chưa được bọc qua `escapeHtml`. Hiện đã bổ sung và khắc phục triệt để.

---

## 2026-09-30 — Hoàn Thành Mục 2.4: Đồ Thị Mạng Lưới Live Agent Graph

### Chi Tiết Triển Khai
1. **Kiến Trúc 9 Node Canonical Swarm (`CANONICAL_GRAPH_NODES`) trong `src/frontend/app.js`**:
   - Khai báo mảng 9 node chuẩn: `Guardrail`, `Rewrite`, `Supervisor`, `PriceAgent`, `NewsAgent`, `IndicatorEngine`, `ChartAgent`, `EvalAgent`, `AnswerComposer`.
   - Mỗi node sở hữu nhãn tiếng Việt, vai trò hệ thống (`role`), icon đại diện (`🛡️`, `🔄`, `🧭`, `📈`, `📰`, `📐`, `📊`, `⚖️`, `✍️`) và cấu hình System Prompt / quy tắc xử lý tĩnh hoàn chỉnh trong `NODE_FALLBACK_PROMPTS`.
2. **Trạng Thái Sẵn Sàng (Idle State) & Khám Phá Tương Tác**:
   - Khi chưa có câu hỏi hoặc ở trạng thái chờ, đồ thị tự động vẽ toàn bộ 9 node ở trạng thái `status-idle` nối tiếp bằng mũi tên điều phối `→`.
   - Người dùng có thể di chuột (hover) hoặc bấm (click) ghim vào bất kỳ node nào để mở popover `I/O Inspector` xem trước System Prompt, vai trò và quy tắc xử lý tĩnh.
3. **Hiệu Ứng Highlight Node Động Trong Quá Trình Streaming**:
   - Khi nhận sự kiện SSE `node_start`: node tương ứng chuyển sang `status-running` kèm hiệu ứng phát sáng xung nhịp xanh dương (`node-glow-pulse`).
   - Khi nhận sự kiện SSE `node_finish`: node chuyển sang `status-done` kèm huy hiệu đo lường thời gian thực thi `⏱ ...s`.
   - Hàm `normalizeNodeName` và `canonicalNodeId` chuẩn hóa mọi tên sự kiện nội bộ từ LangGraph (`pre_rewrite_guardrail`, `rewrite_question`, `price_agent`, v.v.) thành tên hiển thị thân thiện trên UI.
4. **Bổ sung CSS Giao diện Graph (`src/frontend/style.css`)**:
   - Thêm định kiểu `.graph-node-card.status-idle` (nền sáng, chấm xám trung tính, viền thanh thoát).
5. **Kiểm thử tự động**:
   - Thêm bài test `test_phase2_live_agent_graph_and_node_inspector` vào [`tests/test_system.py`](../tests/test_system.py).
   - Thực thi trích xuất logic và chạy round-trip trên Node.js kiểm tra đủ 9 node, system prompt của từng node, hàm chuẩn hóa tên và hàm icon.
   - Chạy toàn bộ regression test suite: **184/184 tests PASS (100%)**, `prompt_lint` đạt OK.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Đồ thị hiển thị đầy đủ 9 node kiến trúc: `Guardrail`, `Rewrite`, `Supervisor`, `PriceAgent`, `NewsAgent`, `IndicatorEngine`, `ChartAgent`, `EvalAgent`, `AnswerComposer`.
  - Hiệu ứng phát sáng `node-glow-pulse` kích hoạt chính xác theo luồng streaming của Agent.
  - Hover / Click vào node hiển thị đầy đủ popover I/O Inspector: Node Name, trạng thái badge, System Prompt tĩnh, Input và Output.
  - Toàn bộ 184/184 bài kiểm thử của dự án đạt trạng thái PASS 100%.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây đồ thị chỉ hiển thị ô trống `Chờ câu hỏi để kích hoạt đồ thị` ở trạng thái idle khiến người dùng không nắm được kiến trúc 9 node; thiếu ánh xạ tên chuẩn hóa và icon riêng cho `IndicatorEngine` / `ChartAgent`. Hiện đã bổ sung đầy đủ và trực quan.

---

## 2026-09-30 — Hoàn Thành Mục 2.3: Khung Chat & Trình Kết Xuất Markdown

### Chi Tiết Triển Khai
1. **Bộ Trình Kết Xuất Markdown Thuần (`src/frontend/app.js`)**:
   - Xây dựng hàm `escapeHtml` và `renderMarkdown` thuần JavaScript (Zero dependency), an toàn XSS tuyệt đối.
   - Hỗ trợ đầy đủ các định dạng:
     - **In đậm & In nghiêng**: `**văn bản**`, `*nghiêng*`.
     - **Bảng dữ liệu chứng khoán**: Chuyển đổi cú pháp table Markdown sang `<table class="chat-markdown-table">` bọc trong thẻ cuộn ngang responsive `.chat-table-wrap`.
     - **Khối mã & Inline code**: `<pre class="chat-code-block"><code class="language-...">`, escape triệt để ký tự HTML.
     - **Biểu đồ nến & Ảnh tài chính**: Cú pháp `![alt](/static/charts/...png)` tự động tạo container `.chat-chart-container` và gắn sự kiện click mở modal phóng to ảnh `openChartModal`.
     - **Tiêu đề & Trích dẫn**: Headings `#` đến `####`, blockquote `> ...` phục vụ hiển thị khuyến cáo rủi ro / disclaimer.
     - **Danh sách**: Hỗ trợ danh sách không thứ tự (`- `, `* `) và có thứ tự (`1. `).
   - Tích hợp vào `appendChat`: Áp dụng cho tin nhắn `role === "assistant"`, tránh trùng lặp nếu biểu đồ đã nhúng trong Markdown; xuất `window.PW_renderMarkdown` và `window.PW_escapeHtml`.
2. **Bổ sung CSS Giao diện Markdown (`src/frontend/style.css`)**:
   - Định kiểu `.msg-text.markdown-body`, bảng `.chat-markdown-table` (zebra striping, hover row, header tương phản), khối mã `.chat-code-block` nền tối, blockquote `.chat-blockquote` viền xanh thương hiệu.
3. **Kiểm thử tự động**:
   - Thêm bài test `test_phase2_chat_markdown_rendering` vào [`tests/test_system.py`](../tests/test_system.py).
   - Thực thi trích xuất logic và chạy round-trip trên Node.js với văn bản Markdown phân tích cổ phiếu mẫu, kiểm tra tính toàn vẹn của thẻ HTML, bảng dữ liệu, khối code và kiểm tra chặn XSS.
   - Chạy toàn bộ regression test suite: **183/183 tests PASS (100%)**, `prompt_lint` đạt OK.

### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
- **What Passes**:
  - Giao diện chat hiển thị đầy đủ tin nhắn người dùng và trợ lý, hỗ trợ Markdown in đậm, bảng dữ liệu, khối code, thẻ ảnh biểu đồ `/static/charts/...`.
  - Khung chat scrollable mượt mà, con trỏ gõ chữ typing streaming hoạt động ổn định.
  - Chống XSS an toàn 100% (mã script bị escape an toàn thành `&lt;script&gt;`).
  - Toàn bộ 183/183 bài kiểm thử tự động đạt trạng thái PASS 100%.
- **What Fails**: 0 lỗi.
- **What Was Missing & Fixed**: Trước đây chat chỉ dùng `textContent` thuần túy khiến bảng dữ liệu và code block của trợ lý bị hiển thị dưới dạng chuỗi thô; thiếu CSS cho table và blockquote. Hiện đã khắc phục triệt để.

---

## 2026-09-30 — Khởi Tạo Hồ Sơ SDD: Monorepo Flattening & Comprehensive Multi-Agent Update

### Bối Cảnh & Yêu Cầu Người Dùng
1. **Kiểm tra và xác định toàn bộ chức năng hiện tại**: Lập danh mục chi tiết 12 phân hệ tính năng sẵn có của hệ thống Multi-Agent Swarm (LangGraph).
2. **Chuẩn hóa cấu trúc Monorepo**: Lên kế hoạch đưa toàn bộ mã nguồn, cấu hình, dữ liệu và tài nguyên từ thư mục con `llm-backend-ref-portfolio-watch/` ra thư mục gốc `vn-stock-swarm/`.
3. **Bộ Golden Dataset mới toàn diện**: Thiết kế tập dữ liệu đánh giá mới gồm 10 lát cắt chức năng (`lookup`, `news`, `indicator`, `comparison`, `portfolio`, `watchlist`, `chart`, `out_of_scope`, `injection`, `disclaimer`) với tiêu chí tối giản nhưng bao quát 100% tình huống thực tế.
4. **Quy trình quan sát định lượng (Observation & Trace)**: Thiết lập kế hoạch thu thập thông số tokens, chi phí USD, độ trễ latency và chuỗi trace qua các Agent.
5. **Kịch bản Demo chuẩn 100%**: Xây dựng kịch bản 10 bước kiểm thử đầu cuối bảo đảm trình diễn thành công trên giao diện Web UI.

### Các File Đặc Tả Được Khởi Tạo Trước Khi Viết Code
- [`README.md`](../README.md): Bản tổng quan dự án toàn diện, kiến trúc Swarm, danh mục chức năng và hướng dẫn cài đặt chạy cục bộ.
- [`AGENTS.md`](../AGENTS.md): Bản quy tắc hành xử và nguyên tắc cốt lõi dành cho AI Coding Assistant theo chuẩn SDD.
- [`specs/product-spec.md`](product-spec.md): Đặc tả sản phẩm, danh mục 12 phân hệ chức năng, 10 lát cắt dataset, phạm vi in/out of scope và 10 tiêu chí nghiệm thu (AC-1 đến AC-10).
- [`specs/implementation-plan.md`](implementation-plan.md): Kế hoạch triển khai 7 Phase chi tiết bám sát MVP.
- [`specs/test-plan.md`](test-plan.md): Chiến lược kiểm thử 4 tầng, tiêu chí chấm điểm golden dataset, quan sát định lượng và kịch bản demo 10 bước.
- [`specs/change-log.md`](change-log.md): Khởi tạo nhật ký theo dõi tiến trình dự án.

### Trạng Thái Hiện Tại
- **Phase 1: Project Setup (Monorepo Flattening & Môi Trường)**: **HOÀN THÀNH 100%**.
- **Phase 2: Core UI**:
  - **Mục 2.1 (Kiểm tra cấu trúc tài nguyên Frontend & Mount static)**: **HOÀN THÀNH 100%**. Đã xác nhận `index.html`, `app.js`, `style.css`, `config.js` tại root và mount cả `/charts` lẫn `/static/charts`.
  - **Mục 2.2 (Kiểm tra bộ chuyển đổi người dùng User Switcher)**: **HOÀN THÀNH 100%**. Đã thay thế biến tĩnh `USER_ID` bằng hàm động `getCurrentUserId()`, gắn header `X-User-ID`, kích hoạt reload toàn bộ dữ liệu khi đổi user và kiểm chứng đạt AC-7.
- **Sẵn sàng**: Sẵn sàng thực hiện tiếp mục 2.3 (Khung Chat & Trình Kết Xuất Markdown) khi người dùng yêu cầu.

---

## 2026-09-30 — Hoàn Thành Mục 2.2: Bộ Chuyển Đổi Người Dùng (User Switcher) & Cô Lập Dữ Liệu (AC-7)

### Chi Tiết Triển Khai
1. **Chuẩn hóa Dynamic User ID trong Frontend (`src/frontend/app.js`)**:
   - Khắc phục lỗi hằng số tĩnh `const USER_ID = getCurrentUserId()` được gán 1 lần duy nhất lúc khởi động trang.
   - Thay thế toàn bộ các lời gọi API (`/watchlist`, `/approvals`, `/market`, `/chat`, `/portfolio`, `/sessions`) sang sử dụng hàm động `getCurrentUserId()`.
   - Hàm `setCurrentUserId(newId)` đồng bộ giá trị với `localStorage.getItem("PW_CURRENT_USER_ID")`, nhãn `portfolio-user-badge` và dropdown `user-switcher-select`.
   - Bổ sung cơ chế tự động nạp lại dữ liệu tương ứng của tenant mới khi chuyển đổi tài khoản (`loadSessions`, `loadWatchlist`, `loadMarket`, `loadApprovals`, `loadPortfolio`).
2. **Kiểm thử tự động**:
   - Thêm test case `test_phase2_user_switcher_wiring_and_tenant_isolation` vào [`tests/test_system.py`](../tests/test_system.py).
   - Kiểm tra UI select element, options (`user_a`, `user_b`, `default`), persistence `PW_CURRENT_USER_ID`, header `X-User-ID`.
   - Kiểm chứng API: Thêm mã `FPT` cho `user_a` -> kiểm tra `user_b` không bị lẫn dữ liệu của `user_a` (xác thực tiêu chí **AC-7**).
3. **Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)**:
   - **What Passes**:
     - Dropdown `#user-switcher-select` hoạt động chuẩn xác, lưu trữ `localStorage` và tự động gắn header `X-User-ID`.
     - Tiêu chí **AC-7 (Cô Lập Đa Người Dùng Tuyệt Đối)** đạt **PASS** 100%.
     - Test case `test_phase2_user_switcher_wiring_and_tenant_isolation` đạt **PASS** (0.09s).
   - **What Fails**: 0 lỗi.
   - **What Was Missing & Fixed**: Đã phát hiện và sửa triệt để việc dùng biến tĩnh `USER_ID` thay vì gọi động `getCurrentUserId()`, giúp thay đổi user có hiệu lực ngay lập tức cho các request tiếp theo mà không cần reload trình duyệt.
   - Đã đánh dấu hoàn thành `[x]` cho **Mục 2.2** trong [`specs/implementation-plan.md`](implementation-plan.md) và tiêu chí **AC-7** trong [`specs/product-spec.md`](product-spec.md).

---

## 2026-09-30 — Hoàn Thành Mục 2.1: Cấu Trúc Tài Nguyên Frontend & Mount Tĩnh

### Chi Tiết Triển Khai
1. **Kiểm tra và chuẩn hóa tệp giao diện**:
   - Xác nhận sự hiện diện của các tệp tĩnh tại `src/frontend/`: `index.html`, `app.js`, `style.css`, `config.js`.
   - Cập nhật [`src/backend/main.py`](../src/backend/main.py): Bổ sung route mount tĩnh `app.mount("/static/charts", StaticFiles(...))` song song với `/charts` để đảm bảo tương thích đường dẫn hình ảnh biểu đồ nến kỹ thuật khi render Markdown.
2. **Kiểm thử tự động**:
   - Thêm bài test `test_phase2_frontend_static_serving_and_mime_types` vào [`tests/test_system.py`](../tests/test_system.py).
   - Kiểm tra mã phản hồi HTTP 200, MIME types (`text/html`, `text/css`, `application/javascript`) và sự hiện diện của cả 2 mount `/charts` và `/static/charts`.
3. **Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)**:
   - **What Passes**: Giao diện SPA tải thành công tại `/`, các tệp tĩnh và hình ảnh biểu đồ được phục vụ chuẩn xác với mã 200. Toàn bộ 5 bài test frontend trong `tests/test_system.py` đều PASS.
   - **What Fails**: 0 lỗi.
   - **What Was Missing & Fixed**: Đã thêm mount alias `/static/charts` tránh trường hợp liên kết ảnh Markdown dạng `/static/charts/chart_xyz.png` bị trả về 404.

---

## 2026-09-30 — Hoàn Thành Phase 1: Project Setup (Monorepo Flattening)

### Chi Tiết Triển Khai
1. **Di chuyển tệp & thư mục ra root**:
   - `src/` (toàn bộ backend, frontend static files, main app)
   - `tests/` (180 bài unit & integration tests)
   - `resources/` (prompts, eval golden datasets)
   - `wheels/` (`vnstock`, `vnai`, `vnstock_ezchart`)
   - `deploy/` (smoke test, nginx configuration)
   - `data/` (SQLite databases: `portfolio_watch.db`, `backend_store.db`)
   - `docs/` (tài liệu SDD guide, methodologies, mapping)
   - `scripts/` (các script hỗ trợ changelog, plan, runner)
   - Cấu hình gốc: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`, `.gitattributes`, `.pre-commit-config.yaml`, `Modelfile`.
2. **Cập nhật CI/CD Workflows (`.github/workflows/`)**:
   - `ci.yml`: Chạy trực tiếp tại root, cache pip dựa trên `pyproject.toml`, paths giám sát `src/**`, `tests/**`, `resources/**`, `wheels/**`, `pyproject.toml`.
   - `eval-gate.yml`: Bỏ tiền tố thư mục con, cache `.eval_cache`, paths `resources/prompts/**`, `src/backend/**`, `resources/eval/**`.
   - `cd.yml`: Docker compose build và smoke test chạy trực tiếp tại root.
### Đánh Giá Tiêu Chí Nghiệm Thu (Acceptance Criteria Review)
Đối chiếu với [specs/product-spec.md](product-spec.md) và [specs/test-plan.md](test-plan.md):

* **What Passes (Đã đạt chuẩn)**:
  - **AC-1 (Monorepo Flattening)**: Toàn bộ cây thư mục đã phẳng tại `vn-stock-swarm/`, không còn thư mục con `llm-backend-ref-portfolio-watch/`. `test_legacy_subfolder_removed` kiểm chứng pass.
  - **AC-2 (Test Suite 100% Pass)**: Chạy lệnh `pytest tests/ -v`, 180/180 test cases đạt trạng thái PASS 100%, thời gian chạy 213s, không có hồi quy.
  - **AC-3 (CI/CD Pipeline Chuyển Xanh)**: 4 tests trong `tests/test_ci_workflows.py` xác nhận `ci.yml`, `eval-gate.yml`, `cd.yml` cấu hình đúng chuẩn root.
  - **Prompt Lint**: Lệnh `python -m backend.infra.llm.prompt_lint resources/prompts/` đạt OK 100%.
  - **Tài liệu & Lệnh chạy**: `README.md` cung cấp đầy đủ cả 2 phương thức chạy local uvicorn và Docker Compose.
* **What Fails (Thất bại)**:
  - Không có (0 failures, 180 passed).
* **What Was Missing & Fixed (Thiếu sót đã xử lý)**:
  - Đã cập nhật đánh dấu hoàn thành `[x]` cho **AC-1**, **AC-2**, **AC-3** trong `specs/product-spec.md`.
  - Không phát sinh code thừa hay tính năng ngoài phạm vi Phase 1.

---

## Lịch Sử Thay Đổi Trước Đó (Tóm Tắt)

* **2026-09-30 (CI/CD Hotfix)**: Sửa lỗi thiếu wheel `vnstock` offline trong GitHub Actions (`ci.yml`, `eval-gate.yml`), cập nhật tương thích assertion `USER appuser` và xử lý graceful fallback cho secret `OPENAI_API_KEYS`. Kết quả: CI Pipeline và Eval Gate chuyển sang trạng thái PASS (Green 100%).
* **2026-09-30 (Bugfix Chat VNM)**: Khắc phục lỗi quyền ghi SQLite `readonly database` bằng `docker-entrypoint.sh`, bổ sung alias `v1` cho PromptRegistry, bổ sung stopwords loại bỏ mã ảo (GIA, TAI, TIA, HIEN, TOI).
* **2026-09-30 (Phase 8)**: Hoàn thành Regression Gate, bổ sung kịch bản kiểm thử ngrok demo và operational runbooks.
* **2026-09-30 (Phase 7)**: Bổ sung xử lý lỗi giá fallback, empty state và decomposition fallback trong supervisor agent.
