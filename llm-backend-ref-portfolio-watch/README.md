# Portfolio Watch & Chat — Quality Loop + Split Deploy

Multi-agent theo dõi danh mục chứng khoán Việt Nam (giám sát biến động +
hỏi–đáp). MVP AI đã có trong repo; vòng Spec-Driven hiện tại tập trung:

1. Debug / đánh giá **từng case** golden dataset tới khi pass.
2. Tận dụng ý tưởng eval (`task_success` + `trajectory`) từ
   [`llm-engineer-demo`](../llm-engineer-demo).
3. Tách **Frontend**, **Backend**, **AI** deploy riêng.
4. UI hiện **từng bước** agent; trace trên **Langfuse**.

## Tài liệu (đọc trước khi code)

| File | Nội dung |
|---|---|
| [specs/product-spec.md](specs/product-spec.md) | Mục tiêu vòng này, scope, acceptance |
| [specs/implementation-plan.md](specs/implementation-plan.md) | Phase 1–8 + backlog multi-agent (3c) |
| [specs/test-plan.md](specs/test-plan.md) | Cách chấm golden + test tách process |
| [specs/change-log.md](specs/change-log.md) | Nhật ký thay đổi |
| [AGENTS.md](AGENTS.md) | Quy tắc coding agent |
| [specs/agents.md](specs/agents.md) | Mô tả từng domain agent |
| [specs/mvp-status-report.md](specs/mvp-status-report.md) | Báo cáo MVP Phase 1–10 (đã xong) |

## Trạng thái

- **Đã có:** multi-agent AI (`src/portfolio_watch/`), AI `:8001`, Backend
  proxy (`backend/` `:8000`), Frontend static (`frontend/` `:5173`), golden
  30 case + regression Phase 5, Prompt Registry; Phase 6–7 local/demo/
  Docker; **Phase 8 Langfuse** (trace + `request_id` + README + `.env.example`).
- **Backlog:** chỉ thêm task Phase 3c khi golden fail chưa sửa được
  (`specs/eval/blocked_cases.yaml`).

## Local development

Hướng dẫn chạy app trên máy local (Spec-Driven Bước 9). **Không** cần đổi
logic app — chỉ env + 3 process.

### Prerequisites

- Python **≥ 3.10**
- Env: conda `dong312` **hoặc** venv (`$HOME/.venv` / project `.venv`)
- File `.env` (copy từ `.env.example`)
- LLM: OpenAI key **hoặc** Ollama/vLLM local

Chi tiết cài env: mục **Prerequisites (Phase 6)** bên dưới.

### Install

```bash
cd llm-backend-ref-portfolio-watch
pip install -U pip
pip install -e ".[dev]"
# Tuỳ chọn tracing: pip install langfuse
```

Kiểm tra import:

```bash
python -c "from src.portfolio_watch.shared.settings import settings; print(settings.app_name)"
```

### Environment variables

```bash
cp .env.example .env
# PowerShell: Copy-Item .env.example .env
```

| Bắt buộc (OpenAI) | Tuỳ chọn quan trọng |
|---|---|
| `OPENAI_API_KEYS` | `AI_BASE_URL`, `FRONTEND_ORIGIN`, `LLM_BACKEND` / `LLM_BASE_URL` |
| `LLM_BACKEND=openai` | `MONITORING_ENABLED` + `LANGFUSE_*` (Phase 8) |

Bảng đầy đủ: **Biến môi trường (Phase 6)**. Mẫu: [`.env.example`](.env.example).

### Run — Backend (product API)

```bash
# Terminal 2 — sau khi AI đã chạy
python scripts/serve_backend.py
# → http://127.0.0.1:8000/health
```

Backend proxy chat/scan tới AI; CRUD watchlist/approvals. Không import
`domain.agents`.

### Run — AI service

```bash
# Terminal 1 — bật trước
python scripts/serve_ai.py
# → http://127.0.0.1:8001/health
```

### Run — Frontend

