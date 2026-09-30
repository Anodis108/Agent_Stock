# Product Spec — Portfolio Watch & Management (MVP 2.0)

## App Name
**Portfolio Watch & Management — Multi-Agent Stock Assistant (MVP 2.0)**

---

## 1. App Goal
Xây dựng trợ lý phân tích và quản lý danh mục cổ phiếu Việt Nam (MVP) bằng hệ thống Swarm Multi-Agent:
- **Quản lý danh mục & Lãi/Lỗ thực tế (P&L):** Theo dõi số lượng cổ phiếu nắm giữ, giá vốn mua vào, tính toán Unrealized P&L, % sinh lời và tổng tài sản ròng (NAV).
- **Hỗ trợ đa người dùng (Multi-tenant):** Mỗi người dùng sở hữu danh mục theo dõi (Watchlist) và ngưỡng cảnh báo biến động (`alert_threshold_pct`) riêng biệt trong SQLite.
- **Đánh giá bất thường đáng tin cậy (EvalAgent):** Kết hợp phân tích kỹ thuật định lượng (RSI 14, SMA 20/50, Golden/Death Cross) cùng tin tức đa nguồn (Vnstock News, CafeF/Vietstock).
- **Xử lý câu hỏi phức tạp (Query Decomposition):** Phân rã các câu hỏi multihop, so sánh đa mã hoặc đa ý hỏi thành các sub-queries độc lập để các Agent xử lý trọn vẹn, không bỏ sót thông tin.
- **Đo lường định lượng chất lượng Agent (Agent Evaluation):** Tích hợp công cụ benchmark tự động (`agent_eval.py`) đo lường Routing, Decomposition, Groundedness và Task Success.

---

## 2. Target Users
1. **Nhà đầu tư cá nhân tại thị trường chứng khoán Việt Nam:**
   - Theo dõi lãi/lỗ danh mục thực tế hằng ngày và nhận cảnh báo rủi ro biến động giá.
   - Đặt câu hỏi tự nhiên (câu đơn lẻ hoặc câu hỏi so sánh phức tạp) và nhận câu trả lời streaming nhanh chóng, có căn cứ kỹ thuật và tin tức.
2. **Kỹ sư AI / Nhà phát triển Agent:**
   - Đánh giá định lượng chất lượng của Swarm Agent và ngăn ngừa lỗi suy giảm chất lượng (regression) khi cập nhật prompt hoặc code.

---

## 3. Core User Flow
1. **Chọn người dùng:** Người dùng chọn tài khoản trên giao diện (ví dụ: `User A`, `User B`, `Default`). Hệ thống tải danh mục, watchlist và cài đặt ngưỡng riêng của user đó.
2. **Quản lý danh mục & Xem P&L:** Người dùng mở bảng Danh mục để xem số lượng, giá vốn, thị giá hiện tại, Lãi/Lỗ (VND) và % Tỷ suất sinh lời. Người dùng có thể thêm hoặc xóa vị thế nắm giữ.
3. **Chat tra cứu & Phân tích:**
   - Người dùng hỏi câu hỏi đơn (*"Giá FPT hôm nay"*) hoặc phức tạp (*"So sánh biến động và tin tức FPT với HPG"*).
   - Guardrail lọc an toàn ➔ Rewrite chuẩn hóa ngữ cảnh và phân rã thành các sub-queries (nếu phức tạp) ➔ Supervisor điều phối worker agents tương ứng (Price, News, Indicator, Chart) ➔ EvalAgent kết hợp chỉ báo kỹ thuật & tin tức đánh giá rủi ro ➔ AnswerComposer trả lời streaming (SSE).
4. **Đánh giá chất lượng hệ thống:** Kỹ sư chạy lệnh `python scripts/run_agent_eval.py` để chấm điểm tự động toàn diện hệ thống.

---

