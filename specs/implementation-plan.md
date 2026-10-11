# Implementation Plan — VN Stock Swarm (Capstone Refactoring & Modular SDD)

Kế hoạch tái cấu trúc và chuẩn hóa toàn diện dự án theo phương pháp **Spec-Driven Development (SDD)**, chia thành các **Phase nhỏ, độc lập và có tiêu chí nghiệm thu rõ ràng**.

> **Quy tắc thực thi cốt lõi (Core Execution Rules)**:
> 1. Mỗi lần chỉ thực hiện duy nhất **01 phase hoặc 01 checklist item** được chỉ định.
> 2. **Chưa viết bất kỳ dòng mã nguồn nào khi chưa có sự xác nhận từ người dùng** (*"Do not write code yet"*).
> 3. Sau mỗi phase, luôn chạy lệnh kiểm thử xác minh và cập nhật trạng thái checklist kèm nhật ký tại [specs/change-log.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/change-log.md).

---

## Danh Sách Các Phase Triển Khai (Phase Overview)

- [x] **Phase 1: Chuẩn Hóa Cấu Hình Tập Trung (Config Decoupling — `config.yaml` & `.env`)** (Hoàn thành - 5/5 tests passed)
- [x] **Phase 2: Tinh Gọn & Làm Sạch Tài Nguyên (`resources/eval/` & `specs/`)** (Hoàn thành - 48/48 tests passed)
- [x] **Phase 3: Tinh Gọn Thư Mục Scripts Vận Hành (`scripts/`)** (Hoàn thành - dry-run & eval runner verified)
- [x] **Phase 4: Di Dời Thư Mục Triển Khai (`deploy/` -> `src/deploy/`)** (Hoàn thành - CI workflows & smoke tests passed)
- [x] **Phase 5: Module Hóa Mã Nguồn Backend (`src/backend/`)** (Hoàn thành - 49/49 tests passed)
- [ ] **Phase 6: Tái Cấu Trúc Bộ Kiểm Thử 3 Tầng (`tests/unit/`, `tests/integration/`, `tests/e2e/`)**
- [ ] **Phase 7: Kiểm Thử Toàn Diện, Đo Lường Tốc Độ CI & Nghiệm Thu Đồ Án**

---

## Chi Tiết Từng Phase & Checklist Thực Thi

### Phase 1: Chuẩn Hóa Cấu Hình Tập Trung (Config Decoupling)
> **Mục tiêu**: Tách bạch tuyệt đối giữa **Bí mật (Secrets)** và **Cấu hình vận hành (Runtime Configs)**. File `.env` chỉ chứa API keys; toàn bộ tham số ứng dụng được quản lý tập trung tại [resources/configs/config.yaml](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/resources/configs/config.yaml).

- [x] **1.1. Soạn thảo tệp cấu hình `resources/configs/config.yaml` chuẩn mực**:
  - `app`: tên ứng dụng, host, port (8000), log_level (INFO), cors_origins.
  - `llm`: backend (`openai`/`ollama`/`vllm`), model (`gpt-4o-mini`), temperature (0.2), max_completion_tokens (800), top_p (1.0), max_retries (3), cascade_models, fallback_backends.
  - `cache`: exact_enabled (true), semantic_enabled (true), semantic_threshold (0.93), ttl_seconds (86400).
  - `memory`: short_term_window (20), short_term_ttl_minutes (60).
  - `storage`: sqlite_path (`resources/data/portfolio_watch.db`), backend_sqlite_path (`resources/data/backend_store.db`), chart_dir (`resources/data/charts`).
  - `market_data`: price_source (`vnstock`), news_source (`cafef`), fallback_on_error (true).
  - `eval`: golden_dataset_path (`resources/eval/golden_v6_comprehensive.yaml`), eval_cache_dir (`.eval_cache`), cost_daily_limit_usd (0.0).
  - `monitoring`: enabled (true), error_sample_rate (1.0), normal_sample_rate (0.05), pii_redaction (true).
