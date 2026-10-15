# VN Stock Swarm & Portfolio Watch — Đồ Án Cuối Khóa LLM Engineer

Hệ thống Trợ lý Phân tích Chứng khoán Đa Tác tử (Multi-Agent Swarm) và Quản lý Danh mục Đầu tư Đa Tài khoản (Multi-tenant Portfolio Watch), phát triển theo phương pháp **Spec-Driven Development (SDD)**.

## Đợt cập nhật hiện tại (chưa code)

Tái cấu trúc Clean Architecture theo chuẩn `AI_Face_checkin` phân rã thành 3 khối chuyên biệt:
- **`src/common/`**: Shared Kernel dùng chung (`base/` với `CustomBaseModel` và `BaseService`/`AsyncBaseService`, `domain/` với thực thể và indicators thuần túy, `logging/`, `settings/`, `transport/`, và `tests/`).
- **`src/web_backend/`**: Microservice Web Gateway cổng 8000 (`api/`, `application/`, `domain/`, `infra/`, `shared/`, và `tests/`).
- **`src/ai_backend/`**: Microservice AI Swarm Engine cổng 8001 (`api/`, `application/`, `domain/`, `infra/`, `shared/`, và `tests/`).
- **`tests/e2e/`**: Kiểm thử liên dịch vụ, Golden Dataset v6 20/20 cases, Docker setup, Capstone Gate.

Public từ chính máy này, chưa thuê cloud. Nginx nghe cổng 80 và chuyển vào web `127.0.0.1:8000`. Cloudflare Tunnel (`cloudflared`) mở HTTPS ra internet mà không cần mở port modem. ngrok vẫn là demo nhanh.

Chưa triển khai. Spec: [specs/product-spec.md](specs/product-spec.md), [specs/implementation-plan.md](specs/implementation-plan.md), [specs/test-plan.md](specs/test-plan.md).

Kế hoạch 6 phase theo `specs/implementation-plan.md`:
1. Shared Kernel (`src/common/`)
2. Web Backend Microservice (`src/web_backend/`)
3. AI Backend Microservice (`src/ai_backend/`)
4. Inter-Service Wiring & Cleanup
5. Verification of 4-Tier Test Suites & Golden v6
6. Docker Compose, Nginx & Deployment Verification

## Demo with ngrok

Web local phục vụ UI và API cùng origin trên cổng **8000**. Khi chạy local tách hai service, Web Backend nghe cổng 8000 và AI Backend nghe cổng 8001:

```bash
# Cửa sổ 1 — Web Backend cổng 8000:
uvicorn web_backend.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
# Cửa sổ 2 — AI Backend cổng 8001:
uvicorn ai_backend.main:app --app-dir src --host 127.0.0.1 --port 8001 --reload
# Cửa sổ 3 — Mở ngrok cho cổng 8000:
ngrok http 8000
```

Mở URL `https` mà ngrok in ra để tương tác trực tiếp với Web App.

Docker: frontend cổng **3001**, web cổng **8000**. `docker compose up -d` chạy toàn bộ dịch vụ. Nginx của frontend chuyển `/chat` về web, nên trang và API cùng origin trên cổng 3001.

```bash
docker compose up -d
ngrok http 8000
ngrok http 3001
```

Mở URL `https` của cổng muốn demo. Cổng 3001 là trang Docker. Cổng 8000 là process web. Nếu trang và API không cùng origin, sửa `BACKEND_BASE_URL` trong `src/frontend/config.js` thành URL `https` của tunnel cổng 8000. Mặc định để trống, nghĩa là cùng origin.

`proxy_buffering` của nginx đã tắt cho route stream, để token SSE không bị giữ đến khi model sinh xong.

## Public HTTPS với Cloudflare Tunnel (`publish.ps1`)

Khởi chạy Cloudflare Tunnel để cấp URL HTTPS công khai ra Internet trỏ thẳng vào Nginx cổng 80:

```powershell
powershell -ExecutionPolicy Bypass -File src/deploy/publish.ps1
```

Script sẽ kiểm tra Nginx và in ra URL `https://<subdomain>.trycloudflare.com`:
- **Kiểm tra sức khỏe**: `GET https://<subdomain>.trycloudflare.com/health` trả về HTTP 200 `{"status": "ok", ...}`.
- **Kiểm tra câu khái niệm**: Mở URL trên trình duyệt và gửi `"RSI là gì"`, câu trả lời hiển thị trích dẫn nguồn `Nguồn: rsi-va-sma.md`.

