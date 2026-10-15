# Implementation Plan — VN Stock Swarm Refactoring

Kế hoạch tái cấu trúc hệ thống theo phương pháp **Spec-Driven Development (SDD)**, chuyển đổi `src/backend` thành 3 khối kiến trúc chuẩn Clean Architecture (kế thừa từ `AI_Face_checkin`):
- **Khối 1: `src/common`** (Shared Kernel dùng chung)
- **Khối 2: `src/web_backend`** (Microservice Web - Cổng 8000)
- **Khối 3: `src/ai_backend`** (Microservice AI Swarm - Cổng 8001)
- **Khối 4: `tests/e2e`** (Kiểm thử liên dịch vụ, Golden v6, Docker, Capstone)

> **Nguyên tắc SDD**:
> - Thực hiện tuần tự từng phase. Chỉ chuyển sang phase tiếp theo khi toàn bộ checkbox của phase hiện tại đã được tick.
> - Mỗi lần hoàn thành một ô checklist: tick `[x]`, ghi lại file đã thay đổi vào `specs/change-log.md`, và chạy lệnh test tương ứng.
> - Tuyệt đối không thêm thư viện ngoài `pyproject.toml`. Không làm vỡ bất kỳ test nào trong 20 ca kiểm chuẩn Golden v6.

---

## Phase 1: Shared Kernel — Xây Dựng Khối Dùng Chung (`src/common/`)

- [x] **1.1. Base Foundation**:
  - Tạo `src/common/base/base_model.py` (`CustomBaseModel` kế thừa Pydantic BaseModel, thiết lập `arbitrary_types_allowed = True`).
  - Tạo `src/common/base/base_service.py` (`BaseService` và `AsyncBaseService` với method trừu tượng `process(input: InputModel) -> OutputModel`).
  - Tạo `src/common/base/__init__.py`.
  - *Kiểm tra*: `python -c "from common.base.base_model import CustomBaseModel; from common.base.base_service import BaseService, AsyncBaseService"`
- [x] **1.2. Domain Models & Pure Math**:
  - Tạo `src/common/domain/entities.py` (chuyển các thực thể cốt lõi `User`, `Holding`, `Watchlist`, `Message`, `StockQuote`).
  - Tạo `src/common/domain/indicators.py` (công thức toán học thuần túy: RSI-14, SMA-20, SMA-50, Golden Cross, Death Cross).
  - Tạo `src/common/domain/ports.py` (các interface trừu tượng `IPriceSource`, `INewsSource`, `IDatabase`).
  - Tạo `src/common/domain/__init__.py`.
  - *Kiểm tra*: `python -c "from common.domain.indicators import calculate_rsi, calculate_sma"`
- [x] **1.3. Structured Logging & Context Correlation**:
  - Tạo `src/common/logging/logger.py` (logger có cấu trúc, gắn Correlation ID, hỗ trợ Console/JSON output).
  - Tạo `src/common/logging/__init__.py`.
  - *Kiểm tra*: `python -c "from common.logging.logger import get_logger; log = get_logger('test')"`
- [x] **1.4. Centralized Settings & Secrets**:
  - Tạo `src/common/settings/config.py` (nạp `resources/configs/config.yaml`, quản lý biến môi trường).
  - Tạo `src/common/settings/secrets.py` (Secret Manager đọc `DATABASE_URL`, API Keys từ `.env` với fallback an toàn).
  - Tạo `src/common/settings/__init__.py`.
  - *Kiểm tra*: `python -c "from common.settings.config import load_config; from common.settings.secrets import get_database_url"`
- [x] **1.5. Inter-Service Transport & DTO Schemas**:
  - Tạo `src/common/transport/schemas.py` (DTO chuẩn trao đổi qua mạng cho `/v1/chat`, `/v1/chat/stream`, `/v1/scan`).
  - Tạo `src/common/transport/transport.py` (HTTP client liên dịch vụ hỗ trợ SSE streaming, retry backoff, exponential delay).
  - Tạo `src/common/transport/__init__.py`.
  - *Kiểm tra*: `python -c "from common.transport.schemas import ChatStreamRequest; from common.transport.transport import stream_remote_sse"`
