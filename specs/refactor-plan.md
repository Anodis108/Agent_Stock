# Kế Hoạch Refactor `src/backend` — Clean Architecture

> **Phương pháp**: Spec-Driven Development (SDD) & Test-Driven Refactoring  
> **Nguyên tắc cốt lõi**: Làm từng ô checklist một. Sau mỗi phase chạy test kiểm tra màu xanh (PASS) mới chuyển sang phase kế tiếp. Không làm vỡ bất kỳ test nào hiện có.

---

## 1. Mục Tiêu & Tiêu Chí Nghiệm Thu (Acceptance Criteria)

1. **Chuẩn hóa kiến trúc Clean Architecture**:
   - `domain/`: Nghiệp vụ cốt lõi, thuần Python, không phụ thuộc thư viện ngoài (FastAPI, SQLAlchemy, LangGraph...).
   - `application/`: Các ca sử dụng (Use Cases), Swarm Agents, StateGraph và Interfaces/Protocols.
   - `infrastructure/`: Hiện thực hóa DB, Qdrant Vector, MinIO, LLM, Vnstock Client.
   - `presentation/`: Các endpoint API FastAPI, SSE Streaming, CLI runners.
   - `main.py`: Composition Root duy nhất chịu trách nhiệm Dependency Injection (DI).
2. **Bảo toàn 100% chức năng & Test Pyramid**:
   - `pytest tests/unit/`: Pass 100% (< 10 giây, offline).
   - `pytest tests/integration/`: Pass 100%.
   - `pytest tests/e2e/`: Pass 100% (gồm cả Golden Dataset v6 và Gate Drill).
3. **Không phá vỡ Docker & Deploy**:
   - Toàn bộ 7 Docker containers trong `docker-compose.yml` khởi động bình thường.

---

## 2. Kiến Trúc Mục Tiêu (Target Folder Structure)

```text
src/backend/
├── domain/                         # [LỚP 1: LÕI NGHIỆP VỤ - THUẦN PYTHON]
│   ├── entities/                   # StockQuote, WatchlistItem, PortfolioHolding, ChatSession, User...
│   ├── value_objects/              # Ticker, PriceChange, Signal, IndicatorResult...
│   ├── indicators.py               # Công thức toán học RSI(14), SMA(20, 50), Golden/Death Cross
│   └── guardrails/                 # Regex & quy tắc nhận diện Prompt Injection, Out-of-Scope
│
├── application/                    # [LỚP 2: ĐIỀU PHỐI & USE CASES]
│   ├── use_cases/                  # answer_question.py, scan_market.py, review_portfolio.py, record_hitl.py
│   ├── interfaces/                 # Protocols/Ports: IPriceSource, INewsSource, IVectorStore, IDatabase
│   ├── dto/                        # Schemas truyền nhận nội bộ Use Case (Pydantic / dataclasses)
│   ├── graph/                      # LangGraph StateGraph (Router -> Supervisor -> Workers -> Composer)
│   └── agents/                     # Các Worker Nodes: PriceAgent, NewsAgent, ChartAgent, PortfolioAgent...
│
├── infrastructure/                 # [LỚP 3: ADAPTERS & CÔNG NGHỆ BÊN NGOÀI]
│   ├── database/                   # Postgres Connection, Pool, Repositories (Session, Portfolio, Watchlist)
│   ├── llm/                        # OpenAI Client, Token & Cost Tracker, Prompt Loaders
│   ├── retrieval/                  # Qdrant Client, Concept Retriever (RAG 5 file markdown)
│   ├── market_data/                # Vnstock Client kèm Offline Fallback & 2-tier Cache (Memory/Redis)
│   ├── storage/                    # MinIO Object Storage, Lưu biểu đồ nến Matplotlib
│   └── config/                     # Nạp cấu hình từ resources/configs/config.yaml & Secret Manager
│
├── presentation/                   # [LỚP 4: CỔNG GIAO TIẾP VÀO]
│   ├── api/                        # FastAPI Router: /chat (SSE), /portfolio, /watchlist, /sessions, /hitl
│   └── cli/                        # Các lệnh runner: gate.py, run_detailed.py, noise_calibration.py
│
├── main.py                         # [COMPOSITION ROOT: Ráp nối toàn bộ dependency]
└── tests/                          # [BỘ KIỂM THỬ 3 TẦNG BẢO TOÀN LOGIC]
```

---

## 3. Lộ Trình Triển Khai Từng Bước (Checklist)

### Phase 0: Thiết Lập Baseline Kiểm Thử (Safety Net)
- [ ] Chạy toàn bộ test hiện có để lưu giữ baseline xanh trước khi refactor.  
  *Lệnh kiểm:* `pytest tests/unit/ tests/integration/ tests/e2e/test_capstone.py -q`

---