---

## 1. Giới Thiệu & Mục Tiêu Dự Án (Project Overview)

Dự án là sản phẩm đồ án tốt nghiệp cuối khóa, giải quyết bài toán hỗ trợ nhà đầu tư cá nhân trên thị trường chứng khoán Việt Nam:
1. **Độ chính xác cao & Khách quan tuyệt đối**: Vượt qua **100% (20/20 test cases)** bộ dữ liệu chuẩn hóa [resources/eval/golden_v6_comprehensive.yaml](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/resources/eval/golden_v6_comprehensive.yaml) trên 10 lát cắt chức năng (`lookup`, `news`, `indicator`, `comparison`, `portfolio`, `watchlist`, `chart`, `out_of_scope`, `injection`, `disclaimer`).
2. **Luồng Chào Hỏi Tức Thì (Greeting Fast-Path)**: Nhận diện câu chào giao tiếp ("Xin chào", "Hello", "Hi bot") là an toàn ngay tại Input Guardrail và nối thẳng sang Chat LLM/Composer (TTFT < 1.0s), không bị từ chối và không kích hoạt tra cứu giá ảo.
3. **Quản Lý Danh Mục Đa Tài Khoản (Multi-tenant Portfolio)**: Cô lập dữ liệu nắm giữ (Holdings, Unrealized P&L, NAV) và danh sách theo dõi (Watchlist) giữa các người dùng (`User A`, `User B`, `Default`).
4. **Kiến Trúc Tách Biệt Cấu Hình (Config Decoupling)**: File `.env` chỉ chứa các biến bí mật (API Keys); toàn bộ cấu hình hệ thống được quản lý tập trung tại [resources/configs/config.yaml](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/resources/configs/config.yaml).
5. **Cấu Trúc Mã Nguồn Sạch Sẽ (Clean Modular Architecture)**: Toàn bộ code nằm trong `src/` (`src/backend/`, `src/frontend/`, `src/deploy/`), gốc dự án sạch sẽ chỉ chứa các tệp tĩnh và hồ sơ đặc tả SDD.
6. **Kiểm Thử 3 Tầng Chuẩn Mực (3-Tier Test Suite)**: Phân tầng `tests/unit/`, `tests/integration/`, `tests/e2e/`, hỗ trợ mock offline bảo đảm pipeline CI chạy hoàn tất trong **< 5 phút**.

---

## 2. Bản Đồ Ánh Xạ Kiến Thức Khóa Học (Curriculum Mapping)

| Module Khóa Học | Kỹ Thuật Đã Học | Hiện Thực Trong Dự Án | Vị Trí Mã Nguồn |
| :--- | :--- | :--- | :--- |
| **Module 1: LLM APIs, Prompting & RAG** | Structured Outputs (Pydantic), Provider Cascade & Fallback, 2-Tier Cache, Input & Output Guardrails | Pydantic Schema, Fallback Ollama/Offline khi mất mạng, Cache MD5 + Cosine 0.93, Tường lửa 2 lớp | `src/backend/infra/llm/`, `src/backend/infra/cache/`, `src/backend/domain/guardrails/` |
| **Module 2: AI Agents & LangGraph** | StateGraph, Conditional Edges, Supervisor Pattern, Tool Calling, Short-term Memory (TTL + Window) | Swarm gồm 7 Worker Agents, điều phối Supervisor, tool Vnstock/CafeF/Matplotlib, Sliding Window 20 tin nhắn TTL 60p | `src/backend/graph/`, `src/backend/agents/`, `src/backend/domain/memory/` |
| **Module 3: Production LLMOps & CI/CD** | Prompt Registry (alias `production`), Golden Slices, Eval Gate, Token & Cost Governance, Docker, CI/CD | Prompt Registry tập trung, 20 test cases v6, so sánh baseline gate, đo token từng câu, GitHub Actions CI/CD < 5m | `src/backend/infra/llm/prompt_registry.py`, `src/backend/eval/`, `src/backend/infra/cost/`, `.github/workflows/` |

---

## 3. Kiến Trúc Swarm Multi-Agent & Luồng Dữ Liệu

