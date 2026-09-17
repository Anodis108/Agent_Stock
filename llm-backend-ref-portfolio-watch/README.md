# Portfolio Watch & Chat Agent

Multi-agent hệ thống theo dõi danh mục chứng khoán Việt Nam: tự động phát hiện
biến động giá/tin bất thường, đánh giá mức độ nghiêm trọng, soạn cảnh báo, và
trả lời câu hỏi tự do của người dùng về cổ phiếu họ đang theo dõi.

Đây là bản build lại theo Spec-Driven Development, dựa trên sơ đồ kiến trúc ở
`../portfolio-watch-agent-explained.md` (+ `.mmd`/`.png` cùng thư mục cha).

## Vì sao có project này

- `../llm-engineer-demo` là nơi học các khối kỹ thuật LLM riêng lẻ (tool
  calling, RAG, guardrails, multi-agent patterns, eval, observability) —
  nhưng chưa ghép thành một sản phẩm hoàn chỉnh, và code chưa đủ gọn.
- Project này **tận dụng ý tưởng/kỹ thuật** đã học ở đó (LLM client, model
  routing, guardrails, tracing...), ghép lại thành một ứng dụng multi-agent
  thật: theo dõi danh mục, phân loại sự kiện, đánh giá mức độ nghiêm trọng,
  soạn cảnh báo, có HITL (human-in-the-loop) khi cần duyệt.
- Kiến trúc thư mục theo clean architecture, tham khảo cách tổ chức của
  `../../AI_Face_checkin` (`api → application → domain → infra`, cộng
  `shared` cho phần dùng chung).

## Tài liệu

- [specs/product-spec.md](specs/product-spec.md) — sản phẩm làm gì, cho ai, MVP scope.
- [specs/implementation-plan.md](specs/implementation-plan.md) — kiến trúc, thứ tự build.
- [specs/test-plan.md](specs/test-plan.md) — cách kiểm chứng từng phần.
- [specs/change-log.md](specs/change-log.md) — nhật ký thay đổi theo thời gian.
- [AGENTS.md](AGENTS.md) — quy tắc làm việc của coding agent (spec-driven).
- [specs/agents.md](specs/agents.md) — mô tả từng domain agent (vai trò, input/output, tool).
- [specs/mvp-status-report.md](specs/mvp-status-report.md) — báo cáo trạng thái MVP cuối.

## Quick start (chọn 1 cách)

Hai cách chạy bằng terminal — **conda env `dong312`** hoặc **Docker Compose**.
UI + API cùng cổng **8000** → mở http://127.0.0.1:8000/ (hoặc http://localhost:8000/).

### Cách A — Conda env `dong312`

```bash
cd d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch

# Kích hoạt env (đã có sẵn trên máy)
conda activate dong312

# Lần đầu (hoặc khi dependency đổi)
pip install -U pip
pip install -e ".[dev]"

# .env — copy nếu chưa có; điền OPENAI_API_KEYS nếu dùng LLM OpenAI
cp .env.example .env          # Git Bash / Linux / macOS
# Copy-Item .env.example .env # PowerShell

# Chạy server
python -m src.portfolio_watch.main
# hoặc reload khi dev:
# uvicorn src.portfolio_watch.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở trình duyệt: **http://127.0.0.1:8000/**

Seed watchlist (terminal khác, env vẫn `dong312`):

```bash
conda activate dong312
curl -X POST http://127.0.0.1:8000/watchlist \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

Dừng: `Ctrl+C` trong terminal đang chạy uvicorn/main.

### Cách B — Docker Compose

Yêu cầu: Docker Desktop (hoặc Docker Engine + Compose) đang chạy.

```bash
cd d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch

# .env bắt buộc (compose dùng env_file: .env)
cp .env.example .env          # điền OPENAI_API_KEYS nếu cần
# Tuỳ chọn: APP_HOST_PORT=8000 trong .env

docker compose up --build
# nền: docker compose up --build -d
```

Mở: **http://localhost:8000/** · Health: http://localhost:8000/health

```bash
# Log
docker compose logs -f app

# Dừng (giữ SQLite volume)
docker compose down

# Dừng + xoá DB demo
docker compose down -v
```

Smoke 3 luồng (máy có Docker):

```bash
conda activate dong312   # hoặc bất kỳ Python có sẵn deps project
python scripts/verify_clean_docker.py
# Kỳ vọng: CLEAN_DOCKER_SMOKE_OK
```

### Thử nhanh sau khi server lên