### Phase 1: Chuẩn Hóa Tầng Domain (Domain Layer)
- [ ] Gom toàn bộ toán chỉ báo (`indicators.py`) và quy tắc an toàn (`guardrails/`) vào `src/backend/domain/`.
- [ ] Định nghĩa các Entities chuẩn bằng dataclasses/Pydantic trong `src/backend/domain/entities/`: `StockQuote`, `Holding`, `Watchlist`, `Message`.
- [ ] Đảm bảo tầng Domain không `import` bất kỳ module nào từ `infrastructure`, `presentation` hay `application`.  
  *Lệnh kiểm:* `pytest tests/unit/test_indicators.py tests/unit/test_guardrails.py -q`

---

### Phase 2: Chuẩn Hóa Tầng Use Cases & Interfaces (Application Layer)
- [ ] Định nghĩa các giao diện trừu tượng (`typing.Protocol`) tại `src/backend/application/interfaces/`:
  - `IPriceSource`: Lấy OHLCV và giá realtime.
  - `INewsSource`: Lấy tin tức cổ phiếu.
  - `IVectorStore`: Tìm kiếm đoạn văn bản khái niệm.
  - `IDatabase`: Lưu trữ session, holding, watchlist.
- [ ] Chuẩn hóa các Use Cases tại `src/backend/application/use_cases/`:
  - `AnswerQuestionUseCase`: Điều phối StateGraph hội thoại và stream token.
  - `PortfolioUseCase`: Tính toán P&L và tổng hợp NAV.
  - `HitlFeedbackUseCase`: Ghi nhận đánh giá Thích / Không thích của người dùng.
- [ ] Giữ nguyên các Agent chuyên trách (`src/backend/application/agents/`) đóng vai trò là worker nodes trong LangGraph.  
  *Lệnh kiểm:* `pytest tests/unit/test_portfolio_service.py tests/unit/test_feedback_signals.py tests/unit/test_concept_rag.py -q`

---

### Phase 3: Chuẩn Hóa Tầng Hạ Tầng (Infrastructure Layer)
- [ ] Gom các cài đặt cụ thể vào `src/backend/infrastructure/`:
  - `database/`: Repository Postgres (và SQLite fallback test).
  - `market_data/`: `VnstockPriceSource` hiện thực hóa `IPriceSource`.
  - `retrieval/`: `QdrantRetriever` hiện thực hóa `IVectorStore`.
  - `llm/`: OpenAI client bọc trong `ILLMClient`.
- [ ] Kiểm tra nguyên lý đảo ngược phụ thuộc (DIP): Tầng Infra chỉ phụ thuộc vào Interface của Application, không có chiều ngược lại.  
  *Lệnh kiểm:* `pytest tests/integration/test_database.py tests/integration/test_agents.py -q`

---

### Phase 4: Chuẩn Hóa Tầng Presentation & Composition Root
- [ ] Đưa các routers FastAPI vào `src/backend/presentation/api/`:
  - `chat_router.py`: Endpoint `/chat` và `/chat/stream` (SSE).
  - `portfolio_router.py`: Endpoint `/portfolio/holdings` và `/watchlist`.
  - `hitl_router.py`: Endpoint `/hitl/feedback`.
- [ ] Tinh gọn `src/backend/main.py`: Đóng vai trò Composition Root, thực hiện nạp config $\rightarrow$ khởi tạo kết nối DB/Qdrant $\rightarrow$ inject vào use case $\rightarrow$ gán router.  
  *Lệnh kiểm:* `pytest tests/integration/test_api.py tests/unit/test_ai_http_stream.py -q`

---

### Phase 5: Hợp Nhất & Kiểm Thử Toàn Diện (End-to-End Verification)
- [ ] Chạy toàn bộ kiểm thử Unit Test.
- [ ] Chạy toàn bộ kiểm thử Integration Test.
- [ ] Chạy kiểm thử E2E (Golden Dataset v6 20/20 cases).
- [ ] Kiểm tra Docker Compose khởi chạy đầy đủ 7 container với codebase mới.  
  *Lệnh kiểm:* `pytest tests/ -q` và `docker compose up -d`

---

## 4. Chiến Lược Giảm Thiểu Rủi Ro (Risk Mitigation)

1. **Cơ chế Shims / Aliases tạm thời**:
   Trong quá trình di chuyển các file, giữ lại file shim ngắn ở vị trí cũ (ví dụ `src/backend/application/portfolio_service.py` trỏ tới `src/backend/application/use_cases/portfolio_service.py`) để các file test cũ không bị gãy `ImportError`.
2. **Không sửa đổi logic nghiệp vụ trong khi refactor cấu trúc**:
   Tách biệt 2 việc: (1) Di chuyển và tổ chức lại file; (2) Tối ưu thuật toán. Ở đợt refactor này, chỉ tập trung vào việc tổ chức lại kiến trúc, giữ nguyên 100% logic bên trong hàm.
3. **Rollback an toàn qua Git**:
   Mỗi Phase hoàn thành sẽ được commit riêng biệt trên git để có thể rollback về bất kỳ mốc an toàn nào nếu phát sinh lỗi.