```mermaid
graph TD
    User([Người dùng / Web UI :8000]) --> API[FastAPI Gateway: src/backend/api/]
    
    subgraph Config & Secrets
        Env[".env (Chỉ chứa Secrets: API Keys)"]
        Yaml["resources/configs/config.yaml (Master App Config)"]
    end
    Env -.-> Settings[Settings Loader]
    Yaml -.-> Settings
    Settings --> API

    API --> Guardrail[1. Input Guardrail]
    Guardrail -->|Tấn công Injection / Phi tài chính| Refusal[Từ chối an toàn / Lịch sự]
    Guardrail -->|Chào hỏi: Greeting Fast-Path| Composer[Answer Composer: TTFT < 1.0s]
    Guardrail -->|Câu hỏi chứng khoán hợp lệ| Rewrite[2. Rewrite & Decomposition]

    Rewrite --> Supervisor[3. Supervisor Orchestrator]
    
    subgraph Swarm Worker Agents
        Supervisor --> PriceAgent[Price Agent: Vnstock OHLCV]
        Supervisor --> NewsAgent[News Agent: CafeF & Vnstock]
        Supervisor --> IndicatorEngine[Indicator Engine: RSI / SMA]
        Supervisor --> ChartAgent[Chart Agent: Matplotlib Candlestick]
        Supervisor --> PWAgent[PortfolioWatch Agent: P&L, NAV, Watchlist]
    end

    PriceAgent --> EvalAgent[4. Eval Agent: Rủi ro & Bất thường]
    NewsAgent --> EvalAgent
    IndicatorEngine --> EvalAgent

    PriceAgent --> Composer
    NewsAgent --> Composer
    EvalAgent --> Composer
    ChartAgent --> Composer
    PWAgent --> Composer

    subgraph Storage Systems
        DB1[(portfolio_watch.db)]
        DB2[(backend_store.db)]
        Cache1[(2-Tier Cache Engine)]
        ChartStore[MinIO bucket charts]
    end

    PWAgent <--> DB1
    PWAgent <--> DB2
    PriceAgent <--> Cache1
    ChartAgent --> ChartStore

    Composer --> SSEStream[5. SSE Streaming Output: Markdown + Chart + P&L Table]
    Refusal --> SSEStream
```

---

## 4. Kê Khai Toàn Diện Hệ Thống Lưu Trữ & Cơ Sở Dữ Liệu (Storage Inventory)

Hệ thống sử dụng kiến trúc lưu trữ phân tầng nhằm bảo đảm tốc độ truy xuất, cô lập dữ liệu người dùng và lưu vết phục vụ LLMOps:

| Hệ Thống Lưu Trữ | Vị Trí Lưu Trữ | Tên Bảng / Mục Đích | Chi Tiết Cấu Trúc & Dữ Liệu |
| :--- | :--- | :--- | :--- |
| **SQLite 1: Core AI DB** | `resources/data/portfolio_watch.db` | `sessions` | Quản lý phiên hội thoại (`session_id`, `user_id`, `created_at`, `updated_at`). |
| | | `messages` | Lịch sử chat ngắn hạn phục vụ Sliding Window và kiểm soát độ tươi (TTL 60 phút). |
| | | `portfolio_holdings` | Danh mục cổ phiếu nắm giữ của từng user (`user_id`, `ticker`, `shares`, `buy_price`, `buy_date`). |
| | | `user_settings` | Cấu hình cá nhân hóa người dùng (`user_id`, `risk_profile`, `alert_threshold_pct`). |
| | | `market_history_10d` | Bộ nhớ đệm lịch sử giá 10 ngày từ Vnstock phục vụ tính SMA/RSI khi offline. |
| | | `hitl_evaluations` | Nhật ký phản hồi Human-in-the-loop (Like/Dislike, đánh giá người dùng). |
| **SQLite 2: Product DB** | `resources/data/backend_store.db` | `watchlist` | Danh sách mã theo dõi trực tiếp từ Web UI (`user_id`, `ticker`, `alert_threshold_pct`, `created_at`). |
| | | `conversations` | Lưu vết toàn bộ hội thoại người dùng đồng bộ với Web UI. |
| | | `alert_events` | Lịch sử cảnh báo biến động giá cổ phiếu vượt ngưỡng thiết lập. |
| **Bộ Nhớ Đệm Cache 2 Tầng** | Exact cache mặc định memory. Redis khi `cache.backend` là `redis` | `Exact Cache (Tầng 1)` | Lưu cặp `Hash MD5(Prompt) -> Response`, TTL 24h, trúng cache tức thì (< 1ms). |
| | | `Semantic Cache (Tầng 2)` | Vector embedding cosine similarity $\ge 0.93$, xử lý câu hỏi gần tương đương (near-duplicates). |
| **Ảnh biểu đồ** | Bucket MinIO `charts`. Fallback `resources/data/charts/` khi MinIO không chạy | Tệp PNG nến kỹ thuật | `ChartAgent` upload `chart_*.png`. Chat vẫn nhúng `/charts/{tên file}`. App đọc object rồi trả `image/png`. |

