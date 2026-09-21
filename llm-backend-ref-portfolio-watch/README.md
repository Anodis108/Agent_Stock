# Portfolio Watch & Chat — Multi-Agent Stock (V2)

Theo dõi cổ phiếu VN: watchlist, cảnh báo bất thường (HITL), chat hỏi–đáp có
timeline bước agent + trace Langfuse lồng nhau.

**V2 complete** — product khuyến nghị chạy qua Docker; code trong `src/portfolio_watch/`.

## Tài liệu

| File | Nội dung |
|---|---|
| [specs/product-spec.md](specs/product-spec.md) | Mục tiêu, acceptance criteria |
| [specs/implementation-plan.md](specs/implementation-plan.md) | Phase 1–16 |
| [specs/test-plan.md](specs/test-plan.md) | Eval, Docker, Langfuse checklist |
| [specs/agents.md](specs/agents.md) | Mô tả agent + graph |
| [specs/mvp-status-report.md](specs/mvp-status-report.md) | MVP + V2 status |
| [AGENTS.md](AGENTS.md) | Quy tắc coding agent |

## Kiến trúc

```
src/portfolio_watch/
├── agents/          # price, news, supervisor, eval, synthesis, answer, classifier
├── graph/           # LangGraph chat + scan
├── backend/         # API :8000 (proxy AI qua HTTP)
├── frontend/        # UI static :5173
├── eval/            # golden runner + regression
├── ai_main.py       # AI service :8001
└── infra/monitoring/tracing.py  # Langfuse
```

```
Browser → Frontend (:5173) → Backend (:8000) → AI (:8001) → Langfuse (host :3000)
```

---

## Local development

Hướng dẫn chạy **ngoài Docker** (3 process). Không đổi logic app — chỉ lệnh và env.

### Prerequisites

- Python **≥ 3.10**
- `pip` / venv
- (Tuỳ chọn) Docker Desktop — nếu muốn chạy product bằng compose thay vì local
- (Tuỳ chọn) Langfuse self-host trên `:3000` nếu bật monitoring
- (Tuỳ chọn) Ollama nếu `LLM_BACKEND=ollama`

### Install

```bash
cd llm-backend-ref-portfolio-watch
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
# Langfuse (chỉ khi MONITORING_ENABLED=true):
# pip install langfuse
```

### Environment variables

```bash
cp .env.example .env
```

Biến quan trọng (chi tiết trong `.env.example`):

| Biến | Local mặc định | Ghi chú |
|---|---|---|
| `LLM_BACKEND` | `openai` | hoặc `ollama` / `vllm` |
| `OPENAI_API_KEYS` | — | Bắt buộc nếu `LLM_BACKEND=openai` |
| `LLM_MODEL` | `gpt-4o-mini` | |
| `AI_API_HOST` / `AI_API_PORT` | `127.0.0.1` / `8001` | Process AI |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Process Backend |
| `AI_BASE_URL` | `http://127.0.0.1:8001` | Backend → AI |
| `BACKEND_BASE_URL` | `http://127.0.0.1:8000` | Frontend → Backend |
| `FRONTEND_ORIGIN` | `*` hoặc `http://127.0.0.1:5173` | CORS Backend |
| `SQLITE_PATH` | `./data/portfolio_watch.db` | DB AI |
| `BACKEND_SQLITE_PATH` | `./data/backend_store.db` | DB Backend |
| `MONITORING_ENABLED` | `false` | Chat vẫn OK khi tắt |
| `LANGFUSE_HOST` | `http://localhost:3000` | **Local** (không dùng `host.docker.internal`) |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | — | Khi bật monitoring |

### Chạy từng process

Mở **3 terminal** (thứ tự: AI → Backend → Frontend).

**1. AI service (backend LLM / agents) — port 8001**

```bash
python -m src.portfolio_watch.ai_main
# hoặc:
uvicorn src.portfolio_watch.ai_main:app --host 127.0.0.1 --port 8001
```

**2. Backend API (proxy UI → AI) — port 8000**

```bash
python -m src.portfolio_watch.backend.main
# hoặc:
uvicorn src.portfolio_watch.backend.main:app --host 127.0.0.1 --port 8000
```

**3. Frontend (static UI) — port 5173**

```bash
python -m http.server 5173 --bind 127.0.0.1 --directory src/portfolio_watch/frontend
```