```bash
# Terminal 3
python scripts/serve_frontend.py
# → http://127.0.0.1:5173/
```

UI static gọi Backend (`frontend/config.js`). Trình duyệt **không** gọi AI
thẳng.

### Local URLs

| URL | Process |
|---|---|
| http://127.0.0.1:5173/ | Frontend (mở UI tại đây) |
| http://127.0.0.1:8000/health | Backend |
| http://127.0.0.1:8000/chat | Backend chat (UI / curl) |
| http://127.0.0.1:8001/health | AI |

Thứ tự bật: **AI → Backend → Frontend**. Luồng request:
**Frontend → Backend → AI**.

### Troubleshooting (tóm tắt)

| Vấn đề | Xử lý nhanh |
|---|---|
| Auth / invalid API key | Điền `OPENAI_API_KEYS` trong `.env`; restart AI |
| Backend 502 AI unreachable | Bật AI trước; kiểm `AI_BASE_URL` / `:8001/health` |
| Backend 502 AI timeout | Tăng `AI_HTTP_TIMEOUT` |
| Port trùng | Đổi `AI_API_PORT` / `API_PORT` / `--port` (8001 / 8000 / 5173) |
| CORS FE→BE | `FRONTEND_ORIGIN=*` hoặc `http://127.0.0.1:5173` |
| Windows SSL cert | `unset SSL_CERT_FILE` (Git Bash) trước khi chạy AI/eval |

Chi tiết: mục **Troubleshooting (Phase 6)** và **Langfuse (Phase 8)**.

## Prerequisites (Phase 6)

Cần sẵn trước khi chạy AI / Backend / Frontend hoặc eval.

### 1. Python môi trường

- **Python ≥ 3.10**
- Một trong hai cách (chọn một):

**Cách A — conda (khuyến nghị lớp / máy đã có env):**

```bash
conda activate dong312
cd llm-backend-ref-portfolio-watch
pip install -e ".[dev]"
```

**Cách B — venv dùng chung (`$HOME/.venv`) hoặc venv project:**

```bash
# Windows (Git Bash): tạo nếu chưa có
python -m venv "$HOME/.venv"
source "$HOME/.venv/Scripts/activate"

# macOS / Linux
# python3 -m venv ~/.venv && source ~/.venv/bin/activate

cd llm-backend-ref-portfolio-watch
pip install -U pip
pip install -e ".[dev]"
```

Kiểm tra nhanh:

```bash
python -c "from src.portfolio_watch.shared.settings import settings; print(settings.app_name)"
```

### 2. File `.env`

1. Copy mẫu: `cp .env.example .env` (Windows PowerShell: `Copy-Item .env.example .env`).
2. Điền ít nhất khi dùng OpenAI: `OPENAI_API_KEYS=...` (có thể nhiều key,
   ngăn cách dấu phẩy). Xem comment trong `.env.example`.
3. Không commit `.env` (đã có trong `.gitignore`).

Chi tiết biến: mục **Biến môi trường**. Lệnh eval: mục **Eval**.
Lỗi thường gặp: mục **Troubleshooting**.

## Chạy 3 process (Phase 6)

Luồng: **Frontend → Backend → AI** (trình duyệt không gọi thẳng AI).
Thứ tự bật: AI → Backend → Frontend. Env đã kích hoạt + `.env` như mục
Prerequisites.

| Process | Lệnh | Port mặc định | Health / URL |
|---|---|---|---|
| AI | `python scripts/serve_ai.py` | **8001** | http://127.0.0.1:8001/health |
| Backend | `python scripts/serve_backend.py` | **8000** | http://127.0.0.1:8000/health |
| Frontend | `python scripts/serve_frontend.py` | **5173** | http://127.0.0.1:5173/ |

```bash
# Terminal 1 — AI service
python scripts/serve_ai.py
# → http://127.0.0.1:8001/health

# Terminal 2 — Backend (proxy tới AI_BASE_URL, mặc định :8001)
python scripts/serve_backend.py
# → http://127.0.0.1:8000/health

# Terminal 3 — Frontend static
python scripts/serve_frontend.py
# → mở http://127.0.0.1:5173/
```