| Việc | UI | curl |
|------|-----|------|
| Health | — | `curl http://127.0.0.1:8000/health` |
| Quét | Watchlist → Quét ngay `FPT` | `curl -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\"}"` |
| Chat | ô Chat | `curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"Giá FPT hiện tại?\"}"` |
| HITL | Cảnh báo chờ duyệt | `curl http://127.0.0.1:8000/approvals` |

Cần **mạng** để lấy giá/tin. Chi tiết env, troubleshooting, ngrok: các mục bên dưới.

---

## Chạy local

Hướng dẫn chi tiết (prerequisites, biến môi trường, troubleshooting).
Làm việc từ thư mục `llm-backend-ref-portfolio-watch/`.

### Prerequisites

| Thành phần | Yêu cầu |
|------------|---------|
| Python | **>= 3.10** — khuyến nghị conda env **`dong312`** (Python 3.12) |
| pip | Trong env đang active |
| Mạng | Cần cho giá (`vnstock`) / tin (CafeF) và (tuỳ chọn) OpenAI |
| Trình duyệt | Chrome / Edge / Firefox — mở UI |
| (Tuỳ chọn) OpenAI API key | Khi `LLM_BACKEND=openai` và muốn LLM thật |
| (Tuỳ chọn) Docker | Cách B — Docker Compose |

### Install (conda `dong312`)

```bash
cd llm-backend-ref-portfolio-watch
conda activate dong312
python -m pip install -U pip
pip install -e .
pip install -e ".[dev]"   # nếu chạy pytest
```

(Thay bằng `python -m venv .venv` nếu không dùng conda.)

### Environment variables

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Windows cmd
copy .env.example .env
```

Chỉnh `.env` theo bảng (chi tiết thêm trong `.env.example`):

| Biến | Bắt buộc? | Mặc định / ghi chú |
|------|-----------|-------------------|
| `OPENAI_API_KEYS` | Khi `LLM_BACKEND=openai` + LLM thật | Nhiều key cách nhau dấu phẩy. Không có key → vẫn chạy được nhiều luồng với heuristic; scan/chat cần mạng cho giá/tin. |
| `LLM_BACKEND` | Không | `openai` (hoặc `ollama` / `vllm`) |
| `LLM_MODEL` | Không | `gpt-4o-mini` |
| `API_HOST` | Không | `127.0.0.1` (local) |
| `API_PORT` | Không | `8000` |
| `SQLITE_PATH` | Không | `./data/portfolio_watch.db` |
| `DEFAULT_WATCHLIST` | Không | `FPT,VNM,HPG` (gợi ý; nên seed qua API nếu DB trống) |
| `DEFAULT_ALERT_THRESHOLD_PCT` | Không | `3.0` |
| `SCAN_INTERVAL_MINUTES` | Không | `60` |
| `PRICE_SOURCE` / `NEWS_SOURCE` | Không | `vnstock` / `cafef` |
| `MONITORING_ENABLED` | Không | `false` (LangFuse tuỳ chọn) |

### Khởi tạo SQLite

Không cần migration tay. Lần đầu app mở DB sẽ tạo thư mục `data/` và các bảng.

Chủ động tạo schema:

```bash
python -c "from src.portfolio_watch.shared.settings import settings; from src.portfolio_watch.infra.storage.sqlite_db import connect; connect(settings.sqlite_path); print('SQLite OK:', settings.sqlite_path)"
```

### Backend run command (conda `dong312`)

```bash
conda activate dong312
python -m src.portfolio_watch.main
```

Hoặc:

```bash
conda activate dong312
uvicorn src.portfolio_watch.main:app --host 127.0.0.1 --port 8000 --reload
```

Một process phục vụ **API + static UI** (không cần server frontend riêng).

### Frontend run command

UI nằm trong `web/` và được FastAPI mount tại `/` — **không** chạy
`npm start` / mở `web/index.html` bằng `file://` (dễ lệch CORS / base URL).

Chỉ cần backend đang chạy, rồi mở trình duyệt (xem Local URLs).

### Local URLs

| Mục | URL |
|-----|-----|
| UI (Chat / Watchlist / Approvals) | http://127.0.0.1:8000/ |
| Health | http://127.0.0.1:8000/health → `{"status":"ok"}` |
| OpenAPI docs | http://127.0.0.1:8000/docs |

Seed watchlist demo (nếu bảng trống — Quét/Chat cần mã trong list):