- [x] **1.2. Tinh gọn `.env` và `.env.example`**:
  - Chỉ giữ lại các trường secrets: `OPENAI_API_KEYS`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `QDRANT_API_KEY`, `QDRANT_HOST`.
- [x] **1.3. Cập nhật module `Settings` nạp cấu hình**:
  - Đọc `config.yaml` làm giá trị gốc, nạp đè từ biến môi trường `.env` nếu có secrets.
- [x] **1.4. Viết Unit Test xác thực nạp cấu hình**:
  - Tạo `tests/test_config.py` kiểm tra nạp đúng các tham số từ YAML và override từ env.
- **Lệnh xác minh**: `pytest tests/test_config.py -v` (Đã PASS 5/5 tests trong 0.08s)

---

### Phase 2: Tinh Gọn & Làm Sạch Tài Nguyên (`resources/eval/` & `specs/`)
> **Mục tiêu**: Đưa toàn bộ dữ liệu đánh giá và artifact từ `specs/eval/` sang `resources/eval/`, chỉ giữ các bản tổng hợp final của product, làm sạch `specs/`.

- [x] **2.1. Di dời & Quy hoạch `resources/eval/`**:
  - Chuyển các file đánh giá quan trọng từ `specs/eval/` sang `resources/eval/`.
  - Giữ các tệp chuẩn final:
    - Dataset: `golden_v6_comprehensive.yaml` (20 câu 10 lát cắt), `replay_faq.yaml` (200 câu FAQ).
    - Baseline: `v6_baseline.json`, `v5_baseline.json`.
    - Báo cáo kết quả: `danh_gia_chi_tiet_golden_v5_v6.xlsx`, `cache_benchmark.json`, `cost_baseline.json`, `eval_summary_v6.json`, `eval_observations_v6.json`.
  - Xóa bỏ các thư mục nháp/tạm (`history/`, `runs/`, `*.log`, `baseline_debug.json`).
- [x] **2.2. Làm sạch thư mục `specs/`**:
  - Xóa thư mục `specs/eval/` sau khi đã đưa sang `resources/eval/`.
  - Xóa các file thừa: `specs/legacy-*`, `specs/agents.md` (đã có `AGENTS.md` tại gốc), `specs/mvp-status-report.md`, `specs/project_analysis.md`.
  - Giữ lại đúng 5 tệp đặc tả cốt lõi:
    - [specs/product-spec.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/product-spec.md)
    - [specs/implementation-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/implementation-plan.md)
    - [specs/test-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/test-plan.md)
    - [specs/change-log.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/change-log.md)
    - [specs/project-summary.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/project-summary.md)
- [x] **2.3. Tinh gọn thư mục `resources/docs/`**:
  - Giữ sơ đồ kiến trúc (`agent_graph.png`, `chat_agent_graph.png`), playbook xử lý sự cố Module 3 (`incident-playbook-*.md`), tài liệu phương pháp luận, và `m3-production-pipeline.md`.
  - Xóa các file nháp tạm không dùng.
- **Lệnh xác minh**: `pytest tests/test_capstone.py tests/test_eval.py tests/test_ci_workflows.py -v` (Đã PASS 48/48 tests)

---

### Phase 3: Tinh Gọn Thư Mục Scripts Vận Hành (`scripts/`)
> **Mục tiêu**: Giữ lại các công cụ vận hành và benchmark chính thức, loại bỏ hoàn toàn các file script scratch/vá tạm.

