# Portfolio Watch & Chat — Multi-Agent Stock (V3)

Theo dõi cổ phiếu VN: chat multi-agent (Claude-like UI + live graph), quét
watchlist, HITL, memory, trace Langfuse — **một process** phục vụ UI + API +
LangGraph.

Spec-Driven Development: đọc [specs/product-spec.md](specs/product-spec.md) và
[specs/implementation-plan.md](specs/implementation-plan.md) trước khi đổi code.
Quy tắc agent: [AGENTS.md](AGENTS.md).

---

## Prerequisites

| Yêu cầu | Ghi chú |
|---|---|
| **Python** ≥ 3.10 | Khuyến nghị 3.11–3.13 |
| **pip** / venv | Cài package từ `pyproject.toml` |
| **Docker Desktop** (tuỳ chọn) | Product demo 1 container `app` |
| **OpenAI API key** | Khi `LLM_BACKEND=openai` (chat/scan cần LLM) |
| Git | Clone repo |

Không bắt buộc: Node.js (frontend là static HTML/JS, không build).  
Không bắt buộc: Qdrant / Langfuse (tắt mặc định; bật khi cần Phase 8–9).

---

## Install (local)

Từ thư mục repo `llm-backend-ref-portfolio-watch`:

```bash
python -m venv .venv

# Windows (Git Bash / bash)
source .venv/Scripts/activate
# Windows CMD: .venv\Scripts\activate.bat
# macOS / Linux: source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
# Sửa .env — ít nhất OPENAI_API_KEYS nếu LLM_BACKEND=openai
mkdir -p data
```

---

## Environment variables

Nguồn chuẩn: [`.env.example`](.env.example). Copy thành `.env` (không commit key thật).

| Biến | Vai trò |
|---|---|
| `LLM_BACKEND` | `openai` \| `ollama` \| `vllm` |
| `OPENAI_API_KEYS` | Key OpenAI (có thể nhiều key, cách nhau bằng `,`) |
| `LLM_MODEL` | Ví dụ `gpt-4o-mini` |
| `LLM_BASE_URL` | Override base URL (Ollama/vLLM); để trống = mặc định |
| `API_HOST` / `API_PORT` | Local mặc định `127.0.0.1` / `8000` |
| `AI_TRANSPORT` | **`inprocess`** (khuyến nghị V3) — UI+API+graph cùng process |
| `FRONTEND_ORIGIN` | CORS; local gộp app dùng `*` |
| `SQLITE_PATH` | DB AI/domain — local `./data/portfolio_watch.db` |
| `BACKEND_SQLITE_PATH` | Watchlist + approvals — `./data/backend_store.db` |
| `MEMORY_SHORT_TERM_WINDOW` / `MEMORY_SHORT_TERM_TTL_MINUTES` | Short-term memory |
| `QDRANT_URL` | Long-term memory; trống = in-memory fallback |
| `MONITORING_ENABLED` | `false` mặc định; `true` + Langfuse keys để bật trace |
| `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Observability |
| `APP_HOST_PORT` | Port publish Docker (mặc định `8000`) |

Docker Compose ghi đè một số biến (`API_HOST=0.0.0.0`, đường dẫn DB trong
`/app/data`, …) — xem `docker-compose.yml`.

---

## Chạy local (dev)

### Backend + frontend (cùng origin — khuyến nghị)

Frontend static nằm ở `src/portfolio_watch/frontend/` và được **mount cùng
origin** bởi FastAPI (`StaticFiles`). Một lệnh:

```bash
python -m uvicorn src.portfolio_watch.backend.main:app --host 127.0.0.1 --port 8000
```

| URL | Nội dung |
|---|---|
| http://127.0.0.1:8000/ | UI (chat, live graph, watchlist, approvals) |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/docs | OpenAPI (Swagger) |

### Frontend tách port (tuỳ chọn, chỉ khi debug static)

Không cần cho flow V3 thường ngày. Nếu mở file bằng `http.server`:

```bash
python -m http.server 5173 --directory src/portfolio_watch/frontend
```

Khi đó đặt trong `config.js` / query: Backend
`http://127.0.0.1:8000` và CORS `FRONTEND_ORIGIN` phù hợp. Khuyến nghị vẫn dùng
cùng origin `:8000`.

### Smoke nhanh

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d "{\"question\":\"Gia FPT hom nay?\",\"user_id\":\"default\"}"
```

(Tránh ký tự Unicode trong curl trên một số shell Windows — dùng body ASCII
hoặc file JSON.)

### Tests

```bash
python -m pytest tests/ -q
# hoặc hẹp hơn:
python -m pytest tests/test_frontend.py tests/test_backend.py -q
```

---

## Docker deploy (product — 1 URL)

```bash
cp .env.example .env   # điền OPENAI_API_KEYS nếu cần
docker compose up --build -d
docker compose logs -f app
```

| Service | URL | Mô tả |
|---|---|---|
| **app** | http://localhost:8000 | UI + API + LangGraph in-process |
| Langfuse (tự host) | http://localhost:3000 | Ngoài compose — optional |
| Qdrant (optional) | http://localhost:6333 | `docker compose --profile qdrant up -d` |

Volume `pw_data` → `/app/data` (SQLite bền sau restart).

```bash
docker compose down
# Eval trong container:
docker compose run --rm app python -m src.portfolio_watch.eval.run --self-check
```

---

## Troubleshooting

| Triệu chứng | Gợi ý |
|---|---|
| `POST /chat` → 502 / timeout | Kiểm tra `OPENAI_API_KEYS`, `LLM_BACKEND`, mạng; tăng timeout nếu cần |
| UI cũ sau khi sửa frontend | Rebuild/restart container (`docker compose up -d --build app`) — image không mount source |
| curl `There was an error parsing the body` | Body JSON encoding (Windows shell) — dùng file `--data-binary @file.json` |
| Port 8000 đã chiếm | Đổi `API_PORT` / `APP_HOST_PORT` hoặc tắt process cũ |
| Qdrant / Langfuse lỗi | Để trống / `MONITORING_ENABLED=false` — app vẫn chat được |
| `vnstock` cảnh báo / rate limit | Thử lại; không chặn boot UI |
| Import / package thiếu | `pip install -e ".[dev]"` từ root repo |
| DB path | Local: `./data/…`; Docker: `/app/data/…` (compose override) |

---

## Specs & docs

| File | Nội dung |
|---|---|
| [specs/product-spec.md](specs/product-spec.md) | Mục tiêu, acceptance |
| [specs/implementation-plan.md](specs/implementation-plan.md) | Checklist phase |
| [specs/test-plan.md](specs/test-plan.md) | Kế hoạch test |
| [specs/change-log.md](specs/change-log.md) | Nhật ký |
| [specs/agents.md](specs/agents.md) | Domain agents |
| [docs/agent_graph.html](docs/agent_graph.html) | Sơ đồ kiến trúc (tĩnh) |

---

*Spec-Driven Development — specs trước, code sau. Không đổi logic app trong
bước cập nhật README này.*