---

## 5. Danh Mục Tính Năng Nghiệp Vụ (Feature Inventory)

| STT | Tên Tính Năng | Mô Tả Nghiệp Vụ Chi Tiết | Phân Hệ Phụ Trách |
| :---: | :--- | :--- | :--- |
| **1** | **Greeting Fast-Path** | Phản hồi câu chào hỏi ("Xin chào", "Hello") tức thì (< 1.0s), hướng dẫn các tính năng chính và gợi ý câu hỏi mẫu. | `InputGuardrail`, `AnswerComposer` |
| **2** | **Tường Lửa Guardrail** | Chặn 100% tấn công Prompt Injection; từ chối câu hỏi ngoài phạm vi chứng khoán Việt Nam; bắt buộc gắn cảnh báo rủi ro khi xin tư vấn. | `InputGuardrail`, `OutputGuardrail` |
| **3** | **Tra Cứu Giá Thị Trường** | Cung cấp giá khớp lệnh, % biến động, trần/sàn, lịch sử 10-30 phiên từ Vnstock, có fallback offline mẫu. | `PriceAgent`, `VnstockPriceSource` |
| **4** | **Tổng Hợp Tin Tức Doanh Nghiệp** | Thu thập và tóm tắt tin tức nóng từ Vnstock News & CafeF, trích dẫn nguồn tin uy tín minh bạch. | `NewsAgent`, `CafefNewsSource` |
| **5** | **Tính Toán Chỉ Báo Kỹ Thuật** | Tính toán định lượng RSI(14) (quá mua >70, quá bán <30), SMA(20), SMA(50), nhận diện Golden/Death Cross. | `TechnicalIndicatorService` |
| **6** | **So Sánh Cổ Phiếu Đa Mã** | Phân rã câu hỏi so sánh thành các sub-queries độc lập và đối chiếu thị giá, biến động của 2 mã trong bảng Markdown. | `RewriteBrain`, `SupervisorBrain` |
| **7** | **Vẽ Biểu Đồ Nến Kỹ Thuật** | Tự động sinh ảnh biểu đồ nến Candlestick kết hợp SMA bằng Matplotlib, nhúng URL ảnh tĩnh vào câu trả lời Markdown. | `ChartAgent` |
| **8** | **Quản Lý Danh Mục P&L & NAV** | Tính toán chi phí vốn, thị giá hiện tại, Unrealized P&L (VND & %) và tổng NAV độc lập theo `user_id`. | `PortfolioWatchAgent`, `PortfolioService` |
| **9** | **Danh Sách Theo Dõi & Cảnh Báo** | Truy xuất và quản lý danh sách mã theo dõi (Watchlist) kèm ngưỡng cảnh báo biến động (`alert_threshold_pct`). | `PortfolioWatchAgent`, `WatchlistStore` |
| **10**| **Miễn Trừ Trách Nhiệm Bắt Buộc** | Từ chối đưa ra lời khuyên đầu tư trực tiếp, bắt buộc chứa cụm từ *"miễn trừ trách nhiệm"*, không chứa *"nên mua/bán"*. | `OutputGuardrail`, `AnswerComposer` |
| **11**| **Live Agent Graph & Trực Quan Hóa**| Đồ thị mạng lưới trực quan hóa trạng thái từng Agent theo thời gian thực trên Web UI (sáng đèn khi xử lý, hover xem I/O). | `Web UI Frontend` |
| **12**| **Bộ Nhớ Ngắn Hạn & Độ Tươi** | Lưu trữ sliding window 20 tin nhắn gần nhất; tự động hết hạn sau 60 phút không tương tác (TTL Eviction). | `MemoryManager`, `SessionRepository` |
| **13**| **Bộ Nhớ Đệm Cache 2 Tầng** | Tiết kiệm 30.0% chi phí gọi LLM và giảm độ trễ trả lời qua bộ nhớ đệm Exact MD5 + Semantic Cosine $\ge 0.93$. | `ExactCache`, `SemanticCache` |
| **14**| **Đo Lường Token & Chi Phí** | Tính toán chính xác số lượng token prompt/completion và chi phí tương ứng (USD và VNĐ) cho từng lượt phản hồi. | `TokenTracker`, `CostTracker` |
| **15**| **Đánh Giá Kiểm Chuẩn Golden v6** | Đánh giá tự động 20 ca kiểm chuẩn bao phủ 10 lát cắt chức năng, chặn suy giảm chất lượng qua cổng kiểm thử Eval Gate. | `EvalGate`, `GoldenRunner` |