- [x] **3.1. Danh mục script vận hành chính thức giữ lại**:
  - [scripts/cache_benchmark.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/cache_benchmark.py): Benchmark tỷ lệ hit và tiết kiệm chi phí của Cache 2 tầng (đã trỏ mặc định về `resources/eval/`).
  - [scripts/cost_baseline.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/cost_baseline.py): Đo lường chi phí LLM và token baseline (đã trỏ mặc định về `resources/eval/`).
  - [scripts/run_agent_eval.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/run_agent_eval.py): Runner đánh giá Golden Dataset tự động (đã xuất báo cáo chuẩn tại `resources/eval/`).
  - [scripts/generate_replay_faq_200.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/generate_replay_faq_200.py): Sinh bộ dữ liệu 200 câu hỏi FAQ rổ VN30.
  - [scripts/start_ngrok_demo.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/start_ngrok_demo.py): Khởi chạy demo chia sẻ public URL.
  - [scripts/run_local.ps1](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/run_local.ps1) & [scripts/run_local.sh](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/scripts/run_local.sh): Khởi chạy cục bộ nhanh.
- [x] **3.2. Loại bỏ các scripts nháp/tạm**:
  - Đã xóa hoàn toàn: `fix_plan.py`, `update_plan.py`, `append_changelog.py`, `config5.py`, `run_eval_v4_md.py`, `run_golden_v5_eval_bundle.py` (và `tests/test_eval_bundle.py`).
- **Lệnh xác minh**: `python scripts/cache_benchmark.py --limit 10 --dry-run` (Đã PASS)

---

### Phase 4: Di Dời Thư Mục Triển Khai (`deploy/` -> `src/deploy/`)
> **Mục tiêu**: Đưa toàn bộ mã nguồn và cấu hình triển khai vào `src/deploy/`, giữ thư mục gốc sạch sẽ, cập nhật đường dẫn liên kết.

- [x] **4.1. Di chuyển thư mục `deploy/`**:
  - Đã chuyển toàn bộ `deploy/` thành `src/deploy/` (chứa `smoke.py`, `nginx-portfolio-watch.conf`). Xóa bỏ thư mục gốc `deploy/`.
- [x] **4.2. Cập nhật các tệp liên kết triển khai**:
  - Cập nhật `.github/workflows/cd.yml` phản ánh vị trí mới `src/deploy/smoke.py` và `src/deploy/lkg`.
  - Cập nhật [tests/test_ci_workflows.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/tests/test_ci_workflows.py), [tests/test_system.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/tests/test_system.py), và [tests/test_capstone.py](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/tests/test_capstone.py) để kiểm tra đường dẫn mới `src/deploy/smoke.py`.
- **Lệnh xác minh**: `pytest tests/test_ci_workflows.py tests/test_capstone.py -v` (Đã PASS 100%)

---

### Phase 5: Module Hóa Mã Nguồn Backend (`src/backend/`)
> **Mục tiêu**: Xóa bỏ toàn bộ tình trạng file rời rạc ở gốc `src/backend/`, đóng gói các chức năng vào đúng thư mục chuyên biệt.

- [x] **5.1. Quy hoạch các file rời rạc ở gốc `src/backend/`**:
  - `main.py` -> Quy hoạch thành `src/backend/api/main.py`.
  - `ai_client.py` & `ai_main.py` -> Tích hợp vào `src/backend/infra/llm/client.py` và `src/backend/infra/llm/service.py`.
  - `cors_util.py` -> Tích hợp vào `src/backend/api/middleware/cors.py`.
  - `steps.py` -> Tích hợp vào `src/backend/eval/steps.py`.
  - `store.py` -> Tích hợp vào `src/backend/infra/storage/store.py`.
- [x] **5.2. Hoàn thiện cấu trúc package chuẩn trong `src/backend/`**:
  - `src/backend/api/`: Quản lý routes, middleware, schemas và app entrypoint.
  - `src/backend/agents/`: 7 Worker Agents + Supervisor + Composer, mỗi agent là 1 subfolder hoàn chỉnh.
  - `src/backend/domain/`: Logic nghiệp vụ lõi (guardrails, chỉ báo RSI/SMA, memory models).
  - `src/backend/infra/`: Hạ tầng external adapters (LLM, Cache 2 tầng, Market data, Storage, Monitoring).
  - `src/backend/services/`: Dịch vụ nghiệp vụ (PortfolioService, MarketService, AlertService).
  - `src/backend/eval/`: Bộ công cụ đánh giá (gate, metrics, scorers).
