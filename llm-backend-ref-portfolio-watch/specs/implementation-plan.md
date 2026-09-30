# Implementation Plan — Portfolio Watch & Management (MVP 2.0)

Kế hoạch triển khai theo phương pháp **Spec-Driven Development** (SDD), chia thành các phase nhỏ, khả thi và bám sát phạm vi MVP.

---

## Nguyên Tắc Thực Hiện Bắt Buộc
1. **Chỉ triển khai một phase hoặc một task tại một thời điểm**: Tuyệt đối không làm lan man sang phase khác.
2. **Không viết code trước khi có yêu cầu**: Chỉ bắt đầu code khi bước tương ứng được người dùng chỉ định.
3. **Cập nhật Change Log & Đánh dấu Checklist**: Sau mỗi phase/task hoàn thành, cập nhật `specs/change-log.md` và đánh dấu `[x]`.
4. **Hướng dẫn kiểm thử rõ ràng**: Mỗi thay đổi phải đi kèm hướng dẫn test cụ thể (lệnh chạy, kết quả mong đợi).

---

## Phase 1: Database Schema & Multi-tenant Models
Mục tiêu: Mở rộng SQLite database để lưu trữ vị thế danh mục và cài đặt ngưỡng theo từng người dùng.
- [x] **Task 1.1:** Tạo bảng `portfolio_holdings` trong SQLite (`src/backend/database/schema.py`):
  - Các trường: `id`, `user_id`, `symbol`, `quantity`, `avg_buy_price`, `purchase_date`, `created_at`, `updated_at`.
- [x] **Task 1.2:** Cập nhật bảng `watchlist` và thêm bảng `user_settings`:
  - `watchlist`: bổ sung trường `user_id` (mặc định `'default'`).
  - `user_settings`: lưu `user_id`, `alert_threshold_pct` (mặc định `3.0%`).
- [x] **Task 1.3:** Xây dựng `PortfolioHoldingRepository` và nâng cấp `WatchlistRepository` trong `src/backend/database/repositories.py`.
- [x] **Task 1.4:** Viết unit tests kiểm tra CRUD holdings và cô lập dữ liệu theo `user_id` trong `tests/test_database.py`.
- [x] **Verification:** Chạy `pytest tests/test_database.py -v` đảm bảo 100% tests PASS (10/10 tests passed).

---

## Phase 2: Portfolio P&L Service & API Endpoints
Mục tiêu: Tính toán lãi/lỗ danh mục tự động và cung cấp API REST cho frontend.
- [x] **Task 2.1:** Xây dựng `PortfolioService` (`src/backend/application/portfolio_service.py`):
  - Lấy danh sách vị thế nắm giữ của `user_id`.
  - Kết nối `PriceSource` lấy thị giá đóng cửa mới nhất từ Vnstock.
  - Tính toán: Market Value, Cost Basis, Unrealized P&L (VND), Tỷ suất lợi nhuận (%), Tổng NAV danh mục.
- [x] **Task 2.2:** Xây dựng Router API `src/backend/api/routers/portfolio.py`:
  - `GET /api/portfolio`: Trả về tổng quan danh mục và chi tiết P&L từng mã theo `user_id`.
  - `POST /api/portfolio/holdings`: Thêm/cập nhật vị thế mua cổ phiếu.
  - `DELETE /api/portfolio/holdings/{id}`: Xóa vị thế khỏi danh mục.
  - `GET /api/user/settings` & `PUT /api/user/settings`: Lấy và cập nhật ngưỡng cảnh báo riêng của user.
- [x] **Task 2.3:** Hỗ trợ nhận diện người dùng MVP qua HTTP Header `X-User-ID` hoặc query param `user_id`.
- [x] **Task 2.4:** Viết unit tests cho các endpoint portfolio trong `tests/test_api.py`.
- [x] **Verification:** Chạy `pytest tests/test_api.py -v` đảm bảo các endpoint portfolio hoạt động chính xác (15/15 passed).

---

