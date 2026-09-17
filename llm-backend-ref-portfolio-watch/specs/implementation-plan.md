# Implementation Plan — Portfolio Watch & Chat Agent

## Kiến trúc thư mục (clean architecture, theo mẫu AI_Face_checkin)

```
src/portfolio_watch/
  api/                    # FastAPI: routers, request/response models, middleware
    routers/
      scan.py             # POST /scan (quét ngay 1 mã)
      chat.py             # POST /chat (hỏi-đáp)
      approvals.py        # GET/POST /approvals (HITL Gate 1 + 2)
      watchlist.py        # CRUD watchlist (không qua HITL cho thêm mã đầu tiên)
    helpers/
      middlewares.py
      exception_handler.py
  application/            # Use-case orchestration — gọi domain services theo đúng luồng
    scan_symbol.py         # luồng giám sát (1 mã): Price+News → Classifier → Eval → Synthesis → Gate
    answer_question.py     # luồng hỏi-đáp: Rewrite → Supervisor → workers → Answer → Guardrail
    review_approval.py     # xử lý approve/reject cho Gate 1 và Gate 2
  domain/
    agents/               # từng agent = 1 module, xem specs/agents.md
      price_agent.py       # hàm thuần, không LLM
      news_agent.py         # ReAct + LLM
      event_classifier.py
      eval_agent.py
      synthesis_agent.py
      supervisor.py         # routing cho nhánh hỏi-đáp
      answer_composer.py
    guardrails/
      output_checks.py     # chặn lời khuyên chắc chắn, đối chiếu evidence
    entities/             # dataclass/pydantic: Severity, FinalAlert, RoutingDecision...
    ports.py              # interface: PriceSource, NewsSource, WatchlistStore, PriceHistoryStore, MemoryStore, Notifier
  infra/
    market_data/
      price_source.py      # implement PriceSource — nguồn giá thật
      news_source.py        # implement NewsSource — cafef
    storage/
      watchlist_store.py    # SQLite/JSON
      price_history_store.py
      memory_store.py
    notify/
      console_notifier.py   # implement Notifier — log/console cho MVP
    llm/                    # tái dùng ý tưởng từ llm-engineer-demo (client, backends, resilience)
  shared/
    settings.py
    logging.py
  main.py                  # khởi tạo FastAPI app, wire dependencies
web/                      # frontend đơn giản (1 trang HTML/JS thuần)
  index.html
  app.js
```

Nguyên tắc: `domain/` không import `infra/` — chỉ phụ thuộc `ports.py`
(interface). `infra/` implement các port đó. `application/` wire domain +
infra lại theo đúng luồng nghiệp vụ. Đây là điểm khác biệt chính so với
llm-backend-ref hiện tại (đang trộn domain logic và infra trong cùng
`domain/service/`).

## Những gì tái dùng từ llm-engineer-demo (ý tưởng, không copy nguyên file)

| Từ llm-engineer-demo | Dùng cho | Ghi chú |
|---|---|---|
| `app/llm` (client, backends, resilience) | `infra/llm/` | Client OpenAI/Ollama/vLLM + retry/rotation — không đổi backend nào cả, chỉ chuyển vị trí + dọn code |
| `app/agent_m2/multi_agent/hierarchical.py` | Orchestrator, Supervisor | Pattern "1 node trung tâm gọi song song nhiều worker rồi gộp kết quả" |
| `app/agent/nodes.py` (ReAct loop, should_continue) | `news_agent.py`, `eval_agent.py` | Vòng lặp LLM ⇄ tool tổng quát |
| `app/optimization/routed/routing.py` | `synthesis_agent.py` | Model routing theo độ phức tạp sự kiện |
| `app/guardrails/checks.py` | `domain/guardrails/output_checks.py` | Rule-based checks; injection.py chỉ dùng nếu cần |
| `app/monitoring/tracing.py` | wiring ở `application/` | 1 span phẳng/lượt, no-op nếu tắt monitoring |
| `app/eval/agent_eval.py` (trajectory eval) | test/eval thủ công sau MVP | Không bắt buộc cho MVP, ghi chú để làm sau |

Code cũ trong `llm-backend-ref/src/chatbot/` (ReAct đơn-agent, guardrails/eval
rỗng) sẽ được **xóa và viết lại** theo cấu trúc trên — không giữ nguyên file,
chỉ giữ tinh thần kỹ thuật đã kiểm chứng (LLM client, settings pattern).

