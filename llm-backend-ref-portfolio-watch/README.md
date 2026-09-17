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

## Chạy local (Phase 6)

Yêu cầu: Python **>= 3.10**. Làm việc từ thư mục `llm-backend-ref/`.

### 1. Cài dependency

```bash
python -m pip install -U pip
pip install -e .

# (tuỳ chọn) chạy test
pip install -e ".[dev]"
```

### 2. Cấu hình môi trường

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Windows cmd
copy .env.example .env
```

Mở `.env` và điền tối thiểu:

| Biến | Bắt buộc? | Ghi chú |
|------|-----------|---------|
| `OPENAI_API_KEYS` | Khi `LLM_BACKEND=openai` và dùng LLM composer | Key OpenAI (nhiều key cách nhau dấu phẩy). Nhiều luồng MVP dùng heuristic — vẫn chạy được scan/chat/HITL với fake/heuristic; giá/tin thật cần mạng (`vnstock` / CafeF). |
| `API_HOST` / `API_PORT` | Không | Mặc định `127.0.0.1` / `8000`. |
| `SQLITE_PATH` | Không | Mặc định `./data/portfolio_watch.db`. |
| `DEFAULT_WATCHLIST` | Không | Mã seed gợi ý (FPT,VNM,HPG) — vẫn nên thêm qua API/UI nếu DB trống. |
| `SCAN_INTERVAL_MINUTES` | Không | Dùng khi gắn cron vào process (Phase 6 xác nhận / Phase 7 Docker). |

### 3. Khởi tạo SQLite

Không cần migration tay. Lần đầu app (hoặc store) mở DB, `sqlite_db.connect()` sẽ:

- tạo thư mục cha của `SQLITE_PATH` (vd. `./data/`);
- tạo bảng (`watchlist`, `price_history`, `preferences`, `conversations`,
  `alert_events`, `rejections`) nếu chưa có.

Có thể chủ động tạo schema trước khi chạy server:

```bash
python -c "from src.portfolio_watch.shared.settings import settings; from src.portfolio_watch.infra.storage.sqlite_db import connect; connect(settings.sqlite_path); print('SQLite OK:', settings.sqlite_path)"
```

### 4. Chạy backend

```bash
python -m src.portfolio_watch.main
```

Tương đương:

```bash
uvicorn src.portfolio_watch.main:app --host 127.0.0.1 --port 8000 --reload
```

- API + static UI: **http://127.0.0.1:8000/**
- Health: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`

### 5. Mở UI

Mở trình duyệt tới **http://127.0.0.1:8000/** (cùng origin với API — `web/` được
FastAPI mount tại `/`). Không cần mở `web/index.html` bằng `file://` (dễ lệch
CORS / base URL).

Ba khu vực UI: Chat, Watchlist (+ Quét ngay), Cảnh báo chờ duyệt.

Seed watchlist demo (nếu bảng trống):

```bash
curl -X POST http://127.0.0.1:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

### 6. Chạy cron / quét watchlist thủ công

Scheduler interval **chưa** gắn sẵn vào `main.py` lifespan (tránh side-effect
khi demo API). Để quét cả watchlist một lần (test-plan #7), chạy:

```bash
python -c "from src.portfolio_watch.api.deps import get_app_deps; from src.portfolio_watch.application.scan_watchlist import scan_watchlist; d=get_app_deps(); r=scan_watchlist(watchlist_store=d.watchlist_store, price_source=d.price_source, news_source=d.news_source, history_store=d.history_store, memory_store=d.memory_store, notifier=d.notifier); print('scanned', r.scanned, 'failed', r.failed)"
```

Hoặc quét một mã qua API/UI: `POST /scan` với `{"symbol":"FPT"}`.

### 7. Kiểm nhanh 3 luồng chính

1. **Quét:** UI → Quét ngay `FPT`, hoặc `curl -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\"}"`
2. **Chat:** UI Chat hoặc `curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"question\":\"Giá FPT hiện tại?\"}"`
3. **HITL:** nếu có pending → `GET /approvals` rồi `POST /approvals/{id}/approve` hoặc `.../reject` với `{"reason":"..."}`.

### 8. Xác nhận máy sạch / virtualenv mới

Script tự động (venv tạm + `pip install -e .` + 3 luồng), không cần sửa code:

```bash
python scripts/verify_clean_local.py
```

Kỳ vọng log kết thúc bằng `CLEAN_VENV_SMOKE_OK` (cần mạng cho giá/tin thật).

### Chạy test

```bash
pytest -q
```

## Demo bằng Docker

Yêu cầu: **Docker** và **Docker Compose** đã cài (Docker Desktop trên Windows/macOS,
hoặc engine + plugin `compose` trên Linux).

### 1. Chuẩn bị `.env`

Từ thư mục `llm-backend-ref/`:

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