Kiểm tra nhanh (sau khi AI + Backend lên):

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8000/health
```

UI gọi Backend tại `http://127.0.0.1:8000` (xem `frontend/config.js`).
Đổi port: `--port` trên từng script, hoặc `AI_API_PORT` / `API_PORT` trong
`.env` (xem bảng bên dưới).

## Biến môi trường (Phase 6)

Nguồn mẫu: [`.env.example`](.env.example). Copy thành `.env` rồi chỉnh.

### Bắt buộc (local demo OpenAI)

| Biến | Mặc định / ví dụ | Dùng cho |
|---|---|---|
| `OPENAI_API_KEYS` | (điền key) | AI chat/scan khi `LLM_BACKEND=openai` |
| `LLM_BACKEND` | `openai` | Chọn backend LLM (`openai` / `ollama` / `vllm`) |

Nếu `LLM_BACKEND=ollama` hoặc `vllm`: không cần key OpenAI; có thể set
`LLM_BASE_URL` (vd. `http://localhost:11434/v1`).

### Tuỳ chọn (có mặc định ổn cho local)

| Biến | Mặc định | Dùng cho |
|---|---|---|
| `AI_BASE_URL` | `http://127.0.0.1:8001` | Backend → AI |
| `AI_API_HOST` / `AI_API_PORT` | `127.0.0.1` / `8001` | Bind AI process |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind Backend |
| `BACKEND_BASE_URL` | `http://127.0.0.1:8000` | Tài liệu / FE config |
| `FRONTEND_ORIGIN` | `*` (dev) | CORS Backend; siết: `http://127.0.0.1:5173` |
| `AI_HTTP_TIMEOUT` | `60` | Timeout Backend→AI (giây) |
| `SQLITE_PATH` | `./data/portfolio_watch.db` | DB phía AI |
| `BACKEND_SQLITE_PATH` | `./data/backend_store.db` | DB Backend (watchlist/approvals) |
| `LLM_MODEL` | `gpt-4o-mini` | Model chat |
| `DEFAULT_WATCHLIST` | `FPT,VNM,HPG` | Seed mã demo |
| `MONITORING_ENABLED` | `false` | Bật tracing Langfuse (AI process) |
| `LANGFUSE_PUBLIC_KEY` | (trống) | Public key project Langfuse |
| `LANGFUSE_SECRET_KEY` | (trống) | Secret key project Langfuse |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Cloud hoặc self-host (vd. `http://localhost:3000`) |

Frontend URL Backend: `frontend/config.js` (`BACKEND_BASE_URL`) hoặc
query `?backend=...` — không bắt buộc biến trong `.env` cho static FE.

## Chạy MVP một process (tham chiếu cũ)

Chỉ khi cần API AI gắn cổng 8000 (không phải stack 3 process chuẩn):

```bash
python -m src.portfolio_watch.main
# → http://127.0.0.1:8000/health
```

Docker một process AI cổng 8000 (không tách Backend/FE) — chỉ khi debug
cũ: `python -m src.portfolio_watch.main`. Stack demo chuẩn: **3 process
local** hoặc **Demo bằng Docker** bên dưới.

## Eval (Phase 6)

Dataset: [`specs/eval/golden_dataset.yaml`](specs/eval/golden_dataset.yaml)
(30 case). Runner: `scripts/run_eval.py`. Cần `.env` + LLM như Prerequisites
(không cần bật Backend/Frontend — eval gọi `answer_question` trực tiếp).

Windows nếu lỗi SSL cert: `unset SSL_CERT_FILE` (Git Bash) trước khi chạy.

### Một case (debug Quality Loop)

