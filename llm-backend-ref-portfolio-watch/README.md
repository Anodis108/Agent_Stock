# Portfolio Watch — Multi-Agent Stock Swarm (Clean & Realtime Edition)

Hệ thống theo dõi cổ phiếu Việt Nam & Trợ lý Chat Đa Tác Nhân (Multi-Agent Swarm) xây dựng theo phương pháp **Spec-Driven Development** và định hướng **MVP-focused**:
- **Kiến Trúc Clean Code & Định Danh Chuẩn Xác**: Tinh gọn mã nguồn, loại bỏ thư mục lồng nhau thừa thãi, đặt tên file/hàm/agent node theo đúng chức năng thực tế.
- **Tài Nguyên Tập Trung Ngang Cấp Src (`resources/`)**: Toàn bộ dữ liệu, prompt, ảnh chart, và telemetry được lưu trữ tại thư mục gốc `resources/` (tuyệt đối không nằm trong `src/`).
- **Bộ Kiểm Thử Cô Đọng (<= 10 Files)**: Hợp nhất toàn bộ 33 file kiểm thử phân mảnh thành đúng 10 file kiểm thử logic, dễ duy trì và bao phủ trọn vẹn mọi tính năng.
- **Đánh Giá Bộ Câu Hỏi & Lưu Dẫn Chứng**: Chạy kiểm thử tự động toàn diện trên bộ 40 câu hỏi Golden Dataset, đánh giá đa tầng và lưu trữ hồ sơ dẫn chứng minh bạch.
- **Phản Hồi Streaming Thời Gian Thực (SSE)**: Khung chat hiển thị câu trả lời chạy chữ từng token kèm Live Swarm Inspector cập nhật trạng thái và thời gian thực thi (Latency Badge `⏱ 0.35s`).
- **Phòng Thủ Sớm Pre-Rewrite Guardrail**: Tự động phát hiện và chặn đứng 100% Prompt Injection / Jailbreak và từ chối an toàn các câu hỏi ngoài phạm vi (chứng khoán Mỹ AAPL, thời tiết).
- **Kế Thừa Ngữ Cảnh Hội Thoại (Short-Term Memory)**: Tự động phân giải các câu hỏi nối tiếp Turn 1 ➔ Turn 2 (ví dụ: *"FPT tăng hay giảm?"* ➔ *"Tại sao lại giảm?"*).
- **Vẽ Biểu Đồ Kỹ Thuật Chuẩn Xác (`ChartAgent`)**: Tự động vẽ biểu đồ đường giá đóng cửa kèm SMA5, SMA10 và Volume cho 1 mã, hoặc biểu đồ so sánh % tăng trưởng cho $\ge 2$ mã.
- **Đồng Bộ Tuyệt Đối Dữ Liệu Giá (Single Source of Truth)**: Cam kết số liệu giá giữa phản hồi Chat và bảng Market Watch 10D luôn đồng nhất.
- **Vòng Lặp Phản Hồi Con Người (HITL Telemetry JSON)**: Xuất toàn bộ dữ liệu phản hồi kèm telemetry vào `resources/data/hitl_feedback.json`.

---

## Cấu Trúc Dự Án Chuẩn Hóa