## Phase 3: Technical Indicators & Multi-source News Cho EvalAgent
Mục tiêu: Trang bị cho EvalAgent các chỉ báo kỹ thuật định lượng và tin tức đa nguồn để đánh giá bất thường chính xác.
- [x] **Task 3.1:** Xây dựng module tính toán chỉ báo kỹ thuật (`src/backend/domain/indicators.py`):
  - Hàm tính `compute_rsi(closes, period=14)`.
  - Hàm tính `compute_sma(closes, period=20)` và `compute_sma(closes, period=50)`.
  - Hàm phân tích trạng thái: Quá mua (`RSI > 70`), Quá bán (`RSI < 30`), Tín hiệu giao cắt MA (`Golden Cross` / `Death Cross`).
- [x] **Task 3.2:** Mở rộng `NewsSource` hỗ trợ tin tức đa nguồn (Vnstock News API + RSS CafeF/Vietstock).
- [x] **Task 3.3:** Nâng cấp `EvalAgent`:
  - Nạp các thông số kỹ thuật (RSI, MA Cross, xu hướng) và tin tức đa nguồn vào input của `eval_agent`.
  - Cập nhật prompt template `eval_severity` để kết hợp phân tích kỹ thuật và tin tức doanh nghiệp khi đưa ra mức độ nghiêm trọng (`high`, `medium`, `low`, `none`).
- [x] **Task 3.4:** Viết unit tests kiểm tra tính chính xác của thuật toán RSI/MA và logic phân loại của `eval_agent` trong `tests/test_agents.py`.
- [x] **Verification:** Chạy `pytest tests/test_agents.py -k "indicator or eval"` đảm bảo PASS.

---

## Phase 4: Rewrite & Query Decomposition Cho Đa Sub-query
Mục tiêu: Nâng cao độ chính xác khi xử lý câu hỏi phức tạp bằng cách phân rã và điều phối xử lý trọn vẹn từng sub-query.
- [x] **Task 4.1:** Hoàn thiện Query Decomposition trong `rewrite_question`:
  - Prompt chỉ dẫn phân rã rõ ràng: nếu câu hỏi chứa nhiều thực thể (so sánh 2–3 mã) hoặc nhiều yêu cầu (vừa hỏi giá vừa hỏi tin tức vừa hỏi kỹ thuật), phân rã thành 2–4 `sub_questions` độc lập, rõ nghĩa.
  - Đảm bảo mỗi sub-question đều có mã cổ phiếu và ý định cụ thể.
- [x] **Task 4.2:** Nâng cấp Supervisor Routing xử lý đa Sub-queries:
  - Supervisor duyệt qua danh sách `sub_questions` và tổng hợp danh sách tất cả các agents cần gọi (`agents_to_call`), đảm bảo không bỏ sót bất kỳ worker nào.
  - Hỗ trợ gọi các worker song song (Fan-out) theo từng mã xuất hiện trong các sub-queries (ví dụ: `prices: [FPT, HPG]`, `news_list: [FPT, HPG]`).
- [x] **Task 4.3:** Nâng cấp AnswerComposer tổng hợp đa nguồn (Multi-evidence Synthesis):
  - AnswerComposer nhận đầy đủ kết quả từ tất cả các sub-queries.
  - Trả lời có cấu trúc rõ ràng theo từng câu hỏi con (ví dụ: mục so sánh giá, mục so sánh tin tức), không bị thiên vị hay bỏ sót thông tin.
- [x] **Task 4.4:** Viết unit tests kiểm tra luồng phân rã câu hỏi và điều phối đa sub-query trong `tests/test_agents.py`.
- [x] **Verification:** Chạy `pytest tests/test_agents.py -k "sub_question or decompose"` đảm bảo PASS.

---

## Phase 5: Agent Evaluation Framework (`agent_eval.py`)
Mục tiêu: Tái sử dụng và tích hợp framework đánh giá chất lượng agent từ `llm-backend-ref`.
- [x] **Task 5.1:** Tích hợp module `agent_eval.py` vào `src/backend/eval/agent_eval.py`.
- [x] **Task 5.2:** Xây dựng bộ tiêu chí đánh giá tự động (Evaluation Metrics):
  - **Routing Precision/Recall**: Supervisor phân phối đúng tác vụ tới các worker.
  - **Query Decomposition Quality**: Tách câu hỏi phức tạp thành các câu con rõ nghĩa, đầy đủ ngữ cảnh.
  - **Groundedness Score**: Câu trả lời của AnswerComposer bám sát facts từ Price, News, Indicators, không bịa đặt.
  - **Task Success Rate**: Tỷ lệ trả lời hoàn chỉnh câu hỏi của người dùng.