- [x] **1.6. Khối Test Cho Common**:
  - Di chuyển và cập nhật `tests/unit/test_indicators.py` -> `src/common/tests/test_indicators.py`.
  - Di chuyển và cập nhật `tests/unit/test_config.py` -> `src/common/tests/test_config.py`.
  - Di chuyển và cập nhật `tests/unit/test_secret_manager.py` -> `src/common/tests/test_secret_manager.py`.
  - *Kiểm tra*: `pytest src/common/tests/ -q`

---

## Phase 2: Web Backend Microservice — Cổng 8000 (`src/web_backend/`)

- [x] **2.1. Web Presentation Layer (`api/`)**:
  - `api/helpers/`: `exception_handler.py` (xử lý lỗi HTTP 4xx, 5xx), `middlewares.py` (Correlation ID, request logging), `validation.py` (kiểm tra đầu vào).
  - `api/models/`: Pydantic models cho Web API (`chat.py`, `portfolio.py`, `hitl.py`, `sessions.py`).
  - `api/routers/`: FastAPI routers (`chat.py`, `portfolio.py`, `watchlist.py`, `sessions.py`, `hitl.py`, `market.py`, `approvals.py`, `scan.py`).
  - *Kiểm tra*: `python -c "from web_backend.api.routers import chat, portfolio, sessions"`
- [x] **2.2. Web Application Layer (`application/`)**:
  - Triển khai các Use Cases kế thừa `BaseService`/`AsyncBaseService`:
    - `chat_gateway_service.py`: Tiếp nhận câu hỏi, điều phối context, gọi sang `ai_backend` qua HTTP, stream token ra UI.
    - `portfolio_service.py`: Quản lý danh mục, tính toán chi phí vốn, giá trị thị trường, NAV, Unrealized P&L.
    - `hitl_service.py`: Ghi nhận đánh giá người dùng (Thumbs Up/Down).
    - `market_service.py`: Tổng hợp thông tin thị trường cho Web.
    - `review_approval_service.py`: Quản lý hàng đợi duyệt lệnh HITL.
  - *Kiểm tra*: `python -c "from web_backend.application.chat_gateway_service import ChatGatewayService"`
- [x] **2.3. Web Domain Layer (`domain/`)**:
  - `session_validator.py`: Xác thực tính hợp lệ của session và user.
  - `portfolio_calculator.py`: Các công thức tài chính chuyên biệt cho danh mục đầu tư.
  - *Kiểm tra*: `python -c "from web_backend.domain.portfolio_calculator import PortfolioCalculator"`
- [x] **2.4. Web Infrastructure Layer (`infra/`)**:
  - `infra/database/`: `connection.py` (kết nối PostgreSQL, fallback SQLite cho test), `pg.py` (driver psycopg3).
  - `infra/database/repositories/`: `SessionRepo`, `MessageRepo`, `PortfolioRepo`, `WatchlistRepo`.
  - `infra/ai_client/`: `remote_ai_client.py` (Client gọi sang `ai_backend:8001`).
  - *Kiểm tra*: `python -c "from web_backend.infra.database.connection import get_connection"`
- [x] **2.5. Web Shared & Entrypoint**:
  - `shared/settings.py` (cấu hình Web: `PORT=8000`, `AI_BASE_URL`).
  - `shared/exceptions.py` (`WebDatabaseException`, `SessionNotFoundException`,...).
  - `main.py`: Entrypoint FastAPI của Web, cấu hình CORS, Middleware, phục vụ static frontend và route include.
  - `Dockerfile`: Multi-stage Dockerfile độc lập cho Web Backend.
  - *Kiểm tra*: `python -c "from web_backend.main import app"`
- [x] **2.6. Khối Test Cho Web Backend**:
  - Di chuyển và cập nhật các test liên quan tới Web:
    - `src/web_backend/tests/test_chat_ui.py`
    - `src/web_backend/tests/test_feedback_signals.py`
    - `src/web_backend/tests/test_portfolio_service.py`
    - `src/web_backend/tests/test_database.py`
    - `src/web_backend/tests/test_api.py`
    - `src/web_backend/tests/test_market.py`
    - `src/web_backend/tests/test_web_ui_integration.py`
  - *Kiểm tra*: `pytest src/web_backend/tests/ -q`

---

## Phase 3: AI Backend Microservice — Cổng 8001 (`src/ai_backend/`)

