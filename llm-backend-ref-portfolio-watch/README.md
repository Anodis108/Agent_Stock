# Portfolio Watch & Management — Multi-Agent Stock Assistant (MVP 2.0)

Ứng dụng web Multi-Agent Swarm quản lý danh mục đầu tư, phân tích cổ phiếu Việt Nam và đánh giá định lượng hệ thống theo phương pháp **Spec-Driven Development** (SDD).

---

## 1. Mục Tiêu Dự Án (MVP 2.0 Goals)

1. **Đa Người Dùng (Multi-tenant Isolation):** Mỗi người dùng sở hữu danh mục theo dõi (Watchlist) và ngưỡng cảnh báo biến động (`alert_threshold_pct`) riêng biệt, dữ liệu phân tách an toàn trong SQLite.
2. **Quản Lý Danh Mục & Lãi/Lỗ Thực Tế (Portfolio P&L Tracking):** Chuyển dịch từ việc "chỉ tra cứu/cảnh báo" sang "quản lý danh mục đầu tư", theo dõi số lượng cổ phiếu nắm giữ, giá vốn mua vào, tính toán Unrealized P&L, tỷ suất lợi nhuận (%) và tổng tài sản ròng (NAV).
3. **Nâng Cấp EvalAgent Với Chỉ Báo Kỹ Thuật & Đa Nguồn Tin:** Tích hợp chỉ báo kỹ thuật định lượng (RSI 14, SMA 20, SMA 50, Golden Cross / Death Cross) và tin tức đa nguồn (Vnstock News, CafeF, Vietstock) để đánh giá mức độ bất thường và rủi ro chính xác, có cơ sở.
4. **Rewrite & Query Decomposition (Multi-Subquery Processing):** Tích hợp kỹ thuật phân rã câu hỏi vào quy trình Rewrite, hỗ trợ xử lý mượt mà các câu hỏi phức tạp, so sánh đa mã bằng cách chia nhỏ thành danh sách `sub_questions` độc lập và điều phối các worker xử lý đầy đủ, không bỏ sót thông tin.
5. **Agent Evaluation Framework (`agent_eval.py`):** Bộ công cụ đánh giá tự động đo lường chất lượng của Swarm Agent: độ chính xác routing của Supervisor, chất lượng phân rã câu hỏi (Decomposition), tính trung thực chống hallucination của AnswerComposer và tỷ lệ hoàn thành tác vụ.

---

## 2. Cấu Trúc Tài Liệu Spec-Driven Development

Bộ tài liệu kỹ thuật được chuẩn hóa và quản lý tập trung:
- [`README.md`](README.md): Tổng quan dự án, hướng dẫn cài đặt, chạy cục bộ, kiểm thử và demo ngrok.
- [`AGENTS.md`](AGENTS.md): Quy tắc hành xử nghiêm ngặt cho AI Coding Agent khi tham gia phát triển dự án.
- [`specs/product-spec.md`](specs/product-spec.md): Đặc tả sản phẩm, người dùng mục tiêu, phạm vi in/out of scope và tiêu chí nghiệm thu (Acceptance Criteria).
- [`specs/implementation-plan.md`](specs/implementation-plan.md): Kế hoạch triển khai 8 Phase bám sát MVP theo từng task nhỏ.
- [`specs/test-plan.md`](specs/test-plan.md): Kế hoạch kiểm thử 3 lớp (Unit/Integration, Feature Acceptance, Agent Evaluation & Regression Gate).
- [`specs/change-log.md`](specs/change-log.md): Nhật ký ghi nhận chi tiết mọi thay đổi và kết quả kiểm thử.

---

## 3. Kiến Trúc Swarm Multi-Agent

```mermaid
graph TD
    User([Người dùng / Web UI]) --> Guardrail[Pre-Rewrite Guardrail]
    Guardrail -->|Vi phạm| Refusal[Guardrail Refusal Node]
    Guardrail -->|Hợp lệ| Rewrite[Rewrite & Decompose Node]
    Rewrite --> Supervisor[Supervisor Routing Node]
    
    Supervisor --> PriceAgent[Price Agent: Live OHLCV]
    Supervisor --> NewsAgent[News Agent: Multi-source News]
    Supervisor --> IndicatorEngine[Indicator Engine: RSI / SMA]
    Supervisor --> ChartAgent[Chart Agent: Matplotlib Candlestick]
    Supervisor --> DiagramAgent[Diagram Agent: Mermaid Plan]
    
    PriceAgent --> EvalAgent[Eval Agent: Risk & Severity]
    NewsAgent --> EvalAgent
    IndicatorEngine --> EvalAgent
    
    PriceAgent --> Composer[Answer Composer]
    NewsAgent --> Composer
    EvalAgent --> Composer
    ChartAgent --> Composer
    DiagramAgent --> Composer
    
    Composer --> SSE[SSE Streaming Response & P&L Update]
```

---

## 4. Hướng Dẫn Cài Đặt & Chạy Cục Bộ (Local Run)

### Yêu Cầu Tiên Quyết
- Python $\ge$ 3.10
- Môi trường ảo (`venv`)
- Các gói thư viện: `fastapi`, `uvicorn`, `langgraph`, `vnstock`, `pytest`

### Cài Đặt
```bash
# 1. Tạo và kích hoạt virtual environment
python -m venv .venv

# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1

# Trên macOS / Linux:
source .venv/bin/activate

# 2. Cài đặt dependencies
pip install -r requirements.txt
```