---

## 6. Cấu Trúc Thư Mục Chuẩn Sạch (Repository Layout)

```
vn-stock-swarm/
├── resources/                  # Tài nguyên tĩnh tổng hợp (Master Assets)
│   ├── configs/
│   │   └── config.yaml         # Master Application Config (LLM, App, Cache, Storage)
│   ├── data/                   # CSDL SQLite & PNG charts
│   ├── docs/                   # Sơ đồ kiến trúc & Concepts markdown
│   ├── eval/                   # Dữ liệu đánh giá Golden v6 & Báo cáo Excel
│   └── prompts/                # Prompt Registry tập trung (alias production)
├── specs/                      # Toàn bộ hồ sơ Spec-Driven Development (SDD)
│   ├── product-spec.md         # Đặc tả yêu cầu sản phẩm & kiến trúc
│   ├── implementation-plan.md  # Kế hoạch triển khai 6 Phase chi tiết
│   ├── test-plan.md            # Kế hoạch kiểm thử kim tự tháp 4 tầng
│   ├── change-log.md           # Nhật ký thay đổi & mốc phát triển
│   └── project-summary.md      # Tài liệu tổng hợp bảo vệ đồ án cuối khóa
├── src/
│   ├── common/                                      # [KHỐI 1: SHARED KERNEL - DÙNG CHUNG]
│   │   ├── base/                                    # Kế thừa chuẩn từ AI_Face_checkin
│   │   │   ├── base_model.py                        # CustomBaseModel (arbitrary_types_allowed = True)
│   │   │   └── base_service.py                      # BaseService, AsyncBaseService (process(input) -> output)
│   │   ├── domain/                                  # Nghiệp vụ toán học & thực thể cốt lõi
│   │   │   ├── entities.py                          # User, Holding, Watchlist, Message, StockQuote
│   │   │   ├── indicators.py                        # Toán học thuần túy: RSI(14), SMA(20, 50), Cross
│   │   │   └── ports.py                             # Giao diện trừu tượng IPriceSource, INewsSource, IDatabase
│   │   ├── logging/                                 # Hệ thống log & Correlation ID
│   │   │   └── logger.py                            # Structured logger (Console / JSON)
│   │   ├── settings/
│   │   │   ├── config.py                            # Nạp resources/configs/config.yaml & Environment
│   │   │   └── secrets.py                           # Secret Manager (DATABASE_URL, API Keys)
│   │   ├── transport/                               # HTTP client liên dịch vụ
│   │   │   ├── transport.py                         # Remote SSE streamer, retry backoff
│   │   │   └── schemas.py                           # DTO chuẩn trao đổi qua mạng (/v1/chat, /v1/scan)
│   │   └── tests/                                   # [TEST CỦA KHỐI COMMON]
│   │       ├── test_indicators.py                   # Test chỉ báo kỹ thuật RSI/SMA
│   │       ├── test_config.py                       # Test nạp config tập trung
│   │       └── test_secret_manager.py               # Test trích xuất secret an toàn
│   │
│   ├── web_backend/                                 # [KHỐI 2: MICROSERVICE WEB - CỔNG 8000]
│   │   ├── Dockerfile                               # Build container riêng
│   │   ├── main.py                                  # Entrypoint: CORS, Middleware, Include routers
│   │   ├── api/
│   │   │   ├── helpers/                             # Exception handler, middlewares, validation
│   │   │   ├── models/                              # Pydantic schemas cho API Web
│   │   │   └── routers/                             # chat, portfolio, watchlist, sessions, hitl...
│   │   ├── application/                             # Use Cases kế thừa BaseService
│   │   │   ├── chat_gateway_service.py              # SSE Gateway sang AI Backend
│   │   │   ├── portfolio_service.py                 # Tính toán P&L, NAV, lãi lỗ
│   │   │   ├── hitl_service.py                      # Ghi nhận đánh giá người dùng
│   │   │   ├── market_service.py                    # Dữ liệu thị trường cho Web
│   │   │   └── review_approval_service.py           # Quản lý hàng đợi duyệt lệnh HITL
│   │   ├── domain/                                  # session_validator, portfolio_calculator
│   │   ├── infra/                                   # database (PostgreSQL/SQLite), repositories, remote_ai_client
│   │   ├── shared/                                  # settings, exceptions
│   │   └── tests/                                   # [TEST CỦA MICROSERVICE WEB]
│   │       ├── test_chat_ui.py, test_feedback_signals.py, test_portfolio_service.py
│   │       └── test_database.py, test_api.py, test_market.py, test_web_ui_integration.py
│   │
│   ├── ai_backend/                                  # [KHỐI 3: MICROSERVICE AI - CỔNG 8001]
│   │   ├── Dockerfile                               # Build container riêng cho AI engine
│   │   ├── main.py                                  # Entrypoint: Chỉ nghe /health, /v1/chat/stream, /v1/scan
│   │   ├── api/                                     # helpers, models (stream, scan), routers (chat_stream, scan, health)
│   │   ├── application/                             # swarm_orchestrator, concept_rag_service, scanner, eval/
│   │   ├── domain/                                  # guardrails (input, output, greeting_fastpath)
│   │   ├── infra/                                   # graph (LangGraph Swarm), agents (10 nodes), market_data, qdrant, llm, cache, storage, cost, monitoring
│   │   ├── shared/                                  # settings, charts styling, exceptions
│   │   └── tests/                                   # [TEST CỦA MICROSERVICE AI]
│   │       ├── test_greeting_fastpath.py, test_guardrails.py, test_concept_rag.py, test_ai_http_stream.py...
│   │       └── test_agents.py, test_portfolio_watch_agent.py, test_chart.py, test_monitoring.py...
│   │
│   ├── frontend/                                    # Giao diện Web App (HTML5, Vanilla CSS, SSE JS)
│   └── deploy/                                      # Dockerfile, Docker Compose, Nginx conf, release.ps1, publish.ps1
├── tests/                                           # [KIỂM THỬ LIÊN DỊCH VỤ (E2E) & DOCKER]
│   ├── conftest.py                                  # Fixtures dùng chung toàn hệ thống
│   └── e2e/                                         # test_golden_v6_slices.py, test_eval.py, test_system.py, test_capstone.py...
├── scripts/                                         # Scripts vận hành chính thức (Benchmark, Cost, Eval)
├── .env                                             # Chứa duy nhất các Secrets (API Keys)
├── pyproject.toml                                   # Quản lý dependencies & metadata
└── README.md                                        # Tài liệu hướng dẫn sản phẩm
```

