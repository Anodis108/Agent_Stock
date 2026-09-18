# backend/

API sản phẩm, deploy độc lập (Phase 3b).

- **Port:** `8000` (`API_HOST` / `API_PORT`)
- **Gọi tới AI:** `AI_BASE_URL` → `http://127.0.0.1:8001` (`/v1/chat`, `/v1/scan`)
- **Ranh giới (AC7):** **Không** import `src.portfolio_watch.domain.agents`
  (cũng không `application` / langgraph). Chat/scan chỉ qua
  `backend/ai_client.py` (HTTP `urllib`).

Chứng minh tự động: `pytest tests/test_backend_no_agent_imports.py`.

## CORS

- Biến `FRONTEND_ORIGIN` (xem `.env.example`):
  - `*` (mặc định nếu trống / `*`) — dev mở mọi origin;
  - hoặc `http://127.0.0.1:5173` — chỉ origin Frontend.
- Preflight OPTIONS cho `POST /chat`, `/scan`, CRUD watchlist/approvals.

## Chạy

```bash
# Terminal AI (nếu cần chat/scan)
python scripts/serve_ai.py

# Terminal Backend
python scripts/serve_backend.py
# hoặc: python -m backend.main
```

## Endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | Health backend |
| GET/POST/PATCH/DELETE | `/watchlist`… | CRUD watchlist (**SQLite Backend**) |
| GET | `/approvals` | Pending duyệt (**SQLite Backend**) |
| POST | `/approvals/{id}/approve` \| `/reject` | Duyệt / từ chối (**SQLite**) |
| POST | `/chat` | Proxy → AI `/v1/chat`; luôn trả `answer` + `steps[]` + `run_id` |
| POST | `/scan` | Proxy → AI `/v1/scan` (+ ingest pending, `steps[]`) |
| GET | `/runs/{run_id}` | Kết quả run (result + steps) |
| GET | `/runs/{run_id}/steps` | Chỉ `steps[]` (MVP one-shot; FE timeline đọc endpoint này) |

## Nơi lưu dữ liệu

| Dữ liệu | Process | File |
|---|---|---|
| Watchlist + approvals (product UI) | **Backend** | `BACKEND_SQLITE_PATH` (mặc định `./data/backend_store.db`) |
| Chat memory / price history / AI watchlist nội bộ | **AI** | `SQLITE_PATH` (mặc định `./data/portfolio_watch.db`) |
| Runs (steps one-shot) | Backend | in-memory (ephemeral) |

Frontend **chỉ** gọi Backend cho CRUD/approve/reject — không ghi SQLite AI.

## Validation (Phase 5)

Input lỗi → **400** với `detail` rõ (không 500):
- Chat: câu hỏi rỗng / chỉ khoảng trắng
- Symbol: rỗng hoặc không đúng 3 chữ cái (watchlist / scan)
- Ngưỡng: âm → «ngưỡng không được âm»; =0 → «phải > 0»

AI down / timeout (Backend→AI): **502** với `detail` (`AI timeout` hoặc
`AI không kết nối được…`). Biến `AI_HTTP_TIMEOUT` (giây, mặc định 60).