```bash
curl -X POST http://127.0.0.1:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

### Kiểm nhanh 3 luồng chính

1. **Quét:** UI → Quét ngay `FPT`, hoặc  
   `curl -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\"}"`
2. **Chat:** UI Chat hoặc  
   `curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"Giá FPT hiện tại?\"}"`
3. **HITL:** `GET /approvals` → `POST /approvals/{id}/approve` hoặc `.../reject` với `{"reason":"..."}`.

Quét cả watchlist một lần (scheduler không gắn sẵn vào lifespan):

```bash
python -c "from src.portfolio_watch.api.deps import get_app_deps; from src.portfolio_watch.application.scan_watchlist import scan_watchlist; d=get_app_deps(); r=scan_watchlist(watchlist_store=d.watchlist_store, price_source=d.price_source, news_source=d.news_source, history_store=d.history_store, memory_store=d.memory_store, notifier=d.notifier); print('scanned', r.scanned, 'failed', r.failed)"
```

### Chạy test / xác nhận máy sạch

```bash
pytest -q
python scripts/verify_clean_local.py
# Kỳ vọng: CLEAN_VENV_SMOKE_OK (cần mạng cho giá/tin thật)
```

### Troubleshooting

| Hiện tượng | Việc nên thử |
|------------|----------------|
| `ModuleNotFoundError: portfolio_watch` / import lỗi | Đã `cd` đúng thư mục project? Đã `pip install -e .` trong venv đang active? |
| Port `8000` bị chiếm | Đổi `API_PORT` trong `.env`, hoặc dừng process cũ; chạy lại `uvicorn ... --port <port>`. |
| UI trắng / API 404 khi mở file HTML | Mở **http://127.0.0.1:8000/** — không dùng `file://web/index.html`. |
| Scan/chat báo không lấy được giá/tin | Cần mạng; kiểm tra `PRICE_SOURCE`/`NEWS_SOURCE`; thử lại sau vài giây (nguồn ngoài có thể chậm). |
| Chat/scan “mã không trong watchlist” | Seed `POST /watchlist` (xem trên) hoặc thêm mã trên UI Watchlist. |
| LLM lỗi / hết quota OpenAI | Điền `OPENAI_API_KEYS` hợp lệ, hoặc tạm chấp nhận heuristic (nhiều agent vẫn chạy được trong test với Heuristic brains). |
| DB “lạ” / dữ liệu cũ | Xoá `./data/portfolio_watch.db` (hoặc đổi `SQLITE_PATH`) rồi chạy lại app. |
| Windows: lệnh `python` không tìm thấy | `conda activate dong312` rồi dùng `python` trong env; hoặc `py -3.12`. |
| `conda: command not found` | Mở Anaconda/Miniconda Prompt, hoặc `source "$(conda info --base)/etc/profile.d/conda.sh"` (Git Bash). |
| Docker `env_file .env` lỗi | Phải có file `.env` (copy từ `.env.example`) trước `docker compose up`. |
| Port 8000 chiếm (conda lẫn Docker) | Chỉ chạy **một** trong hai: dừng `Ctrl+C` hoặc `docker compose down`. |
| `verify_clean_local.py` fail | Đọc log tới dòng lỗi; thường thiếu mạng hoặc port conflict. |

## Eval golden dataset (Phase 9)

```bash
# Self-check scorers + runner stub (không gọi LLM/app)
python scripts/run_eval.py --self-check

# Chạy eval trên 30 case (gọi answer_question); --skip-judge để bỏ LLM-judge
python scripts/run_eval.py --run --skip-judge

# Lưu / so baseline regression (specs/eval/baseline.json)
python scripts/run_eval.py --run --save-baseline
```

Chi tiết slice và gate: `specs/test-plan.md` (Eval pipeline).

## Vẽ sơ đồ agent (Phase 10)

Sinh sơ đồ kiến trúc từ `StateGraph` (13 agent/gate, 2 nhánh + 2 HITL) theo
`specs/agents.md`:

```bash
# Ghi docs/agent_graph.mmd (bắt buộc, offline) + docs/agent_graph.png (nếu có mạng)
python scripts/draw_agent_graph.py

# Đối chiếu node/cạnh với agents.md + ánh xạ ../portfolio-watch-agent-v4.mmd
python scripts/draw_agent_graph.py --verify
```

Kỳ vọng: `VERIFY_OK` (13 node / 26 edge). Output: `docs/agent_graph.mmd`,
`docs/agent_graph.png` (PNG cần mermaid.ink).

## Demo with local (conda `dong312`)

Project này **một process** phục vụ cả backend API và frontend static (`web/`)
trên cổng **8000**. UI gọi API cùng origin (`API_BASE = ""` trong `web/app.js`).

### 1. Start the backend locally

```bash
cd d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch
conda activate dong312
pip install -e .          # nếu chưa cài trong env này
cp .env.example .env      # nếu chưa có .env

python -m src.portfolio_watch.main
```

Port: **8000** (`API_PORT` trong `.env`).

### 2. Start the frontend locally

Không chạy `npm` / Vite. Frontend đã được backend mount tại `/`.

