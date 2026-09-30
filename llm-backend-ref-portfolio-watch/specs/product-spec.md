# Product Spec

## App Name
**Portfolio Watch — Multi-Agent Stock Assistant (Testing & Self-Correction MVP)**

---

## Goal
Xây dựng và hoàn thiện ứng dụng web MVP cho phép theo dõi, tra cứu cổ phiếu Việt Nam qua **Multi-Agent Swarm**, đồng thời **thực hiện kiểm thử toàn bộ 40 câu hỏi và chức năng hiện tại của ứng dụng, phát hiện và sửa chữa tận gốc các lỗi phát sinh**.

- **Cho người dùng:** Nhận câu trả lời streaming nhanh chóng, chính xác về giá, tin tức, phân tích biến động và biểu đồ cổ phiếu; đảm bảo an toàn thông tin (chặn câu hỏi ngoài phạm vi và bẻ khóa).
- **Cho hệ thống kiểm thử & QA:** Tự động hóa đánh giá toàn bộ 40 câu hỏi chuẩn hóa (Golden Dataset v5), phát hiện các ca thất bại và tiến hành sửa lỗi trong logic agent/prompt để đạt tỷ lệ hoàn thành cao nhất.

---

## Target Users
1. **Nhà đầu tư cá nhân:**
   - Tra cứu nhanh thị giá, biến động, tin tức doanh nghiệp niêm yết (FPT, VNM, HPG, SSI, ...).
   - Hỏi nối tiếp theo ngữ cảnh tự nhiên (Turn 1 ➔ Turn 2).
   - Xem biểu đồ kỹ thuật 10 phiên và sơ đồ phân tích.
2. **Kỹ sư AI / Kiểm thử viên (Tester & Developer):**
   - Chạy kiểm thử tự động toàn diện trên bộ câu hỏi chuẩn.
   - Theo dõi luồng xử lý (trace nodes) của từng Agent.
   - Đảm bảo hệ thống đạt chuẩn chất lượng trước khi bàn giao.

---

## Core User Flow
1. **Mở ứng dụng:** Người dùng truy cập giao diện web (`http://localhost:3000` hoặc `:8000`).
2. **Tra cứu thông tin (Turn 1):** Người dùng nhập câu hỏi (ví dụ: *"Giá FPT hôm nay bao nhiêu?"*).
   - Hệ thống kiểm tra an toàn qua Guardrail.
   - Điều phối dữ liệu qua Price/News/Chart Agent.
   - Trả lời streaming từng token theo thời gian thực (SSE).
3. **Hỏi tiếp ngữ cảnh (Turn 2):** Người dùng hỏi tiếp (ví dụ: *"Tại sao lại giảm?"* hoặc *"Vẽ biểu đồ 10 phiên"*).
   - Hệ thống tự động ghi nhớ mã cổ phiếu từ lượt trước để trả lời chính xác.
4. **Kiểm thử tự động & Sửa lỗi (QA Flow):**
   - Developer/Tester chạy kịch bản đánh giá 40 câu hỏi.
   - Hệ thống chỉ ra các câu hỏi bị lỗi (ví dụ: thiếu tin tức FPT, sai phiên giá VNM).
   - Tiến hành sửa logic/prompt và kiểm thử lại cho đến khi vượt qua các tiêu chí nghiệm thu.

---

## Features In Scope
- **Chat Streaming SSE:** Phản hồi câu trả lời trực tiếp từng token kèm hiển thị trace các agent đang thực thi.
- **Hệ thống Multi-Agent:** Phân luồng xử lý chuyên biệt gồm Guardrail, Supervisor, Price Agent, News Agent, Chart Agent, Diagram Agent, Composer.
- **Bộ nhớ ngữ cảnh (Session Memory):** Duy trì ngữ cảnh hội thoại nhiều lượt qua SQLite.
- **Bảo vệ an toàn (Guardrail):** Chặn 100% câu hỏi ngoài phạm vi (cổ phiếu quốc tế, thời tiết, tư vấn mua bán) và cố tình can thiệp hệ thống (prompt injection).
- **Bộ kiểm thử tự động 40 câu hỏi:** Chạy tự động toàn bộ 40 câu hỏi thuộc 7 lát cắt nghiệp vụ (`lookup`, `comparison`, `explain_why`, `charting_diagram`, `session_memory`, `out_of_scope`, `injection`).
- **Sửa lỗi đã định danh:** Khắc phục triệt để các ca kiểm thử chưa đạt (`lookup_04`, `lookup_08`, `lookup_10`).

---

## Features Out of Scope
- Đặt lệnh giao dịch mua/bán thực tế (không tích hợp tài khoản chứng khoán).
- Dữ liệu realtime tick-by-tick (chỉ sử dụng dữ liệu nến ngày 1D và tin tức gần nhất).
- Đăng nhập tài khoản phức tạp, phân quyền người dùng (RBAC), thanh toán.
- Huấn luyện / fine-tune mô hình nền tảng mới (chỉ dùng prompt engineering và tool integration).

---

## Acceptance Criteria
- [x] **Chạy được local:** Ứng dụng chạy mượt mà trên môi trường cục bộ (`localhost:8000`), endpoints `/health` và Session CRUD hoạt động chính xác.
- [x] **Hoàn thành flow chính:** Người dùng gửi câu hỏi và nhận phản hồi streaming SSE (trace agents, tokens) kèm sinh biểu đồ/sơ đồ và lưu trữ SQLite đầy đủ.
- [x] **Bảo vệ an toàn tuyệt đối:** 100% các câu hỏi thuộc nhóm `injection` và `out_of_scope` bị từ chối lịch sự, không trả lời sai lệch (đạt 7/7 ca 100%).
- [x] **Kiểm thử 40 câu hỏi đạt chuẩn:** Toàn bộ 40 câu hỏi trong Golden Dataset v5 được chạy kiểm thử với tỷ lệ Đạt (Pass) $\ge 90\%$ (đạt **40/40 ~ 100.0%** sau Phase 5 Regression).
- [x] **Sửa chữa thành công các ca lỗi:** Các case `lookup_04`, `lookup_08`, `lookup_10` được phân tích nguyên nhân và khắc phục đạt điểm chuẩn (cả 3 ca đều đạt PASS).
- [x] **Unit tests vượt qua 100%:** Toàn bộ 10 file kiểm thử trong thư mục `tests/` chạy pass không có lỗi hồi quy (137/137 tests passed).
- [x] **Sẵn sàng demo ngrok:** Ứng dụng tích hợp công cụ `scripts/start_ngrok_demo.py` sẵn sàng expose public qua ngrok để demo trực tiếp.