```bash
# Chỉ rule-based (nhanh nhất)
python scripts/run_eval.py --run --case-id lookup_01 --skip-judge --skip-agent-eval

# Rule + task_success / trajectory (mặc định agent-eval bật)
python scripts/run_eval.py --run --case-id lookup_01 --skip-judge

# Thêm LLM-judge (lookup / comparison)
python scripts/run_eval.py --run --case-id lookup_01
```

Đổi `lookup_01` → id khác trong golden (`comparison_01`, `injection_01`, …).

### Full golden (30 case)

```bash
# Offline scorer sanity (không gọi LLM/market)
python scripts/run_eval.py --self-check

# Full qua run_eval (có thể rate-limit vnstock guest)
python scripts/run_eval.py --run --skip-judge --baseline specs/eval/baseline_debug.json
# Nghỉ giữa case: thêm --case-delay 25

# Khuyến nghị sau FE/BE (subprocess từng case + retry rate-limit):
python scripts/phase5_regression.py --case-delay 20 --warmup 60
# → specs/eval/phase5_regression_report.md + baseline_phase5.json
```

Cờ hữu ích: `--skip-agent-eval` (chỉ rule), `--limit N`, `--save-baseline`.
Injection phải **100%**; regression drop ≤ `0.05` so với baseline (test-plan).

## Troubleshooting (Phase 6)

### Thiếu API key / LLM lỗi

| Triệu chứng | Cách xử lý |
|---|---|
| Chat/eval báo auth / invalid API key | Điền `OPENAI_API_KEYS` trong `.env` (không để `sk-proj-xxxxx` mẫu). Restart AI. |
| Dùng Ollama local | `LLM_BACKEND=ollama`, set `LLM_BASE_URL=http://localhost:11434/v1`; không cần OpenAI key. |
| Key có nhưng shell `source .env` lỗi | Đặt giá trị trong dấu ngoặc kép; hoặc để app/`python-dotenv` đọc `.env` (không cần `source`). |

### Port trùng

| Port | Process | Cách xử lý |
|---|---|---|
| **8001** | AI | Đổi `AI_API_PORT` + `AI_BASE_URL` cho khớp; hoặc `python scripts/serve_ai.py --port …` |
| **8000** | Backend | Đổi `API_PORT`; cập nhật `frontend/config.js` / `?backend=` |
| **5173** | Frontend | `python scripts/serve_frontend.py --port …` |

Windows xem ai chiếm cổng: `netstat -ano | findstr :8000` (đổi số port).

### AI unreachable / timeout

| Triệu chứng | Cách xử lý |
|---|---|
| Backend **502** `AI không kết nối được…` | Chưa bật AI, hoặc `AI_BASE_URL` sai. Kiểm tra `curl http://127.0.0.1:8001/health`. |
| Backend **502** `AI timeout` | Tăng `AI_HTTP_TIMEOUT` (giây) trong `.env`; hoặc AI quá chậm / LLM treo. |
| UI: «Không nối được Backend» | Backend `:8000` chưa chạy; hoặc FE `BACKEND_BASE_URL` sai. |
| Chat OK health nhưng treo | Tắt AI giữa chừng → Backend trả 502, FE không treo vô hạn (AbortController / timeout). |

Thứ tự đúng: **AI → Backend → Frontend**.

### CORS

| Triệu chứng | Cách xử lý |
|---|---|
| Browser chặn cross-origin (FE `:5173` → BE `:8000`) | `.env`: `FRONTEND_ORIGIN=*` (dev) hoặc `http://127.0.0.1:5173`. Restart Backend. |
| Vẫn lỗi sau khi đổi origin | Đúng origin URL đang mở (`127.0.0.1` ≠ `localhost`). Khớp `FRONTEND_ORIGIN` với thanh địa chỉ. |

Chi tiết CORS: [`backend/README.md`](backend/README.md).

## Demo with local

Demo trên máy của bạn qua **127.0.0.1** (không cần ngrok cho demo thường).
Cần `.env` + LLM key (hoặc Ollama). Thứ tự: **AI → Backend → Frontend**.

### Start Backend locally