## Quyết định kỹ thuật MVP (mặc định, có thể đổi khi implement)

- **Lưu trữ:** SQLite (file, không cần Docker) cho Watchlist/Price
  History/Memory Store — đủ bền để demo, dễ nâng cấp Postgres sau vì đã có
  interface `ports.py`.
- **Gửi cảnh báo:** `ConsoleNotifier` (log ra console + ghi DB) implement
  `Notifier` — interface sẵn sàng cho SMTP/push thật sau này.
- **Cron:** dùng `APScheduler` (nhẹ, không cần thêm service ngoài) thay vì
  Celery/cron system thật.
- **LLM:** dùng lại `infra/llm/` (đa backend: OpenAI/Ollama/vLLM) đã có ở
  llm-engineer-demo — mặc định OpenAI `gpt-4o-mini` cho agent nhẹ (PriceAgent
  không cần LLM), model lớn hơn cho SynthesisAgent khi sự kiện phức tạp
  (model routing).
- **Multi-agent framework:** dùng LangGraph (đã quen thuộc qua
  llm-engineer-demo) cho các luồng có nhiều agent/vòng lặp (giám sát,
  hỏi-đáp); PriceAgent giữ là hàm Python thuần, không ép vào node LLM.
- **Frontend:** 1 trang HTML/JS thuần (`web/index.html`), không dùng
  framework nặng (React/Vue) — đủ để demo 3 luồng chính.
- **Demo packaging:** Docker Compose phục vụ demo ổn định (backend + static
  web trong một stack), biến môi trường qua `.env`, volume cho SQLite.

## Rủi ro / điểm cần quyết định khi implement

- Nguồn tin cafef có thể cần scraping (không có API chính thức) — cần xác
  nhận cách lấy dữ liệu trước khi viết `news_source.py`.
- Nguồn giá real-time miễn phí cho mã VN cần khảo sát nhanh (vnstock,
  SSI/TCBS public API, hoặc tương tự) — ghi quyết định vào change-log khi
  chọn xong.
- Ngưỡng "độ tin cậy cao" ở Confidence Gate (xem specs/agents.md) cần một
  công thức cụ thể (vd. confidence >= 0.8 và severity level khớp ngưỡng user)
  — sẽ chốt khi viết `synthesis_agent.py`.
- Docker image cần network ra ngoài để gọi LLM API và nguồn giá/tin; cần
  ghi rõ biến môi trường bắt buộc và cách mount volume SQLite để data không
  mất khi restart container.

---

## Phase 1 — Project setup

- [x] Xóa code cũ trong `src/chatbot/` (đã xác nhận với người dùng — chỉ giữ
      lại tinh thần kỹ thuật, không giữ file).
- [x] Tạo bộ khung thư mục mới `src/portfolio_watch/` theo cấu trúc ở trên
      (`api/`, `application/`, `domain/`, `infra/`, `shared/`), mỗi thư mục
      có `__init__.py`.
- [x] Tạo `pyproject.toml` (hoặc cập nhật file dependency hiện có) với các
      thư viện cần: `fastapi`, `uvicorn`, `langgraph`, `langchain-openai`
      (hoặc client tương ứng), `pydantic-settings`, `apscheduler`, `sqlite`
      (built-in — không cần thêm gói trừ khi dùng ORM).
- [x] Copy `shared/settings.py` + `.env.example` — thêm biến cấu hình riêng
      cho project này (watchlist mặc định, ngưỡng cảnh báo mặc định, nguồn
      giá/tin), dựa trên mẫu `settings.py` cũ nhưng bỏ phần không liên quan
      (RAG, embeddings...).
- [x] Copy/dọn `infra/llm/` từ `llm-engineer-demo/app/llm` (client, backends,
      resilience) — giữ nguyên hành vi, chỉ đổi vị trí + tên import.
- [x] `main.py` chạy được FastAPI rỗng với 1 endpoint `GET /health` → trả
      `{"status": "ok"}`.
- [x] Xác nhận `python -m src.portfolio_watch.main` (hoặc `uvicorn`) khởi
      động không lỗi.

## Phase 2 — Core UI