- [x] **3.1. AI Presentation Layer (`api/`)**:
  - `api/helpers/`: `exception_handler.py`, `middlewares.py`.
  - `api/models/`: `stream_models.py` (`NodeStart`, `NodeFinish`, `TokenEvent`, `CompleteEvent`), `scan_models.py`.
  - `api/routers/`: `chat_stream.py` (POST `/v1/chat/stream`), `scan.py` (POST `/v1/scan`), `health.py` (GET `/health`).
  - *Kiểm tra*: `python -c "from ai_backend.api.routers import chat_stream, health, scan"`
- [x] **3.2. AI Application Layer (`application/`)**:
  - `swarm_orchestrator.py`: Điểm điều phối LangGraph Swarm (thay thế use-case `answer_question.py`).
  - `concept_rag_service.py`: Tìm kiếm ngữ nghĩa tài liệu khái niệm trên Qdrant.
  - `symbol_scanner_service.py`: Quét phân tích kỹ thuật mã cổ phiếu.
  - `application/eval/`: Bộ công cụ đánh giá (`gate.py`, `history.py`, `regression.py`, `run.py`, `run_detailed.py`, `run_excel_export.py`, `agent_eval.py`, `eval_cache.py`).
  - *Kiểm tra*: `python -c "from ai_backend.application.swarm_orchestrator import SwarmOrchestrator"`
- [x] **3.3. AI Domain Layer (`domain/`)**:
  - `guardrails/input_guardrail.py`: Chặn 100% Prompt Injection, lọc câu hỏi Out-of-Scope.
  - `guardrails/output_checks.py`: Bắt buộc Disclaimer, định dạng bảng P&L.
  - `guardrails/greeting_fastpath.py`: Nhận diện câu chào hỏi để phản hồi tức thì (TTFT < 1s).
  - *Kiểm tra*: `python -c "from ai_backend.domain.guardrails.input_guardrail import InputGuardrail"`
- [x] **3.4. AI Infrastructure Layer (`infra/`)**:
  - `infra/graph/`: StateGraph điều phối LangGraph Swarm (`workflow.py`, `state.py`, `steps.py`).
  - `infra/agents/`: Toàn bộ 10 Agent Nodes (`supervisor_agent`, `price_agent`, `news_agent`, `eval_agent`, `chart_agent.py`, `diagram_agent`, `event_classifier`, `portfolio_watch_agent`, `synthesis_agent`, `answer_composer`).
  - `infra/market_data/`: `price_source.py` (Vnstock với offline fallback), `news_source.py` (CafeF / Vnstock).
  - `infra/qdrant/`: `concepts.py` (client nạp 5 file markdown), `answer.py` (semantic retrieval).
  - `infra/llm/`: `client.py`, `async_client.py`, `completion.py`, `structured.py`, `prompt_registry.py`, `prompt_lint.py`, `prompt_experiment.py`, `semaphore.py`, `resilience.py`, `account_snapshot.py`.
  - `infra/cache/`: `exact.py`, `semantic.py`, `redis_store.py`.
  - `infra/cost/`: `tracker.py`.
  - `infra/monitoring/`: `tracing.py` (Langfuse span & che mờ PII).
  - `infra/storage/`: `chart_store.py`, `memory_store.py`, `long_term_memory.py`, `price_history_store.py`, `watchlist_store.py`.
  - `infra/notify/`: `console_notifier.py`.
  - `infra/scheduler/`: `cron.py`.
  - *Kiểm tra*: `python -c "from ai_backend.infra.graph.workflow import build_swarm_graph"`
- [x] **3.5. AI Shared & Entrypoint**:
  - `shared/settings.py` (cấu hình AI: `PORT=8001`, Qdrant, Redis, OpenAI Keys).
  - `shared/charts.py` (Matplotlib styling chuẩn).
  - `shared/exceptions.py` (`GuardrailViolation`, `LLMTimeoutException`,...).
  - `main.py`: Entrypoint FastAPI của AI Backend, chỉ phục vụ `/health`, `/v1/chat/stream`, `/v1/scan`.
  - `Dockerfile`: Multi-stage Dockerfile độc lập cho AI Backend.
  - *Kiểm tra*: `python -c "from ai_backend.main import app"`