```bash
# Terminal 2 — sau AI
python scripts/serve_backend.py
# → http://127.0.0.1:8000/health
```

Backend proxy `/chat`, `/scan`, watchlist, approvals tới AI (`AI_BASE_URL`,
mặc định `http://127.0.0.1:8001`).

### Start Frontend locally

```bash
# Terminal 3
python scripts/serve_frontend.py
# → http://127.0.0.1:5173/
```

### Start AI locally (Backend cần)

```bash
# Terminal 1 — bật trước Backend
python scripts/serve_ai.py
# → http://127.0.0.1:8001/health
```

### Expose Frontend on local

Mở trình duyệt tại:

**http://127.0.0.1:5173/**

| Port | Process | Local URL |
|---|---|---|
| **5173** | Frontend | http://127.0.0.1:5173/ |
| **8000** | Backend | http://127.0.0.1:8000/health |
| **8001** | AI | http://127.0.0.1:8001/health |

Dùng `127.0.0.1` thay vì `localhost` nếu `FRONTEND_ORIGIN` siết theo IP.

### Configure Frontend → local Backend URL

Mặc định FE gọi Backend tại `http://127.0.0.1:8000` — xem
[`frontend/config.js`](frontend/config.js):

```javascript
window.PW_CONFIG = {
  BACKEND_BASE_URL: "http://127.0.0.1:8000",
  // ...
};
```

**Cách 1 — sửa file** (ổn định): đổi `BACKEND_BASE_URL` nếu Backend chạy cổng
khác, ví dụ `http://127.0.0.1:9000`.

**Cách 2 — query tạm** (không sửa file):

```
http://127.0.0.1:5173/?backend=http://127.0.0.1:8000
```

Sau khi đổi Backend port hoặc URL, restart Frontend **không** bắt buộc (FE
đọc config/query lúc load trang).

### Expose Backend with ngrok (optional)

Chỉ khi cần người khác gọi **Backend API** từ internet (FE vẫn có thể chạy
local):

```bash
# Backend đang chạy :8000
ngrok http 8000
# Lấy URL dạng https://xxxx.ngrok-free.app
```

1. `.env`: `FRONTEND_ORIGIN=*` (hoặc origin FE thật) — restart Backend.
2. Mở FE với query trỏ ngrok Backend:
   `http://127.0.0.1:5173/?backend=https://xxxx.ngrok-free.app`
3. **Không** expose AI `:8001` ra ngrok — Backend vẫn gọi AI nội bộ qua
   `AI_BASE_URL=http://127.0.0.1:8001`.

Demo thuần local **không** cần ngrok.

### Demo scenario (watchlist → chat → scan)

In checklist: `python scripts/phase7_demo_checklist.py`

#### Seed watchlist

Backend tự seed `DEFAULT_WATCHLIST` (`FPT,VNM,HPG`) khi DB trống. Thêm tay:

```bash
curl -s -X POST http://127.0.0.1:8000/watchlist \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

#### Chat → timeline

1. Chat: `Giá FPT hôm nay?` → Timeline steps + câu trả lời.

#### Scan → duyệt (nếu có pending)

1. Quét mã `FPT` → Approvals → Duyệt/Từ chối nếu có pending.

Smoke (mock AI): `python -m pytest tests/test_phase4_manual_checklist.py -q`

Máy sạch: `python scripts/verify_clean_local.py` (hoặc
`VERIFY_USE_CURRENT=1 …`).

## Demo bằng Docker

Compose **3 service** (AI + Backend + Frontend) — cùng ranh giới process
local. Cần file `.env` (copy từ `.env.example`, điền `OPENAI_API_KEYS` nếu
dùng OpenAI).

| Service | Port host | Health / URL |
|---|---|---|
| `ai` | **8001** | http://127.0.0.1:8001/health |
| `backend` | **8000** (`APP_HOST_PORT`) | http://127.0.0.1:8000/health |
| `frontend` | **5173** | http://127.0.0.1:5173/ |

```bash
# Up (build lần đầu)
docker compose up --build

