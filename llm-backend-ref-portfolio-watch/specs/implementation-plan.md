# Implementation Plan

Kế hoạch triển khai chi tiết theo phương pháp **Spec-Driven Development** cho dự án **Portfolio Watch**.

Nguyên tắc:
- Chỉ mở và thực hiện DUY NHẤT một phase tại một thời điểm.
- Trước khi code một phase: tóm tắt những gì sẽ làm, file nào sẽ sửa/tạo/xóa, và cách test.
- Sau khi hoàn thành một phase: đánh dấu `[x]`, cập nhật `specs/change-log.md`, và cung cấp lệnh kiểm thử xác minh.
- Giữ ứng dụng đơn giản, tập trung vào MVP.
- Chưa viết code ứng dụng trong giai đoạn lập kế hoạch này.

---

## Roadmap Tổng Quan

| Phase | Trọng Tâm Triển Khai | Trạng Thái |
| :---: | :--- | :---: |
| **Phase 1** | Project Setup & Baseline Documentation | `[x]` Hoàn thành |
| **Phase 2** | Fix Resources Path & Root Unification (Xóa `src/resources`) | `[x]` Hoàn thành |
| **Phase 3** | Clean Code & Naming Standardization (Xóa `backend/backend`) | `[x]` Hoàn thành |
| **Phase 4** | Test Suite Consolidation (Gói `tests/` xuống $\le 10$ files) | `[x]` Hoàn thành |
| **Phase 5** | Golden Dataset Evaluation & Evidence Archiving (Lưu dẫn chứng) | `[x]` Hoàn thành |
| **Phase 6** | Local Run Instructions & Error State Verification | `[x]` Hoàn thành |
| **Phase 7** | Docker Packaging & End-To-End Verification | `[x]` Hoàn thành |

---

## Phase 1: Project Setup & Baseline Documentation

Mục tiêu: Thiết lập toàn bộ hồ sơ đặc tả, quy định AI agent, kế hoạch kiểm thử và đường cơ sở thay đổi trước khi viết code.

- [x] Tạo và chuẩn hóa [AGENTS.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/AGENTS.md) với các quy tắc cốt lõi: Clean Code, tài nguyên ở root `resources/`, bộ test $\le 10$ files, chạy test lưu dẫn chứng.
- [x] Cập nhật [specs/product-spec.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/product-spec.md) đầy đủ 6 phần: App Goal, Target Users, Core User Flow, Features In Scope, Features Out of Scope, Acceptance Criteria.
- [x] Cập nhật [specs/implementation-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/implementation-plan.md) chia nhỏ thành 7 phases tuần tự với checklist cụ thể.
- [x] Cập nhật [specs/test-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/test-plan.md) với thiết kế 10 files kiểm thử và kế hoạch lưu dẫn chứng Golden Dataset.
- [x] Cập nhật [README.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/README.md) phản ánh kiến trúc chuẩn hóa, hướng dẫn Docker và chạy Local.
- [x] Khởi tạo nhật ký trong [specs/change-log.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/specs/change-log.md).

**Tiêu chuẩn nghiệm thu Phase 1:**
- Cả 6 file tài liệu được đồng bộ đầy đủ, nhất quán và không có mâu thuẫn.

---

## Phase 2: Fix Resources Path & Root Unification

Mục tiêu: Đưa toàn bộ tài nguyên về thư mục gốc `resources/` (ngang cấp với `src/`), xóa bỏ triệt để thư mục `src/resources/`, và sửa toàn bộ code xử lý đường dẫn.

- [x] Rà soát và sửa các hàm xử lý đường dẫn tài nguyên:
  - Sửa `src/backend/agents/chart_agent.py`: thay đổi `Path(__file__).resolve().parents[2]` thành `parents[3]` (trỏ về thư mục gốc workspace) để lưu ảnh vào `resources/data/charts/`.
  - Sửa `src/backend/backend/main.py`: gọi `get_charts_dir()` đồng bộ trỏ về root `resources/data/charts/`.
  - Sửa `src/backend/database/connection.py`: đảm bảo SQLite path fallback trỏ về `resources/data/portfolio_watch.db` (`parents[3]`).
  - Sửa `src/backend/services/hitl_service.py`: trỏ chính xác về `resources/data/hitl_feedback.json` (`parents[3]`).
  - Sửa `src/backend/infra/llm/prompt_registry.py`: bổ sung `here.parents[4] / "resources" / "prompts"` trỏ chính xác về `resources/prompts/`.
  - Sửa `src/backend/eval/run_detailed.py`, `src/backend/eval/run.py`, và `src/backend/eval/regression.py`: sửa fallback root thành `parents[3]`.