- [x] Tạo `web/index.html` với 3 khu vực tĩnh (chưa có dữ liệu thật):
      - Khung chat (ô nhập câu hỏi + khung hiển thị hội thoại).
      - Bảng watchlist (danh sách mã + ngưỡng cảnh báo).
      - Danh sách cảnh báo chờ duyệt (mỗi item có nút Approve/Reject).
- [x] Tạo `web/app.js` với các hàm gọi API rỗng (`fetch` tới các endpoint dự
      kiến ở Phase 4), tạm thời log ra console — chưa cần nối thật.
- [x] CSS tối thiểu (có thể inline hoặc 1 file `style.css`) — chỉ cần đọc
      được, không cần đẹp.
- [x] Xác nhận mở `web/index.html` trực tiếp trên trình duyệt (hoặc qua static
      file server đơn giản) hiển thị đúng 3 khu vực, không lỗi console.

## Phase 3 — Core backend / data logic

- [x] Domain entities (`domain/entities/`): `Severity`, `FinalAlert`,
      `RoutingDecision`, `WatchlistItem` — dataclass/pydantic model thuần,
      không phụ thuộc infra.
- [x] `domain/ports.py`: khai báo interface `PriceSource`, `NewsSource`,
      `WatchlistStore`, `PriceHistoryStore`, `MemoryStore`, `Notifier`.
- [x] `domain/agents/price_agent.py` — hàm thuần tính % thay đổi giá, có
      unit test với fake `PriceSource`.
- [x] `domain/agents/news_agent.py` — vòng lặp ReAct chọn từ khóa + lọc tin
      liên quan, có unit test với fake `NewsSource`.
- [x] `domain/agents/event_classifier.py` — phân loại bình thường/bất
      thường từ kết quả giá + tin.
- [x] `domain/agents/eval_agent.py` — sinh `Severity`, có thể gọi thêm
      `read_price_history` khi cần.
- [x] `domain/agents/synthesis_agent.py` + `domain/guardrails/output_checks.py`
      — soạn `FinalAlert`, áp guardrail, model routing theo độ phức tạp.
- [x] `infra/storage/*.py` — implement `WatchlistStore`, `PriceHistoryStore`,
      `MemoryStore` bằng SQLite (file `.db` local).
- [x] `infra/market_data/*.py` — implement `PriceSource`, `NewsSource` (nguồn
      thật, theo quyết định ở mục "Rủi ro" phía trên).
- [x] `infra/notify/console_notifier.py` — implement `Notifier` (log +
      ghi DB).
- [x] `application/scan_symbol.py` — ghép Orchestrator: Price+News →
      Classifier → Eval (nếu bất thường) → Synthesis → Guardrail →
      Confidence Gate → gửi thẳng hoặc tạo bản ghi chờ duyệt (Gate 1); đề
      xuất đổi ngưỡng luôn tạo bản ghi chờ duyệt (Gate 2).
- [x] `domain/agents/supervisor.py` + `answer_composer.py` +
      `application/answer_question.py` — luồng hỏi-đáp: Rewrite → Supervisor
      routing → gọi lại Price/News/Eval agent khi cần → soạn câu trả lời →
      Guardrail → trả lời (không qua HITL).
- [x] `application/review_approval.py` — xử lý approve/reject cho cả 2 Gate.
- [x] Cron: job định kỳ (APScheduler) gọi `scan_symbol` cho toàn bộ
      watchlist, lỗi ở 1 mã không chặn các mã khác.
- [x] Chạy toàn bộ unit test + integration test theo `test-plan.md` cho phần
      backend này (chưa cần API/UI).

## Phase 4 — Connect UI to data

- [x] `api/routers/scan.py` — `POST /scan` gọi `application/scan_symbol.py`,
      trả kết quả luồng giám sát cho 1 mã.
- [x] `api/routers/chat.py` — `POST /chat` gọi `application/answer_question.py`.
- [x] `api/routers/approvals.py` — `GET /approvals` (danh sách chờ duyệt),
      `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`.
- [x] `api/routers/watchlist.py` — CRUD watchlist cơ bản (thêm/xem/sửa
      ngưỡng, xóa mã).
- [x] Đăng ký toàn bộ router vào `main.py`, bật CORS cho phép `web/` gọi
      trực tiếp (dev, mọi origin).
- [x] Mount static `web/` từ FastAPI (hoặc phục vụ qua cùng origin) để UI
      và API dùng chung một base URL khi demo.