# Background
docker compose up --build -d

# Xem log
docker compose logs -f
docker compose logs -f ai
docker compose logs -f backend

# Down (giữ volume DB)
docker compose down

# Down + xóa volume SQLite (pw_data → /app/data)
docker compose down -v
```

Trong mạng compose, Backend gọi AI qua `AI_BASE_URL=http://ai:8001`.
Trình duyệt trên host vẫn dùng `http://127.0.0.1:8000` (FE `config.js`).
Volume `portfolio-watch-data` mount `/app/data` (AI `SQLITE_PATH` + Backend
`BACKEND_SQLITE_PATH`).

## Langfuse (Phase 8)

Tracing chạy trên **AI process** (Frontend → Backend → AI). Tắt mặc định —
chat vẫn OK khi `MONITORING_ENABLED=false` hoặc thiếu key (no-op).

### Bật monitoring

1. Cài package (một lần): `pip install langfuse`
2. Trong `.env` (copy từ `.env.example` nếu chưa có):

```bash
MONITORING_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
# Self-host ví dụ: LANGFUSE_HOST=http://localhost:3000
```

3. **Restart AI** (`python scripts/serve_ai.py`) — Backend/FE không cần key
   Langfuse. Windows nếu lỗi SSL: `unset SSL_CERT_FILE` trước khi chạy AI.

Key lấy trong Langfuse project → Settings → API Keys.

### Mở Langfuse

- Cloud: mở host trong `LANGFUSE_HOST` (thường `https://cloud.langfuse.com`)
  → đăng nhập → chọn project.
- Self-host: mở URL đó trên browser (vd. `http://localhost:3000`).
- Trang Traces / Observations (tên UI có thể khác nhẹ theo phiên bản).

### Tìm trace theo câu hỏi / request id

1. Chạy 3 process; mở UI `http://127.0.0.1:5173/` → Chat một câu
   (vd. `Giá FPT?`).
2. Lấy `request_id` từ response Backend:
   - DevTools → Network → `POST .../chat` → JSON field `request_id`, hoặc
   - `curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"Giá FPT?\"}"` → đọc `request_id`.
3. Trên Langfuse:
   - Tìm observation / span root tên **`chat`** (scan: **`scan`**) mới nhất, hoặc
   - Lọc / search metadata **`request_id`** trùng giá trị bước 2, hoặc
   - Search theo nội dung câu hỏi (input của root `chat`).
4. Mở trace: phải thấy **1 root** + span con agent (vd. `rewrite_question`,
   `supervisor`, `price_news_fetch`, `answer_composer`).

Checklist + probe tự động:

```bash
python scripts/phase8_langfuse_e2e.py --print-checklist
python scripts/phase8_langfuse_e2e.py   # cần MONITORING=true + key + host sống
```

Báo cáo mẫu: [`specs/eval/phase8_langfuse_e2e_report.md`](specs/eval/phase8_langfuse_e2e_report.md).

### Troubleshooting monitoring

| Triệu chứng | Cách xử lý |
|---|---|
| Chat OK nhưng không có trace | `MONITORING_ENABLED` chưa `true`, thiếu key, hoặc chưa restart **AI**. |
| Log cảnh báo thiếu `LANGFUSE_*` | Điền đủ public/secret key; tracing đang no-op. |
| Log init / flush Langfuse fail | Sai `LANGFUSE_HOST` / key / mạng — chat vẫn chạy (best-effort). |
| Không tìm thấy theo `request_id` | Spans nằm trên AI; đảm bảo chat đi qua Backend→AI; filter theo thời gian + name `chat`. |

## Tham chiếu kỹ thuật

- Eval agent path: `../llm-engineer-demo/app/agent_pr/eval.py`
- Tracing: `../llm-engineer-demo/app/monitoring/tracing.py`
- Kiến trúc agent (MVP): `docs/agent_graph.png` / `.mmd`