```text
llm-backend-ref-portfolio-watch/
├── README.md                     # Tài liệu hướng dẫn cài đặt, chạy local, docker, ngrok và kiểm thử
├── AGENTS.md                     # Quy định cách làm việc cho AI Agent (Spec-Driven Development)
├── docker-compose.yml            # Khởi chạy microservices 2 containers (Frontend 3000, Backend 8000)
├── pyproject.toml                # Cấu hình dependencies & pytest
├── resources/                    # TÀI NGUYÊN TẬP TRUNG TẠI ROOT (NGANG CẤP VỚI SRC, KHÔNG NẰM TRONG SRC)
│   ├── configs/                  # File cấu hình hệ thống
│   ├── data/                     # SQLite DB (portfolio_watch.db), charts/, hitl_feedback.json
│   ├── docs/                     # Tài liệu kiến trúc & sơ đồ Mermaid
│   ├── eval/                     # Bộ dữ liệu vàng (golden_v5.yaml) & baseline
│   └── prompts/                  # Prompt registry có versioning
├── specs/                        # HỒ SƠ SPEC-DRIVEN DEVELOPMENT
│   ├── product-spec.md           # Đặc tả sản phẩm chi tiết
│   ├── implementation-plan.md    # Kế hoạch triển khai theo từng Phase
│   ├── test-plan.md              # Kế hoạch kiểm thử & gói test <= 10 files
│   ├── change-log.md             # Nhật ký thay đổi
│   └── eval/                     # Hồ sơ dẫn chứng đánh giá bộ câu hỏi
├── src/                          # MÃ NGUỒN HỆ THỐNG
│   ├── backend/                  # FastAPI & AI Multi-Agent Swarm (cổng 8000)
│   │   ├── agents/               # Supervisor, Price, News, Chart, Diagram, Composer
│   │   ├── api/                  # FastAPI Routers (chat SSE, sessions, market, hitl)
│   │   ├── database/             # SQLite connection & repositories
│   │   ├── domain/               # Core entities, Ports, Input Guardrails
│   │   ├── eval/                 # Evaluation pipeline, Scorers, Golden runner
│   │   ├── graph/                # LangGraph state & workflow
│   │   ├── infra/                # Vnstock, CafeF, LLM client, Memory, Tracing
│   │   ├── services/             # MarketService, HITLService
│   │   ├── main.py               # Entrypoint FastAPI app duy nhất
│   │   └── Dockerfile            # Container backend độc lập (Python 3.12, Uvicorn)
│   └── frontend/                 # Giao diện Web SPA (Nginx Alpine, cổng 3000)
│       ├── index.html            # Giao diện SPA Claude-style
│       ├── style.css             # Vanilla CSS, Dark/Light theme, latency badge
│       ├── app.js                # Quản lý SSE streaming, live inspector, HITL modal
│       ├── nginx.conf            # Cấu hình Nginx reverse proxy
│       └── Dockerfile            # Container frontend độc lập (Alpine Nginx)
└── tests/                        # BỘ KIỂM THỬ GỌN GÀNG (TỐI ĐA 10 FILES)
    ├── conftest.py               # Fixtures dùng chung & mock test clients
    ├── test_agents.py            # Kiểm thử các agent nodes & workflow routing
    ├── test_guardrails.py        # Kiểm thử Pre-Rewrite Guardrail, chặn Out-of-Scope & Injection
    ├── test_memory.py            # Kiểm thử bộ nhớ ngữ cảnh short-term & sessions
    ├── test_market.py            # Kiểm thử MarketService, ma trận 10D & đồng bộ giá
    ├── test_chart.py             # Kiểm thử ChartAgent & lưu ảnh vào resources/data/charts/
    ├── test_api.py               # Kiểm thử FastAPI endpoints (Chat SSE, Market, HITL)
    ├── test_database.py          # Kiểm thử tầng dữ liệu SQLite & persistence
    ├── test_eval.py              # Kiểm thử bộ runner đánh giá Golden Dataset
    └── test_system.py            # Kiểm thử cấu hình Docker, môi trường & tài liệu
```

---

## Khởi Chạy Nhanh Bằng Docker Compose (Khuyến Nghị)

Hệ thống triển khai 2 container độc lập (Frontend UI Nginx & Backend FastAPI Swarm) chỉ bằng **1 lệnh duy nhất**:

### 1. Chuẩn Bị Cấu Hình Môi Trường
```bash
cp .env.example .env
# Mở file .env và điền OPENAI_API_KEYS=sk-... (hoặc để trống nếu dùng Heuristic fallback)
```

### 2. Khởi Chạy Hệ Thống
```bash
docker compose up --build -d
```
Xem log thời gian thực:
```bash
docker compose logs -f
```

### 3. Địa Chỉ Truy Cập Dịch Vụ
- **Giao diện Web UI (Frontend)**: **`http://localhost:3000`** (Nginx reverse proxy về backend)
- **API Backend (FastAPI)**: **`http://localhost:8000`** (Swagger docs tại `/docs`, healthcheck tại `/health`)

### 4. Dừng Hệ Thống
```bash
docker compose down
```

---

## Hướng Dẫn Phát Triển Cục Bộ (Local Development)

Nếu bạn muốn chạy trực tiếp trên máy không thông qua Docker:

### 1. Yêu Cầu Tiên Quyết (Prerequisites)
- **Python**: Phiên bản `>= 3.10` (Khuyến nghị Python 3.11 hoặc 3.12).
- **Git**: Quản lý mã nguồn.
- **Trình duyệt Web hiện đại**: Chrome, Firefox, Safari, Edge (hỗ trợ SSE - Server-Sent Events).

