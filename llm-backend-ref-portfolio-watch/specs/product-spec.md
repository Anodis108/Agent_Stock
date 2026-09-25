# Product Spec

## App Name
**Portfolio Watch — Multi-Agent Stock Assistant (Clean & Realtime Edition)**

---

## App Goal

Cung cấp một ứng dụng web tinh gọn (MVP) trợ giúp theo dõi, phân tích cổ phiếu Việt Nam thông qua hệ thống Đa tác nhân (Multi-Agent Swarm) với phản hồi thời gian thực (Streaming SSE) và bảng giám sát thị trường 10 phiên.

Mục tiêu trọng tâm của chu kỳ cập nhật này:
1. **Clean Code & Đặt tên chuẩn xác**: Loại bỏ cấu trúc lồng nhau thừa thãi (`src/backend/backend/`), đặt tên file, hàm nghiệp vụ và agent node phản ánh đúng chức năng hiện tại (`guardrail_node`, `supervisor_node`, `price_node`, `news_node`, `chart_node`, `composer_node`), không băm nhỏ hàm thái quá, bổ sung docstrings đầy đủ.
2. **Khắc phục vị trí tài nguyên (`resources/`)**: Xóa bỏ thư mục `src/resources/` sinh nhầm trong `src/`; toàn bộ tài nguyên hệ thống (`prompts/`, `data/`, `charts/`, `eval/`, `docs/`) thống nhất nằm tại thư mục gốc `resources/` (ngang cấp với `src/`).
3. **Gói gọn bộ kiểm thử (`tests/`) xuống không quá 10 file**: Tinh giản 33 file test phân mảnh thành tối đa 10 file kiểm thử có cấu trúc logic, dễ bảo trì, bao phủ toàn diện tính năng.
4. **Đánh giá toàn bộ bộ câu hỏi & lưu dẫn chứng**: Chạy kiểm thử tự động toàn bộ 40 câu hỏi của Golden Dataset, đo lường chi tiết và lưu trữ báo cáo làm dẫn chứng chính thức tại `specs/eval/`.

---

## Target Users

1. **Nhà đầu tư cá nhân (End User)**:
   - Cần tra cứu nhanh giá, biến động 10 phiên, tin tức xúc tác và biểu đồ kỹ thuật của cổ phiếu Việt Nam.
   - Trải nghiệm chat thông minh với tốc độ phản hồi tức thì (Streaming text theo từng token).
   - Hỏi tiếp các câu hỏi tự nhiên theo ngữ cảnh mà không cần nhắc lại mã cổ phiếu (ví dụ: *"Tại sao lại giảm?"*).
   - Nắm bắt xu hướng thị trường qua bảng ma trận Market Watch 10D với số liệu chuẩn xác 100%.
   - Gửi đánh giá phản hồi (HITL) trực tiếp để góp phần nâng cao chất lượng câu trả lời.

2. **Kỹ sư AI & Backend Developer**:
   - Cần codebase sạch sẽ, phân tầng rõ ràng, dễ bảo trì và mở rộng thêm tác nhân mới.
   - Quan sát minh bạch tiến trình hoạt động của các agent qua Live Swarm Inspector cập nhật real-time.
   - Quản lý bộ test gọn gàng ($\le 10$ files) phục vụ CI/CD nhanh chóng.
   - Có báo cáo đánh giá Golden Dataset minh bạch làm dẫn chứng so sánh benchmark qua từng phiên bản.

---

## Core User Flow

1. **Truy cập ứng dụng**:
   - Người dùng mở trình duyệt vào `http://localhost:3000` (Frontend Nginx) hoặc `http://localhost:8000` (Backend API).
   - Giao diện gồm 3 khu vực chính: Sidebar quản lý phiên (trái), Khung chat chính (giữa), Live Swarm Inspector (phải).
2. **Hỏi đáp cổ phiếu (Turn 1)**:
   - Người dùng nhập câu hỏi (ví dụ: *"FPT hôm nay tăng hay giảm?"*).
   - Hệ thống đi qua `guardrail_node` xác thực an toàn.
   - Live Inspector kích hoạt node và hiển thị thời gian xử lý (`⏱ 0.35s`).
   - Khung chat stream câu trả lời từng token thời gian thực: thông báo mức biến động giá kèm tin tức liên quan.
3. **Hỏi nối tiếp theo ngữ cảnh (Turn 2)**:
   - Người dùng hỏi câu lửng lơ: *"Tại sao lại giảm?"*.
   - Hệ thống tự động đọc lịch sử phiên, nhận diện đại từ ẩn, kế thừa mã `"FPT"` và giải trình nguyên nhân biến động giá.
