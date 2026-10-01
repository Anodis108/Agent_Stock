# VN Stock Swarm — Multi-Agent Stock Assistant & Portfolio Watch

Hệ thống trợ lý phân tích chứng khoán Việt Nam và quản lý danh mục đa người dùng (Multi-tenant Portfolio Watch) ứng dụng kiến trúc **Multi-Agent Swarm (LangGraph)**, phát triển theo phương pháp **Spec-Driven Development** (SDD).

---

## 1. App Idea & Mục Tiêu Dự Án

Dự án hướng tới việc xây dựng một hệ sinh thái AI toàn diện hỗ trợ nhà đầu tư cá nhân trên thị trường chứng khoán Việt Nam:
1. **Kiến Trúc Multi-Agent Swarm Chuyên Biệt**: Phối hợp các Agent chuyên trách (Guardrail, Rewrite & Query Decomposition, Supervisor, Price, News, Indicator, Chart, Eval, AnswerComposer) để giải quyết từ câu hỏi đơn giản đến bài toán phân tích so sánh đa chiều.
2. **Quản Lý Danh Mục & P&L Đa Người Dùng (Multi-tenant Portfolio)**: Theo dõi số lượng nắm giữ, giá vốn mua vào, tính toán Unrealized P&L (VND và %), tổng giá trị tài sản ròng (NAV) và danh mục theo dõi (Watchlist) riêng biệt cho từng người dùng qua `user_id`.
3. **Đánh Giá Rủi Ro Định Lượng & Tin Tức (EvalAgent)**: Kết hợp chỉ báo kỹ thuật định lượng (RSI 14, SMA 20, SMA 50, Golden/Death Cross) và tin tức tài chính đa nguồn (Vnstock, CafeF, Vietstock) để phân tích biến động khách quan, trung thực.
4. **Chuẩn Hóa Cấu Trúc Monorepo (Root Flat Structure)**: Tinh gọn cấu trúc thư mục, đưa toàn bộ mã nguồn ra thư mục gốc để quản trị tập trung, tối ưu quy trình Docker và CI/CD GitHub Actions.
5. **Đánh Giá Toàn Diện (Comprehensive Golden Dataset & Observation)**: Xây dựng bộ testcase mẫu tối giản nhưng bao quát toàn bộ chức năng, ghi nhận đầy đủ trace, token usage, latency và cost tracking.

---

## 2. Tổng Hợp Toàn Bộ Chức Năng Của Hệ Thống (Feature Inventory)

| Phân hệ / Chức năng | Mô tả chi tiết | Agent / Module đảm nhiệm |
| :--- | :--- | :--- |
| **1. Tra cứu giá & dữ liệu thị trường** | Lấy giá khớp lệnh, mức tăng/giảm, biến động ngày, lịch sử giá 10 phiên, hỗ trợ fallback dữ liệu mẫu khi sàn đóng cửa/lỗi mạng. | `PriceAgent`, `VnstockPriceSource` |
| **2. Bảng theo dõi 10D Market Matrix** | Endpoint `/api/v1/market/matrix-10d` cung cấp ma trận giá 10 ngày kèm sparkline của top cổ phiếu VN30. | `MarketService`, `MarketRouter` |
| **3. Tổng hợp tin tức tài chính** | Cào và tổng hợp tin tức nóng, tin doanh nghiệp từ Vnstock News và CafeF, trích dẫn nguồn minh bạch. | `NewsAgent`, `CafefNewsSource` |
| **4. Động cơ chỉ báo kỹ thuật** | Tính toán tự động RSI(14), SMA(20), SMA(50), xác định tín hiệu giao cắt xu hướng Golden Cross / Death Cross. | `TechnicalIndicatorService`, `domain.indicators` |
| **5. Đánh giá bất thường & rủi ro** | Phân loại mức độ nghiêm trọng (`none`, `low`, `medium`, `high`) dựa trên chỉ số kỹ thuật và độ nóng của tin tức. | `EvalAgent` |
| **6. Phân rã câu hỏi đa ý (Decomposition)** | Tự động nhận diện câu hỏi so sánh hoặc đa mã (VD: *"So sánh giá và tin tức của FPT với HPG"*), tách thành các sub-queries độc lập để gom đủ dữ liệu. | `RewriteBrain`, `supervisor_agent.nodes` |
| **7. Quản lý danh mục & Lãi/Lỗ (P&L)** | Lưu trữ số lượng, giá vốn, ngày mua; tự động tính Unrealized P&L, tỷ suất lợi nhuận và tổng NAV theo từng `user_id`. | `PortfolioService`, `PortfolioHoldingRepository` |
| **8. Danh mục theo dõi & Cảnh báo (Watchlist)** | Thêm/bớt mã theo dõi, cài đặt ngưỡng cảnh báo biến động (`alert_threshold_pct`) riêng cho từng người dùng. | `WatchlistStore`, `UserSettingsRepository` |
| **9. Vẽ biểu đồ nến & chỉ báo (Chart)** | Sinh biểu đồ nến kỹ thuật kết hợp SMA bằng Matplotlib, phục vụ trực tiếp qua URL ảnh tĩnh trong phản hồi SSE. | `ChartAgent` |
| **10. Tường lửa an toàn (Guardrails)** | Chặn 100% Prompt Injection, từ chối câu hỏi ngoài phạm vi chứng khoán, kèm miễn trừ trách nhiệm đầu tư trung lập. | `PreRewriteGuardrail`, `AnswerComposer` |
| **11. Web App Trực Quan & Live Graph** | Giao diện Chat Markdown streaming (SSE), hiển thị đồ thị mạng lưới Agent theo thời gian thực (hover xem system prompt), bảng P&L và bộ chuyển người dùng (User Switcher). | `src/frontend/`, `src/backend/main.py` |
| **12. Vận hành & Tin cậy (DevOps / CI/CD)** | A/B Testing prompt (`production` vs `v2`), fallback đa backend LLM (OpenAI, Ollama, vLLM), Docker Compose, GitHub Actions CI/CD. | `infra.llm`, `.github/workflows/` |