- [x] **Task 5.3:** Xây dựng script thực thi `scripts/run_agent_eval.py` xuất báo cáo tổng quan (JSON & Markdown format).
- [x] **Task 5.4:** Đưa kiểm tra đánh giá Agent vào cổng chất lượng `tests/test_eval.py`.
- [x] **Verification:** Chạy `python scripts/run_agent_eval.py --sample 5` kiểm tra benchmark chạy thông suốt.

---

## Phase 6: Frontend UI Enhancements & Multi-tenant Switcher
Mục tiêu: Bổ sung giao diện Quản lý danh mục P&L và bộ chuyển đổi người dùng (User Switcher).
- [x] **Task 6.1:** Thêm thanh điều khiển **User Switcher** ở thanh tiêu đề Web UI (`src/frontend/index.html` & `app.js`):
  - Dropdown chọn nhanh: `User A`, `User B`, `Default`.
  - Tự động gắn header `X-User-ID` vào các request API tương ứng.
- [x] **Task 6.2:** Thêm Tab **Quản Lý Danh Mục (P&L)**:
  - Hiển thị 3 thẻ tóm tắt: Tổng giá trị tài sản (NAV), Tổng Lãi/Lỗ (VND), Tỷ suất lợi nhuận toàn danh mục (%).
  - Bảng danh mục cổ phiếu: Mã, Số lượng, Giá mua, Thị giá hiện tại, Lãi/Lỗ VND, % Sinh lời, Thao tác Thêm/Xóa mã.
- [x] **Task 6.3:** Cập nhật Live Graph & I/O Inspector:
  - Hiển thị danh sách `sub_questions` trong mục Output của `rewrite_question`.
  - Hiển thị kết quả tính toán RSI/MA trong mục I/O của `eval_agent`.
  - Bảo toàn chức năng hover/click hiển thị đầy đủ System Prompt / Thông tin tĩnh.
- [x] **Verification:** Mở giao diện trên trình duyệt, chuyển đổi user và thử thêm/xóa mã trong bảng danh mục.

---

## Phase 7: Validation, Error States & Edge Cases
Mục tiêu: Đảm bảo hệ thống xử lý mượt mà các trường hợp biên và dữ liệu bất thường.
- [x] **Task 7.1:** Xử lý trường hợp mã cổ phiếu không tồn tại trong danh mục P&L:
  - Hiển thị thông báo lỗi rõ ràng, đánh dấu `price_error`, không làm crash giao diện danh mục.
- [x] **Task 7.2:** Xử lý trường hợp người dùng mới chưa có danh mục (Empty State):
  - Hiển thị hướng dẫn trực quan: *"Danh mục đang trống. Hãy thêm mã cổ phiếu đầu tiên của bạn!"*.
- [x] **Task 7.3:** Xử lý trường hợp câu hỏi phức tạp không thể phân rã:
  - Fallback an toàn về chính câu hỏi gốc, tiếp tục luồng xử lý thông thường.
- [x] **Task 7.4:** Viết tests kiểm tra các trường hợp biên trong `tests/test_api.py`.
- [x] **Verification:** Chạy `pytest tests/` đảm bảo không có unhandled exceptions.

---

## Phase 8: Regression Gate, Local Run & ngrok Demo Readiness
Mục tiêu: Đảm bảo toàn bộ hệ thống hoạt động ổn định, không lỗi hồi quy và sẵn sàng demo.
- [ ] **Task 8.1:** Chạy lại toàn bộ test suite (`pytest tests/ -v`), đảm bảo 100% tests PASS (>= 145 tests).
- [ ] **Task 8.2:** Kiểm tra hồi quy bảo vệ an toàn: 100% câu hỏi Prompt Injection và Out-of-scope tiếp tục bị chặn fail-closed.
- [ ] **Task 8.3:** Cập nhật tài liệu hướng dẫn vận hành trong `README.md` với các lệnh chạy mới.
- [ ] **Task 8.4:** Kiểm thử mở tunnel ngrok bằng `python scripts/start_ngrok_demo.py` và kiểm tra truy cập từ thiết bị bên ngoài.
- [ ] **Verification:** Kiểm tra báo cáo cuối cùng đạt toàn bộ Acceptance Criteria trong `specs/product-spec.md`.