---

## 7. Hướng Dẫn Cài Đặt & Vận Hành Nhanh

### 7.1. Cài Đặt Môi Trường Cục Bộ (Native Python)
```bash
# 1. Kích hoạt môi trường Python (>= 3.10)
conda activate dong312

# 2. Cài đặt các thư viện cần thiết
pip install -e .

# 3. Tạo .env và điền secret. Tên biến nằm trong .env.example:
#    DATABASE_URL, OPENAI_API_KEYS, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, QDRANT_API_KEY
#    Tham số (model, cache, cổng, bộ nhớ, monitoring) sửa ở resources/configs/config.yaml

# 4. Khởi chạy hai microservices trên hai tiến trình độc lập:
# Cửa sổ 1 — Web Backend (cổng 8000, giao diện web & API người dùng):
uvicorn web_backend.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload

# Cửa sổ 2 — AI Backend (cổng 8001, xử lý Swarm và RAG khái niệm):
uvicorn ai_backend.main:app --app-dir src --host 127.0.0.1 --port 8001 --reload

# Truy cập giao diện tại: http://localhost:8000 (hoặc http://127.0.0.1:8000)
# Kiểm tra sức khỏe AI Backend tại: http://127.0.0.1:8001/health
```

Secret cần điền trong `.env` (mẫu tên biến ở `.env.example`):