Mở trình duyệt:

- UI: **http://127.0.0.1:8000/**
- Health: **http://127.0.0.1:8000/health**

### 3. Configure frontend API base URL (local backend)

Mặc định trong `web/app.js`:

```js
const API_BASE = "";
```

Giữ `""` khi mở UI qua **http://127.0.0.1:8000/** — mọi `fetch("/scan")`,
`fetch("/chat")`, … đi về local backend cùng host/port.

**Không** trỏ `API_BASE` sang URL khác nếu bạn đang demo local cùng origin
(tránh CORS / lệch môi trường). Chỉ đổi `API_BASE` khi cố ý tách UI và API
sang hai host (không phải luồng demo local mặc định).

Seed watchlist nếu trống:

```bash
curl -X POST http://127.0.0.1:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

### 4. Expose với ngrok (tuỳ chọn — demo từ máy khác / internet)

Cài [ngrok](https://ngrok.com/) và đăng nhập. Vì UI + API cùng cổng **8000**,
chỉ cần **một** tunnel:

```bash
# Terminal 1 — conda
conda activate dong312
python -m src.portfolio_watch.main

# Terminal 2 — expose cả UI và API
ngrok http 8000
```

Dùng HTTPS URL mà ngrok in ra (ví dụ `https://xxxx.ngrok-free.app`) để mở UI.
Vẫn giữ `API_BASE = ""` — browser gọi API trên **cùng** host ngrok.

**Không cần** tunnel ngrok thứ hai cho “backend riêng”, trừ khi bạn tách
frontend/backend thành hai process/port (kiến trúc hiện tại không làm vậy).

Nếu bắt buộc hai URL ngrok (hiếm): đặt `API_BASE` trong `web/app.js` thành
URL ngrok của backend, rồi serve UI từ tunnel frontend — dễ gặp CORS; MVP
khuyến nghị một tunnel vào port **8000**.

### 5. Kiểm nhanh sau khi demo local

1. http://127.0.0.1:8000/health → `{"status":"ok"}`
2. UI: Quét `FPT` / Chat / Approvals
3. (Nếu dùng ngrok) mở URL ngrok → cùng 3 luồng

## Demo bằng Docker Compose

Xem **Quick start → Cách B** ở trên. Tóm tắt:

```bash
cd d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch
cp .env.example .env    # nếu chưa có
docker compose up --build
```

- UI: http://localhost:8000/
- Health: http://localhost:8000/health → `{"status":"ok"}`
- Volume SQLite: `portfolio-watch-sqlite` → `/app/data/portfolio_watch.db`

### Chuẩn bị `.env` cho Compose

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Điền `OPENAI_API_KEYS` nếu dùng LLM OpenAI. Nên dùng `.env` chỉ chứa biến
Portfolio Watch (xem ghi chú Docker trong `.env.example`). Tuỳ chọn:

- `APP_HOST_PORT=8000` — cổng mở trên máy host (mặc định 8000).

### 2. Build và chạy

```bash
docker compose up --build
```

Chạy nền:

```bash
docker compose up --build -d
```

Mở **một URL** (API + UI cùng origin):

- UI: http://localhost:8000/
- Health: http://localhost:8000/health → `{"status":"ok"}`

Seed watchlist nếu trống (Quét / Chat cần mã trong list):

```bash
curl -X POST http://localhost:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

### 3. Dừng / log / reset SQLite

```bash
# Xem log
docker compose logs -f app

# Dừng container (giữ volume SQLite)
docker compose down

# Reset demo sạch — xoá luôn volume DB
docker compose down -v
# Volume name: portfolio-watch-sqlite  (mount /app/data trong container)
```

SQLite nằm trên volume Docker `portfolio-watch-sqlite` → `/app/data/portfolio_watch.db`
(không mất khi `restart` / `down` nếu không dùng `-v`).

### 4. Kiểm nhanh 3 luồng (Docker)

Cần Docker daemon đang chạy. Script `compose up --build`, gọi cùng API mà UI
dùng (health / UI HTML / quét / chat / approve+reject), rồi `compose down`:

```bash
python scripts/verify_clean_docker.py
# In: CLEAN_DOCKER_SMOKE_OK
```

Tuỳ chọn xoá luôn volume DB sau khi chạy: `VERIFY_DOCKER_DOWN_V=1 python scripts/verify_clean_docker.py`.

## Prompt Registry (Phase 8)

Prompts git-based trong `prompts/<name>/vN.yaml` + `production.txt`. Đổi
`production.txt` → agent dùng version mới (không sửa code gọi). Chi tiết:
`specs/agents.md`, `tests/test_prompt_registry.py`.
