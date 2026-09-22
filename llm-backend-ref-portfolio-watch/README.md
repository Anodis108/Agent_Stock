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
| **Docker Desktop** | Bắt buộc để chạy product demo |
| Git | Clone repo |
| **OpenAI API key** | Nếu cấu hình LLM_BACKEND=openai |

---

## Quick Start (Docker-first)

Product được đóng gói để chạy hoàn toàn qua Docker.

1. Clone repo:
   ```bash
   git clone <repo_url>
   cd llm-backend-ref-portfolio-watch
   ```
2. Cấu hình môi trường:
   ```bash
   cp .env.example .env
   # Sửa .env — cấu hình ít nhất OPENAI_API_KEYS
   ```
3. Build và chạy:
   ```bash
   docker compose up --build -d
   docker compose logs -f app
   ```

Biến môi trường: copy từ [`.env.example`](.env.example) — memory, Langfuse, Qdrant (optional).

Volume `pw_data` → `/app/data` (SQLite bền sau restart). Qdrant optional:
`docker compose --profile qdrant up -d`.

Truy cập:
| Service | URL | Mô tả |
|---|---|---|
| **app** | http://localhost:8000 | UI (chat, live graph, watchlist) + API |
| Langfuse (tự host) | http://localhost:3000 | Tùy chọn (ngoài compose) |
| Qdrant | http://localhost:6333 | Tùy chọn |

*Contributors dev local — xem [Optional local development](#optional-local-development).*

---

## Demo walkthrough (5 phút)

Prerequisite: Chạy `docker compose up -d`, mở http://localhost:8000.

1. **Chat**: Gửi "Giá FPT hôm nay?" ở cột trái — thấy câu trả lời assistant.
2. **Live graph**: Panel bên phải node sẽ sáng lần lượt; hover node → inspector hiện input/output chi tiết.
3. **Market**: Chuyển sang tab Market status → xem danh sách mã watchlist (giá/%/trạng thái).
4. **Langfuse (optional)**: Bật `MONITORING_ENABLED=true` + keys trong `.env`, restart; thực hiện 1 chat → 1 trace trên Langfuse UI.

---

## Eval (in container)

Chạy test/đánh giá hoàn toàn thông qua container (không cần cài local):

- **Self-check**:
  ```bash
  docker compose run --rm app python -m src.portfolio_watch.eval.run --self-check
  ```
- **Chạy 1 case cụ thể (skip judge)**:
  ```bash
  docker compose run --rm app python -m src.portfolio_watch.eval.run --run --case-id lookup_01 --skip-judge
  ```
- **Full regression**:
  ```bash
  docker compose run --rm app python -m src.portfolio_watch.eval.regression
  ```

---

## Troubleshooting

| Triệu chứng | Gợi ý |
|---|---|
| `POST /chat` → 502 / timeout | Kiểm tra `OPENAI_API_KEYS` trong `.env`, restart container |
| UI cũ sau khi update | Rebuild lại image: `docker compose up --build app` |
| Port 8000 đã chiếm | Đổi `APP_HOST_PORT` trong `.env` |
| Dừng stack | `docker compose down` |

---

## Optional local development

> **Product path = Docker** (xem Quick Start). Phần này dành cho **contributors** dev/test local — không thay đường chính AC9.

| Yêu cầu | Ghi chú |
|---|---|
| Python 3.10+ | Khớp `pyproject.toml` |
| venv | Khuyến nghị |

1. Tạo và kích hoạt venv:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   ```
2. Cài dependencies + dev tools:
   ```bash
   pip install -e ".[dev]"
   ```
3. Cấu hình môi trường:
   ```bash
   cp .env.example .env
   # Sửa .env — ít nhất OPENAI_API_KEYS
   ```
4. Chạy app (UI + API + LangGraph, một process):
   ```bash
   uvicorn src.portfolio_watch.backend.main:app --reload --port 8000
   ```
5. Mở http://localhost:8000
6. Chạy test:
   ```bash
   python -m pytest tests/ -q
   ```

**Troubleshooting (local):** port 8000 bận → đổi `--port`; lỗi x509/SSL với conda → `unset SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE`.

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