- [x] **5.3. Cập nhật các đường dẫn import liên quan**:
  - Đảm bảo toàn bộ import nội bộ nhất quán và không phát sinh lỗi `ModuleNotFoundError`.
- **Lệnh xác minh**: `pytest tests/test_api.py tests/test_system.py -v` (Đã PASS 49/49 tests)

---

### Phase 6: Tái Cấu Trúc Bộ Kiểm Thử 3 Tầng (`tests/unit/`, `tests/integration/`, `tests/e2e/`)
> **Mục tiêu**: Gom gộp 24 file test phẳng thành 3 tầng chuẩn Production LLMOps theo Module 3 `LLM-Engineer-Handbook`.

- [x] **6.1. Thiết lập cấu trúc thư mục 3 tầng**:
  - Tạo: `tests/unit/`, `tests/integration/`, `tests/e2e/`.
- [x] **6.2. Phân bổ các bài test vào đúng tầng**:
  - **Tầng Unit (`tests/unit/`)**:
    - `test_guardrails.py`, `test_greeting_fastpath.py`, `test_indicators.py`, `test_portfolio_service.py`, `test_memory.py`, `test_output_guardrail_formatting.py`, `test_config.py`.
  - **Tầng Integration (`tests/integration/`)**:
    - `test_api.py`, `test_database.py`, `test_agents.py`, `test_chart.py`, `test_portfolio_watch_agent.py`, `test_system.py`, `test_web_ui_integration.py`, `test_monitoring.py`, `test_market.py`, `test_edge_cases.py`, `test_module3_features.py`.
  - **Tầng E2E / Eval (`tests/e2e/`)**:
    - `test_golden_v6_slices.py`, `test_eval.py`, `test_demo_walkthrough.py`, `test_ci_workflows.py`, `test_docker_setup.py`, `test_capstone.py`.
- [x] **6.3. Chuẩn hóa `tests/conftest.py`**:
  - Thiết lập fixture mock offline dùng chung (`VnstockPriceSource(fallback_on_error=True)`), đảm bảo không gọi internet và chạy siêu tốc.
- **Lệnh xác minh**:
  ```bash
  pytest tests/unit/ -v         # Đã PASS 61/61 tests (100%)
  pytest tests/integration/ -v  # Đã PASS 170/170 tests (100%)
  pytest tests/e2e/ -v          # Đã PASS 66/66 runnable tests (1 skipped baseline format)
  ```

---

### Phase 7: Kiểm Thử Toàn Diện, Đo Lường Tốc Độ CI & Nghiệm Thu Đồ Án
> **Mục tiêu**: Nghiệm thu sản phẩm đồ án tốt nghiệp cuối khóa, đảm bảo zero-regression, CI chạy < 5 phút và hồ sơ bảo vệ đồ án sẵn sàng.

- [x] **7.1. Chạy toàn bộ Test Suite 3 tầng**:
  - Chạy `pytest tests/ -v`, bảo đảm 100% bài test đạt trạng thái PASS (Đã hoàn thành: 298/298 tests PASS, 0 failures, 0 skipped).
- [x] **7.2. Kiểm tra độ chính xác Golden Dataset v6 (20/20 cases PASS)**:
  - Chạy `pytest tests/e2e/test_golden_v6_slices.py -v` đạt 100% PASS trên 10 lát cắt (Đã hoàn thành: 12/12 tests PASS, bao phủ trọn vẹn 20/20 test cases).
- [ ] **7.3. Đo lường tốc độ CI Pipeline**:
  - Xác nhận toàn bộ bài test hoàn tất trong **< 5 phút**.
- [ ] **7.4. Đồng bộ hồ sơ SDD & Cập nhật `specs/change-log.md`**:
  - Ghi nhận chi tiết kết quả tái cấu trúc và bàn giao cho người dùng.
- **Lệnh xác minh**: `pytest tests/ -v --durations=10`