- `DATABASE_URL`: chuỗi nối PostgreSQL. Mẫu `postgresql://portfolio:portfolio@localhost:5432/portfolio_watch`. App đọc biến này, không ghép host từ file yaml.
- `OPENAI_API_KEYS`: bắt buộc để gọi model. Nhiều key cách nhau bằng dấu phẩy.
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`: tùy chọn, để ghi trace.
- `QDRANT_API_KEY`: tùy chọn.

Tham số còn lại nằm ở `resources/configs/config.yaml`: model, cache, cổng, bộ nhớ, monitoring, embedding, host/cổng/tên database (`storage.postgres_host`, `storage.postgres_port`, `storage.postgres_db`), collection khái niệm (`storage.concept_collection`), collection bộ nhớ dài hạn (`memory.qdrant_collection`). Sửa tham số ở file đó. Nếu cùng một giá trị có trong cả `.env` và `config.yaml`, `.env` ghi đè. Compose ghi đè `DATABASE_URL` trong container thành host `postgres` cổng 5432.

### 7.2. Hai image, Postgres, và Qdrant bằng Docker Compose

`docker compose` chạy hai image app. Mỗi image một Dockerfile. Postgres và Qdrant mỗi cái một container, không nằm trong image web hay AI.

| Image | Dockerfile | Service | Cổng | Process |
| :--- | :--- | :--- | :--- | :--- |
| `portfolio-watch:web` | `src/web_backend/Dockerfile` | `backend` | 8000 | `uvicorn web_backend.main:app` |
| `portfolio-watch:ai` | `src/ai_backend/Dockerfile` | `ai` | 8001 | `uvicorn ai_backend.app:app` |

Postgres là service `postgres`, image `postgres:16-alpine`, cổng host 5432. Qdrant là service `qdrant`, image `qdrant/qdrant`, cổng host 6333 và 6334.

Cần có file `.env` trước khi compose chạy, vì service `backend` và `ai` đọc `env_file: .env`. Chưa có thì sao từ `.env.example`.

```bash
docker compose build
docker compose up -d postgres qdrant backend ai
```

Service `backend` còn kéo `redis` và `minio` vì compose khai báo phụ thuộc hai service đó. Trong compose, web gọi AI tại `http://ai:8001`. Mở giao diện tại http://localhost:8000. Health của AI: http://localhost:8001/health.

Frontend Docker, cổng 3001, chạy sau khi backend khỏe:

```bash
docker compose up -d frontend
```

http://localhost:3001 phục vụ trang tĩnh và trỏ về backend cổng 8000.

### 7.3. Vận Hành Và Phát Hành Bằng `src/deploy/release.ps1` Trên Windows (PowerShell)

Dự án cung cấp script `src/deploy/release.ps1` để quản lý toàn bộ vòng đời phát hành và triển khai cục bộ trên Windows mà không gọi `gcloud` và không dùng `systemd` / `systemctl`:

```powershell
# 1. Khởi chạy toàn bộ hệ thống (tự tạo .env nếu thiếu, lưu git SHA LKG, chạy containers, kiểm tra trạng thái):
powershell -ExecutionPolicy Bypass -File src/deploy/release.ps1 up

# 2. Kiểm tra trạng thái containers và endpoint sức khỏe (Web 8000 & AI 8001):
powershell -ExecutionPolicy Bypass -File src/deploy/release.ps1 status

# 3. Chạy kiểm thử khói tự động (Smoke test qua src/deploy/smoke.py):
powershell -ExecutionPolicy Bypass -File src/deploy/release.ps1 smoke -Url "http://127.0.0.1:8000" -Stream

# 4. Hoàn nguyên nhanh khi gặp sự cố (rollback prompt alias về LKG, force-recreate containers và chạy lại smoke test):
powershell -ExecutionPolicy Bypass -File src/deploy/release.ps1 rollback
```