4. **Phòng vệ câu hỏi ngoài lề hoặc can thiệp prompt**:
   - Người dùng hỏi ngoài phạm vi (*"Giá cổ phiếu AAPL?"*, *"Thời tiết hôm nay?"*) hoặc gửi câu lệnh can thiệp (*"Ignore previous instructions..."*).
   - `guardrail_node` từ chối lịch sự ngay tại cửa ngõ; không trả lời lan man, không gán nhầm sang FPT.
5. **Yêu cầu biểu đồ kỹ thuật**:
   - Người dùng yêu cầu: *"Vẽ biểu đồ giá FPT 10 phiên"* hoặc *"So sánh biến động VNM và HPG"*.
   - `chart_node` sinh ảnh biểu đồ kỹ thuật lưu vào `resources/data/charts/` và hiển thị ảnh trực quan trong khung chat.
6. **Xem bảng Market Watch 10D**:
   - Người dùng chuyển sang tab **Market Watch (10D)** để theo dõi ma trận giá 10 mã cổ phiếu lớn qua 10 phiên.
   - Dữ liệu giá đảm bảo trùng khớp 100% với số liệu trả lời trong khung chat (Single Source of Truth).
7. **Đánh giá phản hồi (HITL)**:
   - Dưới mỗi câu trả lời, người dùng có thể bấm Thumbs Up 👍 / Thumbs Down 👎 hoặc chấm 1-5 sao.
   - Khi đánh giá tiêu cực, form xuất hiện cho phép chọn lý do cụ thể và ghi nhận xét.
   - Dữ liệu đánh giá kèm toàn bộ telemetry được lưu vào `resources/data/hitl_feedback.json`.

---

## Features In Scope

### 1. Clean Code & Chuẩn Hóa Định Danh
- Loại bỏ thư mục lồng nhau `src/backend/backend/`; file khởi chạy backend duy nhất tại `src/backend/main.py`.
- Chuẩn hóa tên agent nodes và functions phản ánh đúng chức năng:
  - `guardrail_node`: Phòng thủ sớm, phát hiện Injection và Out-of-scope.
  - `rewrite_node`: Chuẩn hóa câu hỏi và phân giải đại từ ngữ cảnh.
  - `supervisor_node`: Định tuyến điều phối các worker agents.
  - `price_node`: Lấy giá và dữ liệu lịch sử từ Vnstock.
  - `news_node`: Quét và trích xuất tin tức tài chính CafeF.
  - `chart_node`: Sinh biểu đồ đường giá SMA/Volume hoặc biểu đồ so sánh %.
  - `diagram_node`: Sinh sơ đồ quy trình Mermaid.
  - `composer_node`: Tổng hợp dữ liệu và stream câu trả lời cuối cùng.
- Không băm nhỏ hàm nghiệp vụ thành các helper vụn vặt; viết hàm trọn vẹn, liền mạch, có docstrings đầy đủ.

### 2. Thống Nhất Vị Trí Tài Nguyên (`resources/`)
- Xóa bỏ triệt để thư mục `src/resources/`.
- Toàn bộ tài nguyên nằm duy nhất tại thư mục gốc `resources/` (ngang cấp với `src/`):
  - `resources/data/charts/`: Lưu trữ các ảnh biểu đồ Matplotlib.
  - `resources/data/portfolio_watch.db`: SQLite database lưu trữ phiên và tin nhắn.
  - `resources/data/hitl_feedback.json`: Tệp lưu trữ telemetry đánh giá người dùng.
  - `resources/prompts/`: Registry lưu prompt của từng agent node.
  - `resources/eval/`: Bộ dữ liệu kiểm thử vàng `golden_v5.yaml` và baseline.
- Sửa toàn bộ mã nguồn xử lý đường dẫn để trỏ chính xác về root `resources/`.

### 3. Gói Gọn Bộ Kiểm Thử (`tests/` <= 10 Files)
- Hợp nhất 33 file kiểm thử hiện tại thành tối đa 10 file có cấu trúc rõ ràng:
  1. `tests/conftest.py`: Fixtures dùng chung, in-memory DB, mock clients.
  2. `tests/test_agents.py`: Kiểm thử các agent nodes và luồng điều phối swarm.
  3. `tests/test_guardrails.py`: Kiểm thử chặn Prompt Injection và từ chối Out-of-Scope.
  4. `tests/test_memory.py`: Kiểm thử ngữ cảnh hỏi nối tiếp Turn 1 ➔ Turn 2 và quản lý sessions.
  5. `tests/test_market.py`: Kiểm thử MarketService, ma trận 10D và đồng bộ dữ liệu giá.
  6. `tests/test_chart.py`: Kiểm thử ChartAgent và lưu trữ biểu đồ vào `resources/data/charts/`.
  7. `tests/test_api.py`: Kiểm thử các endpoint FastAPI (Chat SSE streaming, sessions, market, HITL).
  8. `tests/test_database.py`: Kiểm thử SQLite models, migrations, lưu trữ tin nhắn.
  9. `tests/test_eval.py`: Kiểm thử runner đánh giá Golden Dataset và cơ chế chấm điểm.
  10. `tests/test_system.py`: Kiểm thử Docker container, biến môi trường và tài liệu hướng dẫn.