- [x] Di chuyển toàn bộ 41 file ảnh biểu đồ hiện có từ `src/resources/data/charts/` sang `resources/data/charts/`.
- [x] Xóa bỏ hoàn toàn thư mục `src/resources/` trên ổ đĩa.
- [x] Kiểm tra xác nhận: Chạy thử kiểm thử `test_chart_agent.py` và kiểm tra `Test-Path src/resources` trả về `False`, ảnh được ghi và phục vụ từ root `resources/data/charts/`.

**Tiêu chuẩn nghiệm thu Phase 2:**
- Thư mục `src/resources/` biến mất hoàn toàn khỏi cây thư mục.
- Toàn bộ dữ liệu, prompt, ảnh chart và telemetry được nạp/ghi chuẩn xác tại root `resources/`.

---

## Phase 3: Clean Code & Naming Standardization (Core Backend)

Mục tiêu: Tinh gọn cấu trúc mã nguồn, loại bỏ thư mục con lặp lại `src/backend/backend/`, đặt tên file/hàm/node đúng chức năng hiện tại, và bổ sung docstrings đầy đủ.

- [x] Tái cấu trúc thư mục backend phẳng và rõ ràng:
  - Loại bỏ thư mục trùng lặp `src/backend/backend/`.
  - Thống nhất entrypoint FastAPI duy nhất tại `src/backend/main.py`.
  - Dọn dẹp router trùng lặp và các import dư thừa.
- [x] Chuẩn hóa tên các Agent Nodes trong LangGraph workflow:
  - `guardrail_node`: Node phòng vệ cửa ngõ, chặn Prompt Injection & Out-of-Scope.
  - `rewrite_node`: Node chuẩn hóa câu hỏi và phân giải đại từ ngữ cảnh.
  - `supervisor_node`: Node điều phối định tuyến Swarm.
  - `price_node`: Node thu thập dữ liệu giá Vnstock.
  - `news_node`: Node trích xuất tin tức CafeF.
  - `chart_node`: Node sinh biểu đồ kỹ thuật Matplotlib.
  - `diagram_node`: Node sinh sơ đồ quy trình Mermaid.
  - `composer_node`: Node tổng hợp dữ liệu và stream câu trả lời.
- [x] Áp dụng nguyên tắc Clean Code:
  - Giữ các hàm nghiệp vụ trọn vẹn, không băm nhỏ thành các helper 2-3 dòng.
  - Viết docstrings tiếng Việt/Anh chuẩn mực cho toàn bộ module, class và function chính.
  - Xóa bỏ dead code và các file rác trung gian.

**Tiêu chuẩn nghiệm thu Phase 3:**
- Cấu trúc `src/backend/` gọn gàng, không còn thư mục lồng nhau `backend/backend`.
- Các node agent và hàm nghiệp vụ có tên gọi rõ ràng, trực quan, đúng chức năng thực tế.

---

## Phase 4: Test Suite Consolidation (Gói `tests/` xuống <= 10 files)

Mục tiêu: Gom 33 file kiểm thử hiện tại vốn bị phân mảnh qua các phase thành tối đa 10 file kiểm thử logic, chuẩn mực, bao phủ 100% chức năng.

- [x] Tái cấu trúc và hợp nhất thành 10 file kiểm thử duy nhất:
  - `tests/conftest.py`: Fixtures dùng chung, in-memory DB, mock LLM/Vnstock, test clients.
  - `tests/test_agents.py`: Kiểm thử các agent nodes và luồng điều phối Swarm.
  - `tests/test_guardrails.py`: Kiểm thử chặn Prompt Injection và từ chối Out-of-Scope.
  - `tests/test_memory.py`: Kiểm thử ngữ cảnh hỏi nối tiếp Turn 1 ➔ Turn 2 và quản lý sessions.
  - `tests/test_market.py`: Kiểm thử `MarketService`, ma trận 10D và đồng bộ dữ liệu giá.
  - `tests/test_chart.py`: Kiểm thử `ChartAgent` và lưu trữ biểu đồ vào `resources/data/charts/`.
  - `tests/test_api.py`: Kiểm thử các endpoint FastAPI (Chat SSE streaming, sessions, market, HITL).
  - `tests/test_database.py`: Kiểm thử SQLite models, migrations, lưu trữ tin nhắn.
  - `tests/test_eval.py`: Kiểm thử runner đánh giá Golden Dataset và cơ chế chấm điểm.
  - `tests/test_system.py`: Kiểm thử Docker container, biến môi trường và tài liệu hướng dẫn.
- [x] Xóa bỏ toàn bộ các file test cũ tạm thời theo phase (`test_env_example_phase16.py`, `test_readme_phase*.py`, `test_phase14.py`, v.v.).
- [x] Chạy `pytest tests/ -v` xác nhận: Đúng $\le 10$ files kiểm thử, 100% test cases vượt qua (82/82 passed).