### Chạy Backend API Server (Local Run)
```bash
# Chạy với uvicorn tại cổng 8080 (hoặc 8000)
powershell -Command "Set-Item -Path Env:PYTHONPATH -Value 'src'; uvicorn backend.main:app --app-dir src --host 127.0.0.1 --port 8080 --reload"
```
- API Docs: `http://localhost:8080/docs`
- Health check: `http://localhost:8080/health`
- Giao diện Web App: Mở trình duyệt tại `http://localhost:8080` (Backend phục vụ trực tiếp static files frontend).

### Chạy Với Docker Compose
Hệ thống hỗ trợ đóng gói container hóa toàn diện cho cả Backend và Nginx frontend:
```bash
# Khởi chạy toàn bộ hệ thống với Docker Compose
docker compose up --build
```
Ứng dụng sẽ khả dụng tại `http://localhost:8080`.

### Hướng Dẫn Sử Dụng Giao Diện Web UI (MVP 2.0)
1. **Bộ Chuyển Đổi Người Dùng (User Switcher):**
   - Trên thanh tiêu đề góc phải, chọn tài khoản nhanh (`User A`, `User B`, `Default`).
   - Mọi request (chat, watchlist, portfolio) tự động gắn header `X-User-ID: <user_id>` để đảm bảo phân tách dữ liệu tuyệt đối giữa các nhà đầu tư.
2. **Tab Quản Lý Danh Mục Đầu Tư (Portfolio P&L):**
   - Chuyển sang tab **"Danh mục (P&L)"** trên giao diện.
   - Thẻ thống kê thời gian thực: Tổng giá trị tài sản (NAV), Lãi/Lỗ ròng (VND), Tỷ suất lợi nhuận (%).
   - Bảng quản lý cổ phiếu: Theo dõi khối lượng, giá mua bình quân, giá hiện tại, P&L từng mã.
   - Thao tác Thêm mã (`Mã`, `Khối lượng`, `Giá mua`) và Xóa mã trực tiếp trên bảng.
3. **Tra Cứu & Trò Chuyện Thông Minh (Chat Tab):**
   - Hỗ trợ câu hỏi so sánh phức tạp (e.g., *"So sánh FPT và VNM về giá và tin tức"*), hệ thống tự động phân rã thành các `sub_questions` con.
   - I/O Inspector hiển thị trực quan các bước: Pre-Rewrite Guardrail, Sub-queries, Chỉ báo RSI/SMA và Live Graph.

---

## 5. Hướng Dẫn Kiểm Thử (Testing & Quality Gate)

### 5.1. Chạy Bộ Test Suite Hồi Quy Đầy Đủ
```bash
# Chạy toàn bộ test suite (176 tests)
powershell -Command "Set-Item -Path Env:PYTHONPATH -Value 'src'; pytest tests/ -v"
```
*Yêu cầu nghiệm thu:* 100% test cases PASSED (>= 145 tests; hiện tại: 176/176 passed).

### 5.2. Kiểm Tra Hồi Quy Bảo Vệ An Toàn (Safety Guardrails)
```bash
# Kiểm tra chặn tuyệt đối Prompt Injection và Out-of-scope queries
powershell -Command "Set-Item -Path Env:PYTHONPATH -Value 'src'; pytest tests/test_guardrails.py -v"
```
*Tiêu chí:* 100% câu hỏi tấn công Prompt Injection và lạc đề bị từ chối an toàn (Fail-closed) với mã phản hồi từ chối chuẩn mực.

### 5.3. Chạy Đánh Giá Agent Tự Động (`agent_eval.py`)
```bash
# Chạy đánh giá mẫu nhanh (5 câu hỏi)
powershell -Command "Set-Item -Path Env:PYTHONPATH -Value 'src'; python scripts/run_agent_eval.py --sample 5"

# Hoặc chạy toàn bộ bộ benchmark
powershell -Command "Set-Item -Path Env:PYTHONPATH -Value 'src'; python scripts/run_agent_eval.py"
```
Đo lường 4 tiêu chí cốt lõi:
- **Routing Precision/Recall:** Tỷ lệ phân phối đúng worker của Supervisor Agent.
- **Query Decomposition Quality:** Tỷ lệ tách câu hỏi phức tạp thành sub-queries độc lập.
- **Groundedness Score:** Tỷ lệ câu trả lời bám sát dữ liệu thực tế, chống bịa đặt (Hallucination).
- **Task Success Rate:** Tỷ lệ phản hồi thành công và trọn vẹn yêu cầu của người dùng.

Báo cáo chi tiết được tự động xuất ra `specs/eval/agent_eval_report.json` và `specs/eval/agent_eval_report.md`.

---

## 6. Hướng Dẫn Demo Với ngrok

Để trình diễn Web App trực tiếp ra internet cho người dùng từ xa:
```bash
# Bước 1: Kiểm tra trạng thái Backend sẵn sàng
python scripts/start_ngrok_demo.py --port 8080 --check-only

# Bước 2: Khởi động backend local nếu chưa chạy (cổng 8080)
uvicorn backend.main:app --app-dir src --port 8080

# Bước 3: Mở tunnel ngrok public
python scripts/start_ngrok_demo.py --port 8080
```
Script sẽ cung cấp URL Public HTTPS (ví dụ: `https://xxxx.ngrok-free.app`) để người dùng truy cập từ smartphone hoặc máy tính bảng bên ngoài một cách an toàn.