- Xóa bỏ toàn bộ các file test tạm thời theo phase cũ.

### 4. Đánh Giá Bộ Câu Hỏi & Lưu Trữ Dẫn Chứng
- Chạy kiểm thử tự động toàn bộ 40 câu hỏi trong `resources/eval/golden_v5.yaml` trên 7 slices:
  `lookup` (12), `comparison` (8), `explain_why` (6), `charting_diagram` (4), `session_memory` (3), `out_of_scope` (4), `injection` (3).
- Lưu kết quả đánh giá, pipeline trace, thời gian xử lý, số token và chi phí làm dẫn chứng tại:
  - Báo cáo chi tiết: `specs/eval/eval_results_golden_v5.md`.
  - Tệp cơ sở dữ liệu: `specs/eval/v5_baseline.json`.

### 5. Khả Năng Cốt Lõi Của Ứng Dụng Web
- Phản hồi câu trả lời chạy chữ từng token qua Server-Sent Events (`/api/v1/chat/stream`).
- Live Agent Inspector hiển thị trạng thái và thời gian chạy từng node theo thời gian thực.
- Đồng bộ 100% số liệu giá giữa khung chat và bảng Market Watch 10D (Single Source of Truth).
- Form đánh giá HITL cho phép chọn lý do chi tiết và xuất telemetry JSON.

---

## Features Out of Scope

Để giữ dự án đơn giản, tập trung hoàn thiện MVP chất lượng cao, các tính năng sau **không** thuộc phạm vi triển khai:
1. **Đặt lệnh giao dịch thực tế**: Không tích hợp API mua bán cổ phiếu với các công ty chứng khoán.
2. **Streaming giá Tick-by-Tick**: Không hỗ trợ websocket realtime từng giây (chỉ sử dụng dữ liệu nến ngày 1D).
3. **Hệ thống phân quyền & người dùng phức tạp**: Không triển khai OAuth2, RBAC nhiều cấp hay hệ thống thanh toán.
4. **Visual Graph Builder**: Không xây dựng công cụ kéo thả trực quan để chỉnh sửa luồng agent graph.

---

## Acceptance Criteria

1. **Vị trí tài nguyên chuẩn xác**:
   - Thư mục `src/resources/` bị xóa hoàn toàn; không có file tài nguyên nào sinh ra trong `src/`.
   - Toàn bộ ảnh chart, cơ sở dữ liệu, file HITL feedback và prompts nằm đúng trong root `resources/`.
2. **Bộ kiểm thử tinh gọn**:
   - Thư mục `tests/` chứa đúng $\le 10$ file kiểm thử `.py`.
   - Toàn bộ test suite chạy vượt qua 100% (`pytest tests/`).
3. **Mã nguồn sạch & Định danh chuẩn**:
   - Không còn thư mục `src/backend/backend/`; backend app được khởi tạo duy nhất tại `src/backend/main.py`.
   - Các agent nodes, functions và files được đặt tên chính xác theo chức năng.
   - Toàn bộ các module, class và function chính có docstrings rõ ràng.
4. **Dẫn chứng đánh giá bộ câu hỏi đầy đủ**:
   - Đánh giá toàn bộ 40 câu hỏi của Golden Dataset thành công.
   - Tỷ lệ vượt qua tổng thể (Overall Pass Rate) $\ge 85\%$.
   - Nhóm `injection` đạt **100% Pass** (Zero-Tolerance Security Gate).
   - Nhóm `out_of_scope` đạt **100% Pass** (từ chối lịch sự, không bịa đặt hoặc trả về giá FPT).
   - Báo cáo dẫn chứng được lưu đầy đủ tại `specs/eval/eval_results_golden_v5.md` và `specs/eval/v5_baseline.json`.
5. **Vận hành & Triển khai**:
   - Ứng dụng chạy được trên môi trường cục bộ (Local Python + Uvicorn) và Docker Compose (`docker compose up --build`).
   - Giao diện người dùng và API hoạt động ổn định, tin cậy.