**Tiêu chuẩn nghiệm thu Phase 4:**
- Thư mục `tests/` có đúng $\le 10$ files kiểm thử.
- Toàn bộ bài test chạy pass mà không mất đi bất kỳ khía cạnh kiểm thử cốt lõi nào.

---

## Phase 5: Golden Dataset Evaluation & Evidence Archiving

Mục tiêu: Chạy kiểm thử tự động toàn bộ 40 câu hỏi Golden Dataset, đánh giá chi tiết chất lượng câu trả lời, và lưu lại dẫn chứng minh bạch.

- [x] Chuẩn bị bộ dữ liệu chuẩn `resources/eval/golden_v5.yaml` gồm đúng 40 câu hỏi cân bằng 7 nhóm:
  - `lookup` (12), `comparison` (8), `explain_why` (6), `charting_diagram` (4), `session_memory` (3), `out_of_scope` (4), `injection` (3).
- [x] Thực thi runner đánh giá chi tiết:
  ```bash
  python -m backend.eval.run_detailed
  ```
- [x] Kiểm tra các chốt chặn chất lượng:
  - Tỷ lệ vượt qua tổng thể đạt $\ge 85\%$ (Đạt 92.5% - 37/40 passed).
  - Slice `injection` đạt **100% Pass** (Zero-Tolerance Security Gate - 3/3 passed).
  - Slice `out_of_scope` đạt **100% Pass** (từ chối lịch sự, không bịa giá FPT - 4/4 passed).
- [x] Xuất bản và lưu trữ hồ sơ dẫn chứng:
  - Báo cáo Markdown chi tiết: `specs/eval/eval_results_golden_v5.md`.
  - Tệp cơ sở dữ liệu JSON: `specs/eval/v5_baseline.json`.

**Tiêu chuẩn nghiệm thu Phase 5:**
- [x] Hồ sơ dẫn chứng đánh giá được lưu trữ đầy đủ trong `specs/eval/`, có số liệu minh bạch về token, chi phí và latency.

---

## Phase 6: Local Run Instructions & Error State Verification

Mục tiêu: Kiểm tra xác minh môi trường chạy cục bộ (không dùng Docker), xác thực các trạng thái lỗi và hoàn thiện hướng dẫn chạy local.

- [x] Kiểm tra chạy backend API cục bộ bằng Uvicorn:
  ```bash
  uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
  ```
- [x] Kiểm tra phục vụ giao diện Web SPA tại `http://localhost:8000`.
- [x] Xác minh các trạng thái lỗi và validation:
  - Trường hợp không có OpenAI API Key ➔ kích hoạt chế độ Heuristic fallback mượt mà.
  - Trường hợp câu hỏi rỗng hoặc payload không hợp lệ ➔ trả về mã lỗi HTTP 422 rõ ràng.
  - Trường hợp session không tồn tại ➔ xử lý tạo mới hoặc báo lỗi thân thiện.
- [x] Cập nhật phần hướng dẫn chạy local trong [README.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch/README.md) đầy đủ prerequisites, cài đặt, và troubleshooting.

**Tiêu chuẩn nghiệm thu Phase 6:**
- [x] Bất kỳ ai làm theo hướng dẫn trong README đều có thể khởi chạy ứng dụng local thành công và nhận diện rõ các trạng thái phản hồi.

---

## Phase 7: Docker Packaging & End-To-End Verification

Mục tiêu: Đóng gói hệ thống 2 containers hoàn chỉnh với Docker Compose và kiểm thử nghiệm thu End-To-End toàn bộ ứng dụng.

- [x] Cập nhật `src/backend/Dockerfile` và `docker-compose.yml` theo cấu trúc mới:
  - Lệnh khởi động container backend: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
  - Gắn kết volume dữ liệu bền vững `/app/data` và root `resources/`.
- [x] Khởi chạy toàn bộ hệ thống bằng một lệnh duy nhất:
  ```bash
  docker compose up --build -d
  ```
- [x] Chạy kiểm thử tự động xác minh bên trong container:
  ```bash
  docker compose run --rm app pytest tests/ -v
  docker compose run --rm app python -m backend.eval.run_detailed
  ```
- [x] Xác minh toàn bộ các luồng trải nghiệm trên trình duyệt:
  - Frontend Web UI tại `http://localhost:3000`.
  - Backend API Docs tại `http://localhost:8000/docs`.
  - Chat streaming SSE mượt mà, inspector sáng đèn đúng node.
  - Ma trận Market Watch 10D hiển thị số liệu đồng nhất.
- [x] Lập báo cáo tổng kết trạng thái MVP (MVP Status Report).

**Tiêu chuẩn nghiệm thu Phase 7:**
- [x] Hệ thống 2 container chạy ổn định (`healthy`), không phát sinh lỗi.
- [x] Toàn bộ các tiêu chí nghiệm thu MVP đạt chuẩn.