### 2. Cài Đặt Môi Trường
```bash
# 1. Khởi tạo và kích hoạt virtual environment
python -m venv .venv
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Trên macOS / Linux:
source .venv/bin/activate

# 2. Nâng cấp pip và cài đặt gói dependencies
python -m pip install -U pip setuptools wheel
pip install -e ".[dev]"
```

### 3. Cấu Hình Biến Môi Trường
```bash
cp .env.example .env
```
Các tham số quan trọng trong `.env`:
| Biến môi trường | Giá trị mặc định | Giải thích ý nghĩa |
| :--- | :--- | :--- |
| `LLM_BACKEND` | `openai` | Backend LLM: `openai`, `ollama`, hoặc `vllm`. |
| `OPENAI_API_KEYS` | `sk-...` | Khóa API OpenAI (hệ thống fallback an toàn nếu không có key). |
| `LLM_MODEL` | `gpt-4o-mini` | Model LLM định tuyến và xử lý ngôn ngữ. |
| `API_HOST` | `127.0.0.1` | Địa chỉ máy chủ backend cục bộ (`0.0.0.0` trong Docker). |
| `API_PORT` | `8000` | Cổng HTTP của máy chủ backend cục bộ. |
| `SQLITE_PATH` | `./resources/data/portfolio_watch.db` | Đường dẫn SQLite DB lưu trữ tin nhắn và phiên. |

### 4. Khởi Chạy Máy Chủ Backend Cục Bộ
```bash
# Cách 1: Sử dụng tham số --app-dir (Khuyến nghị, đơn giản trên mọi nền tảng)
uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000

# Cách 2: Thiết lập PYTHONPATH trực tiếp
# Trên Windows PowerShell:
$env:PYTHONPATH="src;."
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Trên macOS / Linux:
export PYTHONPATH="src:."
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
> **Phục vụ giao diện Web SPA trọn gói**: Khi backend khởi chạy, FastAPI tự động mount và phục vụ toàn bộ Web UI SPA trực tiếp tại: **`http://localhost:8000/`**. Swagger API Interactive Docs có sẵn tại: **`http://localhost:8000/docs`**.

### 5. Xác Minh Các Trạng Thái Phản Hồi & Validation (Error States)
Hệ thống được thiết kế xử lý lỗi phòng thủ chặt chẽ:
- **HTTP 422 Unprocessable Entity**: Trả về khi payload request thiếu trường bắt buộc hoặc sai định dạng schema (ví dụ: `POST /chat` với payload rỗng `{}` hoặc sai kiểu dữ liệu).
- **HTTP 400 Bad Request**: Trả về khi người dùng gửi câu hỏi rỗng (chỉ chứa khoảng trắng) hoặc mã cổ phiếu không hợp lệ (không phải định dạng 2–10 ký tự).
- **HTTP 404 Not Found**: Trả về khi truy vấn thông tin phiên không tồn tại (`GET /api/v1/sessions/{invalid_id}`) với thông báo thân thiện `"Session không tồn tại"`.
- **Tự động khởi tạo phiên (Auto Session Creation)**: Khi gửi câu hỏi với một `session_id` mới chưa từng tồn tại qua `POST /chat` hoặc `POST /api/v1/chat/stream`, hệ thống tự động tạo mới phiên hội thoại và lưu trữ lịch sử tin nhắn mà không làm gián đoạn người dùng.
- **Chế độ Heuristic Fallback (Khi không có OpenAI API Key)**: Nếu không có khóa `OPENAI_API_KEYS` trong `.env`, hệ thống tự động kích hoạt bộ não quy tắc Heuristic (`HeuristicRewriteBrain`, `HeuristicSupervisorBrain`, `HeuristicAnswerDraftBrain`), trả về dữ liệu an toàn từ Vnstock/CafeF mà không gây sập ứng dụng.