- [x] **3.6. Khối Test Cho AI Backend**:
  - Di chuyển và cập nhật các test liên quan tới AI:
    - `src/ai_backend/tests/test_greeting_fastpath.py`
    - `src/ai_backend/tests/test_guardrails.py`
    - `src/ai_backend/tests/test_output_guardrail_formatting.py`
    - `src/ai_backend/tests/test_concept_rag.py`
    - `src/ai_backend/tests/test_ai_http_stream.py`
    - `src/ai_backend/tests/test_async_client.py`
    - `src/ai_backend/tests/test_redis_store.py`
    - `src/ai_backend/tests/test_memory.py`
    - `src/ai_backend/tests/test_chart_store.py`
    - `src/ai_backend/tests/test_prompt_rollback.py`
    - `src/ai_backend/tests/test_agents.py`
    - `src/ai_backend/tests/test_portfolio_watch_agent.py`
    - `src/ai_backend/tests/test_chart.py`
    - `src/ai_backend/tests/test_monitoring.py`
    - `src/ai_backend/tests/test_module3_features.py`
    - `src/ai_backend/tests/test_edge_cases.py`
  - *Kiểm tra*: `pytest src/ai_backend/tests/ -q`

---

## Phase 4: Inter-Service Wiring & Cleanup

- [x] **4.1. Cập Nhật Cấu Hình Dự Án (`pyproject.toml`)**:
  - Cập nhật danh sách packages tìm kiếm trong `pyproject.toml`: `["common*", "web_backend*", "ai_backend*"]`.
  - Loại bỏ định nghĩa package `backend*`.
  - *Kiểm tra*: `pip install -e .`
- [x] **4.2. Xóa Bỏ Hoàn Toàn `src/backend/`**:
  - Xác nhận 100% logic đã được chuyển sang `src/common`, `src/web_backend`, hoặc `src/ai_backend`.
  - Xóa bỏ thư mục `src/backend/`.
  - *Kiểm tra*: `python -c "import os; assert not os.path.exists('src/backend')"`
- [x] **4.3. Kiểm Tra Ranh Giới Độc Lập**:
  - Đảm bảo `src/web_backend` không import bất kỳ module nào từ `src/ai_backend`.
  - Đảm bảo `src/web_backend` không import `openai` hay `langgraph`.
  - *Kiểm tra*: Chạy script kiểm tra AST import boundaries.

---

## Phase 5: Verification of 4-Tier Test Suites & Golden v6

- [x] **5.1. Chạy Test Suite Tầng 1 (Common)**:
  - *Kiểm tra*: `pytest src/common/tests/ -v`
- [x] **5.2. Chạy Test Suite Tầng 2 (Web Backend)**:
  - *Kiểm tra*: `pytest src/web_backend/tests/ -v`
- [x] **5.3. Chạy Test Suite Tầng 3 (AI Backend)**:
  - *Kiểm tra*: `pytest src/ai_backend/tests/ -v`
- [x] **5.4. Chạy Test Suite Tầng 4 (E2E & Capstone Gate)**:
  - Kiểm tra `tests/e2e/test_golden_v6_slices.py`: Đạt 20/20 test cases (100% PASS).
  - Kiểm tra `tests/e2e/test_eval.py`: Eval Gate PASS.
  - Kiểm tra `tests/e2e/test_system.py`: System integration PASS.
  - Kiểm tra `tests/e2e/test_capstone.py`: Capstone requirements PASS.
  - Kiểm tra `tests/e2e/test_demo_walkthrough.py`: Demo 10 bước PASS.
  - *Kiểm tra*: `pytest tests/e2e/ -v`

---

## Phase 6: Docker Compose, Nginx & Deployment Verification

- [x] **6.1. Docker Compose Configuration**:
  - Cập nhật `docker-compose.yml` sử dụng `src/web_backend/Dockerfile` cho service `backend` và `src/ai_backend/Dockerfile` cho service `ai_backend`.
  - Kiểm tra các volume mounts và biến môi trường (`AI_BASE_URL=http://ai_backend:8001`).
  - *Kiểm tra*: `pytest tests/e2e/test_docker_setup.py -q`
- [x] **6.2. Nginx & Deployment Scripts**:
  - Kiểm tra `src/deploy/nginx.conf`: Nghe port 80, proxy về `127.0.0.1:8000`, tắt buffering trên route stream.
  - Kiểm tra `src/deploy/release.ps1` (`up`, `smoke`, `rollback`, `status`).
  - Kiểm tra `src/deploy/publish.ps1` (Cloudflare Tunnel).
  - *Kiểm tra*: `pytest tests/integration/test_system.py -k "nginx or release or publish" -q`