Frontend gọi Backend tại `http://127.0.0.1:8000` (`frontend/config.js`). Override tạm:

```text
http://127.0.0.1:5173/?backend=http://127.0.0.1:8000
```

### Local URLs

| Service | URL |
|---|---|
| Frontend | http://127.0.0.1:5173 |
| Backend health | http://127.0.0.1:8000/health |
| AI health | http://127.0.0.1:8001/health |
| Langfuse (nếu self-host) | http://localhost:3000 |

### Troubleshooting (local)

| Triệu chứng | Gợi ý |
|---|---|
| Backend 502 / chat timeout | AI chưa chạy hoặc `AI_BASE_URL` sai — kiểm tra `:8001/health` |
| CORS / UI không gọi được API | `FRONTEND_ORIGIN=*`; mở đúng `http://127.0.0.1:5173` |
| `OPENAI` lỗi auth | Điền `OPENAI_API_KEYS` trong `.env`; restart AI |
| Langfuse không thấy trace | Local: `LANGFUSE_HOST=http://localhost:3000` + keys + `MONITORING_ENABLED=true`; restart AI |
| Thiếu package / import lỗi | `pip install -e ".[dev]"` từ thư mục repo |
| DB trống / path lỗi | Tạo `./data` nếu cần; kiểm tra `SQLITE_PATH` / `BACKEND_SQLITE_PATH` |

### Test & eval (local)

```bash
pytest tests/ -q

python -m src.portfolio_watch.eval.run --self-check
python -m src.portfolio_watch.eval.run --run --case-id lookup_01 --skip-judge
```

---

## Chạy product (Docker — khuyến nghị)

```bash
cp .env.example .env   # điền OPENAI_API_KEYS nếu LLM_BACKEND=openai
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000/health |
| AI | http://localhost:8001/health |
| Langfuse (self-host, ngoài compose) | http://localhost:3000 |

```bash
docker compose down
docker compose logs -f ai
```

Trong Docker, AI dùng `LANGFUSE_HOST=http://host.docker.internal:3000` (compose đã set).

### Troubleshooting Docker

| Triệu chứng | Gợi ý |
|---|---|
| Backend 502 / chat lỗi | `docker compose ps` — `ai` phải healthy; `docker compose logs ai` |
| Langfuse không thấy trace | `.env`: `MONITORING_ENABLED=true` + keys; AI dùng `host.docker.internal:3000` |
| Chat OK nhưng không trace | Tắt monitoring vẫn chat bình thường — bật lại và restart `ai` |
| SQLite trống sau rebuild | Volume Docker `portfolio-watch-data` (`pw_data` trong compose) — `docker volume ls` |

## Demo nhanh (watchlist → quét → chat → Langfuse)

1. `docker compose up --build` **hoặc** chạy 3 process local ở trên
2. Mở http://localhost:5173 (hoặc http://127.0.0.1:5173)
3. **Watchlist:** thêm mã (vd. FPT) → **Quét** → xem timeline bước agent
4. **Chat:** hỏi "Giá FPT hôm nay?" → timeline + câu trả lời
5. (Tuỳ chọn) Bật Langfuse trong `.env` → gửi 1 chat → http://localhost:3000 → **1 trace**, expand ≥ 3 cấp span

## Langfuse

```env
MONITORING_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
# Local uvicorn:  http://localhost:3000
# Trong Docker AI: http://host.docker.internal:3000
LANGFUSE_HOST=http://localhost:3000
```

Checklist: 1 chat UI = 1 trace; span graph node (`supervisor`, `price_agent`, …) → span con (`fetch_quote`, `draft`, …).

## Eval golden (Docker)

```bash
docker compose run --rm ai python -m src.portfolio_watch.eval.run --run --case-id lookup_01 --skip-judge
docker compose run --rm ai python -m src.portfolio_watch.eval.run --self-check
docker compose run --rm ai python -m src.portfolio_watch.eval.regression --case-delay 20
docker compose run --rm ai python -m src.portfolio_watch.eval.run --run --skip-judge --slice injection
```

## Export graph

```bash
# Local
python -m src.portfolio_watch.graph.workflow

# Docker
docker compose run --rm ai python -m src.portfolio_watch.graph.workflow
```

---

*Spec-Driven Development — `specs/implementation-plan.md`*