---

## 3. Kiến Trúc Multi-Agent Swarm

```mermaid
graph TD
    User([Người dùng / Web UI]) --> Guardrail[1. Pre-Rewrite Guardrail]
    Guardrail -->|Vi phạm / Ngoài phạm vi| Refusal[Guardrail Refusal Node]
    Guardrail -->|Hợp lệ| Rewrite[2. Rewrite & Query Decomposition]
    
    Rewrite --> Supervisor[3. Supervisor Orchestration Node]
    
    Supervisor -->|Sub-query giá| PriceAgent[Price Agent: OHLCV & Market Data]
    Supervisor -->|Sub-query tin tức| NewsAgent[News Agent: Vnstock & CafeF News]
    Supervisor -->|Sub-query kỹ thuật| IndicatorEngine[Indicator Engine: RSI 14 / SMA 20-50]
    Supervisor -->|Yêu cầu vẽ đồ thị| ChartAgent[Chart Agent: Matplotlib Candlestick]
    
    PriceAgent --> EvalAgent[4. Eval Agent: Risk & Anomaly Assessment]
    NewsAgent --> EvalAgent
    IndicatorEngine --> EvalAgent
    
    PriceAgent --> Composer[5. Answer Composer Node]
    NewsAgent --> Composer
    EvalAgent --> Composer
    ChartAgent --> Composer
    
    Composer --> SSE[6. SSE Streaming Response: Markdown + Chart + P&L]
    Refusal --> SSE
```

---

## 4. Tài Liệu Spec-Driven Development (SDD)

Bộ tài liệu đặc tả được duy trì tại thư mục `specs/`:
* [specs/product-spec.md](specs/product-spec.md): Đặc tả sản phẩm, yêu cầu chức năng, phi chức năng và Tiêu chí nghiệm thu (Acceptance Criteria).
* [specs/implementation-plan.md](specs/implementation-plan.md): Kế hoạch triển khai theo từng Phase rõ ràng, bám sát MVP.
* [specs/test-plan.md](specs/test-plan.md): Kế hoạch kiểm thử 5 lớp (Unit test, AC verification, Golden dataset eval, Observation, Demo script).
* [specs/change-log.md](specs/change-log.md): Nhật ký chi tiết tiến trình cập nhật và kết quả nghiệm thu.
* [AGENTS.md](AGENTS.md): Bản quy tắc ứng xử bắt buộc dành cho các AI Coding Assistant.

---

## 5. Hướng Dẫn Cài Đặt & Chạy Cục Bộ

### Yêu Cầu Môi Trường
* Python >= 3.10 (khuyến nghị Python 3.11 hoặc 3.12)
* SQLite 3
* Git

### Cài Đặt
```bash
# 1. Kích hoạt môi trường ảo
# Windows:
& "$HOME\.venv\Scripts\Activate.ps1"
# Linux / macOS:
source ~/.venv/bin/activate

# 2. Cài đặt dependencies (bao gồm wheel nội bộ)
pip install wheels/*.whl
pip install -e ".[dev]"
```

### Chạy Cục Bộ (Local)
```bash
# Thiết lập biến môi trường và chạy Backend API (kèm Frontend Static)
$env:PYTHONPATH="src"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* **Giao diện Web UI:** `http://localhost:8000`
* **API Documentation (Swagger):** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/health`

### Chạy Qua Docker Compose
```bash
# Khởi chạy toàn bộ dịch vụ (Backend FastAPI + Frontend Nginx)
docker compose up --build -d
```
* **Frontend UI (Nginx):** `http://localhost:3000`
* **Backend API:** `http://localhost:8000`

---

## 6. Chạy Kiểm Thử & Đánh Giá Chất Lượng

```bash
# Chạy toàn bộ 178+ unit & integration tests
pytest tests/ -v

# Chạy đánh giá tập Golden Dataset mới (Offline / Mock judge)
python -m backend.eval.run --subset --skip-agent-eval --json specs/eval/pr_report.json --report specs/eval/pr_report.md
```