### 6. Xử Lý Sự Cố Thường Gặp (Troubleshooting)
| Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **`Address already in use` (Cổng 8000 bị chiếm)** | Cổng 8000 đang được sử dụng bởi IDE hoặc ứng dụng khác | Chạy Uvicorn trên cổng khác: `uvicorn backend.main:app --app-dir src --port 8088` hoặc đặt `API_PORT=8088` trong `.env`. |
| **`ModuleNotFoundError: No module named 'backend'`** | Chưa cấu hình thư mục gốc mã nguồn vào Python path | Thêm tham số `--app-dir src` vào lệnh Uvicorn hoặc gán `$env:PYTHONPATH="src;."` (PowerShell) / `export PYTHONPATH="src:."` (Linux/macOS). |
| **Giao diện Web không tải được (`404 Not Found`)** | Không tìm thấy thư mục `src/frontend` | Đảm bảo thư mục `src/frontend/index.html` tồn tại ngang hàng với `src/backend`. |
| **Cảnh báo `findfont: Failed to find font weight 600 for Arial`** | Hệ điều hành thiếu font Arial cụ thể | Đây chỉ là thông báo của Matplotlib khi render biểu đồ; hệ thống tự động chuyển sang font hệ thống chuẩn (700 bold) mà không ảnh hưởng kết quả. |


---

## Hướng Dẫn Demo Bằng ngrok

Để chia sẻ demo giao diện hoặc API ra ngoài internet một cách an toàn mà không cần triển khai cloud phức tạp:

### 1. Cài Đặt và Cấu Hình ngrok
Tải ngrok tại [https://ngrok.com/](https://ngrok.com/) và cấu hình authtoken:
```bash
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

### 2. Kịch Bản Demo: Chạy Docker Compose + Expose Frontend
Khi đang chạy hệ thống bằng Docker Compose (Frontend cổng 3000, Backend cổng 8000):
```bash
ngrok http 3000
```
- Ngrok sẽ cung cấp một đường link public HTTPS (ví dụ: `https://abcd-1234.ngrok-free.app`).
- Mở liên kết này trên trình duyệt di động hoặc gửi cho người xem demo. Mọi request API đều được Nginx reverse proxy tự động chuyển về Backend.

### 3. Kịch Bản Demo: Chạy Local Backend Độc Lập
Khi chạy Uvicorn local tại cổng 8000:
```bash
ngrok http 8000
```
- Truy cập địa chỉ public HTTPS do ngrok cấp để demo toàn bộ Web UI và Swagger API `/docs`.

---

## Kiểm Thử & Lưu Trữ Dẫn Chứng Đánh Giá

### 1. Chạy Bộ Kiểm Thử Tự Động (Gói Gọn Trong 10 Files)
```bash
# Chạy cục bộ:
pytest tests/ -v

# Chạy bên trong container:
docker compose run --rm app pytest tests/ -v
```

### 2. Chạy Đánh Giá Toàn Bộ 40 Câu Hỏi Golden Dataset & Lưu Dẫn Chứng
```bash
# Chạy cục bộ:
python -m backend.eval.run_detailed

# Chạy bên trong container:
docker compose run --rm app python -m backend.eval.run_detailed
```
- Bộ runner tự động đánh giá toàn bộ 40 câu hỏi, đo lường chi tiết Latency, Token, Chi phí, và điểm số Correctness / Completeness / Grounding.
- Kết quả được tự động ghi nhận vào các file hồ sơ dẫn chứng:
  - Báo cáo Markdown chi tiết: [specs/eval/eval_results_golden_v5.md](specs/eval/eval_results_golden_v5.md)
  - Tệp cơ sở dữ liệu JSON: [specs/eval/v5_baseline.json](specs/eval/v5_baseline.json)

### 3. Chạy Kiểm Tra Riêng Nhóm Bảo Mật Zero-Tolerance
```bash
python -m backend.eval.run --slice injection
```

---

## Quy Trình Phát Triển Dựa Trên Đặc Tả (Spec-Driven Development)

Mọi thay đổi trong hệ thống đều tuân thủ nghiêm ngặt quy trình:
1. **Đặc tả sản phẩm**: Xem [specs/product-spec.md](specs/product-spec.md)
2. **Kế hoạch triển khai theo Phase**: Xem [specs/implementation-plan.md](specs/implementation-plan.md)
3. **Kế hoạch kiểm thử & gói test <= 10 files**: Xem [specs/test-plan.md](specs/test-plan.md)
4. **Nhật ký thay đổi**: Xem [specs/change-log.md](specs/change-log.md)
5. **Quy tắc làm việc cho AI Agent**: Xem [AGENTS.md](AGENTS.md)