## 4. Features In Scope (MVP Focus)
- **Multi-tenant Isolation:** Phân tách Watchlist, Holdings và User Settings theo `user_id` trong SQLite. Nhận diện user qua header `X-User-ID` hoặc User Switcher trên UI.
- **Portfolio P&L Tracking:**
  - Lưu trữ: `symbol`, `quantity`, `avg_buy_price`, `purchase_date`.
  - Tự động tính: Giá trị vốn, Thị giá hiện tại, Lãi/Lỗ chưa thực hiện (VND), Tỷ suất (%), Tổng NAV danh mục.
- **Technical Indicators & Multi-source News Cho EvalAgent:**
  - Tính toán: RSI (14), SMA (20), SMA (50), Golden Cross / Death Cross.
  - Tổng hợp tin tức từ Vnstock News API và nguồn bổ trợ.
  - Cung cấp dữ liệu chỉ báo kỹ thuật cho EvalAgent để xác định mức độ bất thường (`high`, `medium`, `low`, `none`).
- **Rewrite & Query Decomposition (Multi-Subquery):**
  - Tự động phân rã câu hỏi phức tạp thành 2–4 `sub_questions` độc lập kèm mã đầy đủ.
  - Supervisor điều phối thu thập đầy đủ dữ liệu cho từng sub-query (không bỏ sót mã hoặc khía cạnh được hỏi).
- **Agent Evaluation Framework (`agent_eval.py`):**
  - Benchmark tự động chấm 4 chỉ số: Routing Accuracy, Decomposition Quality, Groundedness (chống hallucination) và Task Success Rate.
- **Nền tảng sẵn có:** Chat Streaming SSE, hiển thị System Prompt/Static info khi hover node trên Live Graph, vẽ biểu đồ Matplotlib, Guardrails Zero-Tolerance.

---

## 5. Features Out of Scope
- Hệ thống Authentication đầy đủ (JWT, OAuth2, Email confirmation, đổi mật khẩu) — dùng User Switcher / Header `X-User-ID` cho MVP.
- Tích hợp tài khoản giao dịch tại các công ty chứng khoán để đặt lệnh mua/bán thật.
- Dữ liệu Realtime WebSocket tick-by-tick (vẫn sử dụng dữ liệu nến ngày 1D và giá khớp lệnh gần nhất).
- Quản lý margin, tính thuế TNCN, phí giao dịch chi tiết và phân bổ cổ tức.

---

## 6. Acceptance Criteria
- [x] **AC-1 (Cô lập đa người dùng):** Thao tác thêm/xóa mã trong Watchlist, Holdings và thay đổi ngưỡng của `user_a` không làm thay đổi dữ liệu của `user_b`.
- [x] **AC-2 (Tính P&L chính xác):** Với 1,000 FPT mua giá 100.0 khi thị giá là 120.0, bảng hiển thị đúng Lãi `+20,000,000 VND` (+20.0%) và tính đúng tổng NAV danh mục.
- [x] **AC-3 (EvalAgent có chỉ báo kỹ thuật):** Khi phân tích cổ phiếu có biến động mạnh, EvalAgent nhận được RSI(14) và trạng thái MA20/MA50 trong context để đưa ra lý giải định lượng, thuyết phục.
- [x] **AC-4 (Xử lý đa sub-query hoàn chỉnh):** Khi hỏi câu hỏi so sánh hoặc đa ý (ví dụ: *"So sánh giá và tin tức của FPT và HPG"*), hệ thống phân rã thành các câu hỏi con, Supervisor gọi đầy đủ worker cho cả 2 mã và câu trả lời bao quát trọn vẹn cả 2 khía cạnh.
- [x] **AC-5 (Agent Evaluation hoạt động):** Chạy `agent_eval.py` thành công và xuất báo cáo chấm điểm chi tiết đạt chuẩn $\ge 85\%$.
- [x] **AC-6 (Bảo vệ an toàn 100%):** 100% câu hỏi Prompt Injection và Out-of-scope bị chặn fail-closed lịch sự.
- [x] **AC-7 (Không lỗi hồi quy):** Toàn bộ 176 unit tests hiện tại tiếp tục PASS 100%.
- [x] **AC-8 (Giao diện trực quan):** Web UI có thanh chuyển đổi người dùng (User Switcher) và tab hiển thị bảng danh mục P&L rõ ràng.