### 7.4. Thực Thi Bộ Kiểm Thử 4 Tầng
```bash
# 1. Chạy toàn bộ 4 tầng kiểm thử của hệ thống
pytest src/ tests/ -v

# 2. Chạy nhanh tầng Common Kernel (< 1s)
pytest src/common/tests/ -v

# 3. Chạy tầng Web Backend Microservice
pytest src/web_backend/tests/ -v

# 4. Chạy tầng AI Backend Microservice
pytest src/ai_backend/tests/ -v

# 5. Chạy tầng E2E & Golden Dataset v6 (20/20 test cases)
pytest tests/e2e/test_golden_v6_slices.py -v
```

### 7.5. Exact cache: mặc định memory, cách bật Redis

Exact cache mặc định là **memory**. `resources/configs/config.yaml` có `cache.backend: "memory"`. App dùng bộ nhớ trong tiến trình, không cần Redis và không cần gói `redis`.

Bật Redis cho exact cache:

```bash
pip install redis
docker compose up -d redis
```

Trong `resources/configs/config.yaml`, đổi `cache.backend` thành `redis`, rồi khởi động lại app. `get_exact_cache()` giữ store của lần gọi đầu, nên đổi config khi app đang chạy thì chưa ăn.

- Máy host: `REDIS_URL` mặc định là `redis://localhost:6379`. Nếu cổng 6379 đã bị chiếm, chạy `REDIS_PORT=6380 docker compose up -d redis` và đặt `REDIS_URL=redis://localhost:6380`.
- Docker Compose: backend đã có `REDIS_URL=redis://redis:6379`. Vẫn phải đổi `cache.backend` thành `redis`. File `resources/` được mount vào container.

Semantic cache không đi qua Redis.

### 7.6. Ảnh biểu đồ trên MinIO

`storage.chart_backend` trong `resources/configs/config.yaml` mặc định là `minio`. Bucket là `charts`. URL trong chat vẫn là `/charts/chart_....png`. App đọc object và trả ảnh. Không dùng presigned URL.

```bash
docker compose up -d minio
```

- Máy host: endpoint trong config là `localhost:9000`. Access key và secret key nằm trong `.env` (`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`). Console: `http://localhost:9001`. Nếu cổng 9000 đã bị chiếm, chạy `MINIO_PORT=9100 MINIO_CONSOLE_PORT=9101 docker compose up -d minio` và sửa `storage.minio_endpoint` thành `localhost:9100`.
- Docker Compose: backend dùng `MINIO_ENDPOINT=minio:9000`.

Nếu MinIO không kết nối được, PNG ghi vào `storage.chart_dir` (`resources/data/charts/` trên máy host, `/app/data/charts` trong container). Đổi `chart_backend` thành `local` rồi khởi động lại app nếu không dùng MinIO.

### 7.7. Nạp năm file khái niệm vào Qdrant

Năm file nằm trong `resources/docs/concepts/`: `gia-tran-san.md`, `lenh-ato-atc-lo.md`, `rsi-va-sma.md`, `nav-va-lai-lo-chua-chot.md`, `mien-tru-trach-nhiem.md`.

Qdrant phải đang chạy (`docker compose up -d qdrant` ở mục 7.2). Từ thư mục gốc dự án:

```bash
PYTHONPATH=src python -c "from qdrant_client import QdrantClient; from ai_backend.retrieval.concepts import index_concepts; print(index_concepts(client=QdrantClient(url='http://localhost:6333', timeout=10, check_compatibility=False)))"
```

Lệnh này cắt từng file theo đoạn văn, embed offline (không gọi OpenAI), xóa collection cũ rồi ghi lại. Tên collection lấy từ `storage.concept_collection` trong `config.yaml`, mặc định `stock_concepts`. Collection đó phải khác `memory.qdrant_collection` (`portfolio_watch_memory`). Số in ra là số đoạn đã ghi.

---

## 8. Hướng Dẫn Trình Bày Bảo Vệ Đồ Án Cuối Khóa (Capstone Presentation)
Vui lòng tham khảo chi tiết tài liệu [specs/project-summary.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/project-summary.md) để xem:
- Kịch bản demo 5 phút theo từng bước bấm trên màn hình.
- Danh mục câu hỏi phản biện thường gặp của Hội đồng và câu trả lời mẫu.
- Số liệu đo lường định lượng tiết kiệm chi phí và tỷ lệ cache hit.