- [x] Sửa `web/app.js`: thay các hàm log-only ở Phase 2 bằng `fetch` gọi
      đúng 4 nhóm endpoint trên; hiển thị kết quả thật lên 3 khu vực UI.
- [x] Xác nhận thủ công: quét 1 mã → thấy kết quả trên UI; hỏi 1 câu → thấy
      câu trả lời; có cảnh báo chờ duyệt → approve/reject trên UI cập nhật
      đúng trạng thái.

## Phase 5 — Validation and error states

- [x] API validate input (symbol không tồn tại, ngưỡng âm, câu hỏi rỗng...)
      → trả lỗi 4xx rõ ràng thay vì 500 hoặc treo.
- [x] `PriceSource`/`NewsSource` lỗi hoặc timeout → agent trả kết quả rõ
      ràng ("không lấy được dữ liệu"), không làm crash toàn bộ luồng quét.
- [x] Cron: 1 mã lỗi trong watchlist không chặn các mã còn lại (đã có test ở
      Phase 3, xác nhận lại ở mức tích hợp).
- [x] Guardrail chặn đúng các case vi phạm (lời khuyên mua/bán chắc chắn, số
      liệu không khớp evidence) — xác nhận bằng test case cụ thể trong
      `test-plan.md`.
- [x] HITL: approve/reject một bản ghi không tồn tại hoặc đã xử lý rồi → trả
      lỗi rõ ràng, không đổi trạng thái ngoài ý muốn.
- [x] Frontend: hiển thị trạng thái lỗi cơ bản (vd. "Không lấy được dữ liệu,
      thử lại") khi API trả lỗi, không để UI treo trắng hoặc im lặng.
- [x] Rà lại toàn bộ acceptance criteria trong `product-spec.md` — xác nhận
      từng mục pass.

## Phase 6 — Local run instructions

- [x] Viết hướng dẫn chạy local vào `README.md`:
      - Cài dependency (`pip install -e .` hoặc tương đương).
      - Copy `.env.example` → `.env`, điền `OPENAI_API_KEYS` và các biến bắt
        buộc khác.
      - Khởi tạo SQLite (migration/script tạo bảng nếu cần).
      - Chạy backend: `python -m src.portfolio_watch.main` (hoặc lệnh
        `uvicorn` tương ứng), mặc định cổng nào.
      - Mở UI (trực tiếp `web/index.html` hoặc qua cùng origin với backend)
        trỏ tới đúng base URL API.
      - Chạy cron thủ công (nếu không muốn chờ lịch thật) — lệnh cụ thể.
- [x] Xác nhận làm theo đúng hướng dẫn từ máy sạch (hoặc virtualenv mới) chạy
      được toàn bộ 3 luồng chính không cần chỉnh sửa gì thêm.
- [x] Cập nhật `specs/change-log.md` ghi lại ngày hoàn thành từng phase.

## Phase 7 — Docker demo setup

- [x] Thêm `Dockerfile` cho app: cài dependency, copy source + `web/`, expose
      cổng API (vd. `8000`), lệnh chạy `uvicorn`/`main` sẵn sàng production-
      like cho demo.
- [x] Thêm `docker-compose.yml` với ít nhất 1 service app; map port host ↔
      container; mount volume cho file SQLite (data không mất khi restart).
- [x] Đảm bảo container đọc biến môi trường từ `.env` / `env_file` (không
      hard-code secret trong image); cập nhật `.env.example` với các biến
      Docker cần (host bind, đường dẫn DB trong volume, v.v.).
- [x] FastAPI phục vụ cả API và static `web/` trong container để demo chỉ cần
      mở một URL (vd. `http://localhost:8000`).
- [x] Viết mục "Demo bằng Docker" trong `README.md`:
      - Yêu cầu: Docker + Docker Compose đã cài.
      - Các bước: copy `.env`, `docker compose up --build`, mở URL UI.
      - Cách dừng / xem log / reset volume SQLite nếu cần demo sạch.
- [x] Xác nhận trên máy sạch: `docker compose up --build` rồi chạy được 3
      luồng chính (quét mã, chat, approve/reject) qua UI trong browser.
- [x] Ghi vào `specs/change-log.md` quyết định Docker (port, volume path,
      image base) và ngày hoàn thành Phase 7.
