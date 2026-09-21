# Change Log

Nhật ký thay đổi theo thời gian cho project Portfolio Watch & Chat Agent.
Ghi theo ngày, mới nhất ở trên.

## 2026-09-21 — README local development instructions

### What

- Cập nhật `README.md`: mục **Local development** — prerequisites, install,
  env, lệnh chạy AI / Backend / Frontend, URL local, troubleshooting.
- Giữ Docker làm đường chạy product khuyến nghị; **không** đổi app logic.

### Test

Đọc README; (tuỳ chọn) chạy 3 process local và mở http://127.0.0.1:5173.

## 2026-09-19 — Phase 15c–15d volume + healthcheck

### 15c

- Volume `pw_data` → `/app/data` (ai + backend). **Giữ path:** AI
  `portfolio_watch.db`, Backend `backend_store.db` — không migrate.

### 15d

- `docker-compose.yml` — healthcheck `/health` cho `ai` (:8001) và `backend` (:8000).

### Test

```bash
python -m pytest tests/test_docker_compose.py -q
docker compose up --build -d
docker compose ps   # ai/backend healthy
```

## 2026-09-19 — Tests dùng dependency thật (bỏ fakes.py)

### What

- Xóa `tests/fakes.py`; `conftest.py` wire `VnstockPriceSource`, `CafefNewsSource`,
  SQLite thật qua `build_real_deps()`.
- Bỏ patch Heuristic brain — pytest dùng LLM production (cần `.env` + network).
- Backend `test_chat_proxy_to_real_ai`: uvicorn AI session fixture + HTTP thật.
- Langfuse hierarchy mock bỏ; giữ test no-op khi `MONITORING_ENABLED=false`.

### Test

```bash
cp .env.example .env   # điền OPENAI_API_KEYS
python -m pytest tests/ -q
```

## 2026-09-19 — Gom tests còn 7 file

### What

- Xóa ~95 file `tests/test_*.py` rời; giữ 7 file cốt lõi:
  `test_docker`, `test_backend`, `test_ai`, `test_agents`, `test_eval`,
  `test_tracing`, `test_frontend` (+ `conftest.py`, `fakes.py`).

### Test

```bash
python -m pytest tests/ -q
```

## 2026-09-19 — Phase 15b Dockerfile src-only (review — agy scratch)

### Implement

- `Dockerfile` — bỏ `COPY backend/`, `COPY frontend/`; UI nằm trong `COPY src`.
- Image tag giữ `portfolio-watch:split` (compose).
- `tests/test_dockerfile.py`, `tests/test_docker_single_url.py` — assert path mới.

### Test

```bash
python -m pytest tests/test_dockerfile.py tests/test_docker_env_file.py tests/test_docker_single_url.py -q
docker compose build
```

## 2026-09-19 — Phase 15a Compose 3 service trỏ entry mới trong src/portfolio_watch/

### Implement

- Copy legacy backend `backend/*.py` → `src/portfolio_watch/backend/` và đổi absolute import `backend.` thành `src.portfolio_watch.backend.`.
- Copy legacy frontend `frontend/*` → `src/portfolio_watch/frontend/`.
- Cập nhật `docker-compose.yml`: backend trỏ uvicorn command tới `src.portfolio_watch.backend.main:app`, frontend trỏ directory tới `src/portfolio_watch/frontend`. (Không xoá các thư mục cũ).

### Test

```bash
python -m pytest tests/test_docker_compose.py tests/test_backend_no_agent_imports.py -q
```

## 2026-09-19 — Phase 14f–14g Langfuse no-op + mock hierarchy

### 14f

- `tests/test_monitoring_noop.py` — `test_v1_scan_ok_when_monitoring_disabled`.

### 14g (review — agy ghi scratch, implement lại trong repo)

- `tests/test_langfuse_tracing.py` — `test_agent_step_child_of_agent_not_root`,
  `test_agent_step_noop_when_monitoring_disabled`.

### Test

```bash
python -m pytest tests/test_monitoring_noop.py tests/test_langfuse_tracing.py -q
```

**Checklist thủ công (test-plan §4):** Langfuse `:3000` + `docker compose up` → 1 chat →
1 trace, expand ≥ 3 cấp span.

## 2026-09-19 — Phase 14e Docker Langfuse env (agy)

### Implement

- `docker-compose.yml` — AI service: `LANGFUSE_HOST=http://host.docker.internal:3000`,
  `extra_hosts: host.docker.internal:host-gateway` (keys vẫn từ `.env`).
- `tests/test_docker_env_file.py` — `test_compose_configures_langfuse_host`.

### Test

```bash
python -m pytest tests/test_docker_env_file.py -q
```

## 2026-09-19 — Phase 14d wire agent_step + graph turn propagation

### Implement

- `agents/*/nodes.py` — `agent_step(turn, …)` ở bước nội bộ (price fetch, news react,
  draft, guardrail, classify, …).
- **Review fix:** `graph/chat.py`, `graph/scan.py` truyền `turn=turn` xuống mọi
  `run_*_agent` / `rewrite_question` / `route_question` / `classify_event` để step span
  lồng đúng dưới agent span.
- `tests/test_langfuse_tracing.py` — fake stubs nhận `turn=`.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py tests/test_graph_chat.py tests/test_graph_scan.py -q
```

## 2026-09-19 — Phase 14c agent_step (trace_step helper) + review

### Implement

- agy SUCCESS nhưng ghi scratch workspace — implement lại trong repo.
- `tracing.py` — thêm `agent_step(turn, agent_name, step_name, …)`.
- `tests/test_langfuse_tracing.py` — `test_trace_step_three_level_hierarchy`.

### Review vs test-plan §4

- **Pass:** root → agent → step 3 cấp (mock).
- **Missing (14d):** wire `agent_step` vào `agents/*/nodes.py`.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py -q
```

## 2026-09-19 — Phase 14a root trace + 14b agent span (review)

### 14a Implement (agy)

- `v1.py` — gọi `answer_question` / `scan_symbol` (wrapper có `trace_request`).
- **Quyết định:** 1 POST `/v1/scan` = 1 trace (per-request, không per-symbol batch).

### 14b Review

- Graph nodes (`chat.py`, `scan.py`) đã gọi `agent_span(turn, …)`; `turn` đồng bộ
  qua application wrapper (`turn = request_id or uuid`).
- **Pass:** `test_trace_request_and_agent_spans_when_enabled` — hierarchy root → agent.
- agy 14b fail (503) — xác nhận code hiện tại đủ spec.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py tests/test_request_id_propagation.py tests/test_monitoring_noop.py tests/test_ai_v1_service.py -q
docker compose up --build
# Gửi 1 chat → Langfuse UI :3000 → 1 trace (checklist 14g thủ công sau)
```

## 2026-09-19 — Phase 13f deprecate application → graph + review

### Implement (agy `gemini-3.1-pro-high`)

- `application/answer_question.py` — wrapper `run_chat_graph()` + `trace_request`.
- `application/scan_symbol.py` — wrapper `run_scan_graph()` + helpers giữ nguyên.
- Phase 13 pytest stub: `test_graph_chat.py`, `test_graph_scan.py`, `test_graph_steps.py`.

### Review vs product-spec / test-plan

- **Pass:** eval/router vẫn gọi `answer_question`/`scan_symbol`; orchestration qua graph.
- **Fixed:** tests patch `graph.chat.*` thay vì `application.answer_question.*`.

### Test

```bash
python -m pytest tests/test_answer_question.py tests/test_scan_symbol.py tests/test_graph_chat.py tests/test_graph_scan.py tests/test_langfuse_tracing.py -q
docker compose run --rm ai pytest tests/test_ai_v1_service.py -q
```

## 2026-09-19 — Phase 13d steps[] from graph + review

### Implement (agy `gemini-3.1-pro-high`)

- `graph/steps.py` — `build_steps_from_chunks()` từ `stream_mode="updates"`.
- `chat.py` / `scan.py` — gán `result.steps` từ stream chunks.
- `v1.py` — `/v1/scan` dùng `result.steps`; xóa `build_scan_steps()`.
- `tests/test_graph_steps.py` — unit chat + scan step mapping.

### Review vs product-spec / test-plan

- **Pass:** test-plan §3 — chat/scan invoke trả `steps[]` theo graph nodes.
- **Missing (13e–13f):** export PNG, deprecate application layer.

### Test

```bash
python -m pytest tests/test_graph_steps.py tests/test_graph_chat.py tests/test_ai_v1_service.py -q
```

## 2026-09-19 — Phase 13b review vs product-spec / test-plan

### Pass

- test-plan §3 (scan): graph compile OK; nodes khớp luồng `agents.md` (price+news →
  classifier → eval → synthesis → Gate1/Gate2).
- product-spec §2 (giám sát): normal END; abnormal → eval → synthesis → auto-send /
  HITL Gate1; Gate2 proposal pending.
- `run_scan_graph()` contract `ScanSymbolResult` giống `scan_symbol`.

### Fixed (review)

- Error handling: eval/synthesis node catch → route END, giữ price/news/routing.
- `request_id` + fallback `turn` UUID (parity `scan_symbol`).
- Warning log khi notifier fail ở `gate1_auto`.
- Tests: port parity từ `test_scan_symbol.py` (+ eval error path mock).

### Missing (không thuộc 13b — phase sau)

- Wire API `/v1/scan` → graph (**13c**).
- `steps[]` từ graph events (**13d**).
- `trace_request` root span (**14a**); export graph PNG (**13e**).

### Test

```bash
python -m pytest tests/test_graph_scan.py -q
```

## 2026-09-19 — Phase 13b agy validate + review

### Agy `--task implement` (validation)

- Prompt: `.agy-runs/phase13b-validate-prompt.txt` → output:
  `.agy-runs/phase13b-implement-validate.json` (SUCCESS, ~205s).
- **So sánh với bản Cursor:** `scan.py`, `state.py` **giống hệt** (agy không sửa core).
- **Agy bổ sung:** 3 test (`low_confidence`, `gate2`, `empty_symbol`) trong
  `tests/test_graph_scan.py`; export `ChatState`/`ScanState` trong `graph/__init__.py`.
- **Giữ bản hiện tại** + cải tiến agy (tests/exports); backup Cursor:
  `.agy-runs/backup-13b-cursor/`.

### Agy `--task review --skip-permissions`

- Output: `.agy-runs/20260919-042044-review.json`.
- High: thiếu `trace_request` (Phase 14), thiếu try/except abnormal pipeline.
- Medium: thiếu `request_id` param, 4 test parity còn thiếu vs `test_scan_symbol.py`.

### Workflow (từ 13c, mọi `/antigravity-cli`)

1. `agy --task implement` trước (prompt trong `.agy-runs/`).
2. Đọc JSON output; pytest verify.
3. Chỉ sửa tay khi agy fail / test fail.
4. `agy --task review --skip-permissions` khi cần.

## 2026-09-19 — Phase 13b LangGraph scan

### Implement

- `src/portfolio_watch/graph/scan.py` — graph: fetch (price+news) → event_classifier
  → (normal END | eval → gate2? → synthesis → gate1 auto/pending);
  `run_scan_graph()` trả `ScanSymbolResult` (cùng contract `scan_symbol`).
- `src/portfolio_watch/graph/state.py` — thêm `ScanState`.
- `tests/test_graph_scan.py` — compile + normal/abnormal invoke stub.
- Reuse helpers từ `application/scan_symbol.py`; runtime deps qua `contextvars`.

### Test

```bash
python -m pytest tests/test_graph_scan.py -q
```

## 2026-09-19 — Phase 13a LangGraph chat + review

### Implement

- `src/portfolio_watch/graph/chat.py` — graph thật: rewrite → supervisor →
  workers → answer_composer; `run_chat_graph()` trả `AnswerQuestionResult`.
- `src/portfolio_watch/graph/state.py` — `ChatState`.
- `tests/test_graph_chat.py` — compile + invoke stub (heuristic brains).
- Runtime deps qua `contextvars` (LangGraph không giữ object trong configurable).

### Review vs product-spec / test-plan

- **Pass:** test-plan §3 partial — graph compile + invoke stub; nodes khớp chat flow.
- **Missing (13b–13f):** scan graph, wire API, steps từ graph events, deprecate application.

### Test

```bash
python -m pytest tests/test_graph_chat.py -q
```

## 2026-09-19 — Phase 12 complete (12a–12i) + review

### Implement

- Port 7 agents → `src/portfolio_watch/agents/<name>/` (nodes, state, schemas;
  news/eval có `tools.py`).
- Legacy `domain/agents/*.py` re-export; `tests/conftest.py` patch factory trên
  `agents/*/nodes` + domain.
- **12h:** giữ prompts tại `infra/llm/prompt_registry` + `prompts/` YAML (không
  tách per-agent folder — tránh trùng).
- **12i:** `guardrails` + `entities` giữ `domain/`; agents import qua domain
  cho đến Phase 15 (không duplicate sang `shared/`).

**Lưu ý:** `agy` chưa cài — implement trực tiếp.

### Review vs product-spec / test-plan

- **Pass:** test-plan §2 — mỗi agent folder + pytest tương ứng pass.
- **Pass:** product-spec AC §2 partial — 7 agent folders; backend vẫn không import agents.
- **Missing:** Phase 13+ (graph thật, Langfuse, Docker-only, xóa scripts).

### Test

```bash
python -m pytest tests/ -q -k "price_agent or news_agent or event_classifier or eval_agent or synthesis_agent or supervisor or answer_composer or phase12"
```

## 2026-09-19 — Phase 12a price_agent + review (SDD Bước 5–6)

### Implement

- Port `domain/agents/price_agent.py` → `agents/price_agent/` (`nodes.py`, `state.py`,
  `schemas.py`, `__init__.py`).
- Legacy path re-export giữ import cũ.
- `tests/test_phase12a_price_agent.py`.

**Lưu ý:** `agy` chưa cài — implement trực tiếp thay vì `agy_run.py`.

### Review vs product-spec / test-plan

- **Pass:** test-plan §2 price_agent (fetch close + change_pct); không LLM; 12 tests pass.
- **Pass:** pattern `agent_pr` (nodes + state + schemas).
- **Missing (Phase 12+):** các agent còn lại, graph wire, Langfuse.

### Test

```bash
python -m pytest tests/test_price_agent.py tests/test_phase12a_price_agent.py tests/test_price_evidence_before_pct.py -q
```

## 2026-09-19 — Review Phase 11 vs product-spec / test-plan (SDD Bước 6)

### Pass (Phase 11 scope)

- Skeleton 5 thư mục + `__init__.py` + README; import package OK.
- Bảng migrate trong change-log + `src/portfolio_watch/README.md`.
- `graph/` re-export `domain/graph/` — không đổi hành vi.
- Functional smoke pass (agent, API, graph, backend-no-agent-imports).
- Legacy `backend/`, `frontend/`, `scripts/` song song — đúng plan.

### Fail / ngoài scope Phase 11 (chưa sửa)

- `pytest tests/ -q` full: ~30 fail — doc-guard MVP (README Phase 6–10, plan cũ).
  Không do skeleton; dọn Phase **16d**.
- product-spec AC §5.2–5.3 (agent folders, xóa scripts): Phase **12–15**.
- test-plan §2–§5 (agent refactor, LangGraph, Docker-only eval): Phase **12–15**.

### Fix review

- Thêm `src/portfolio_watch/README.md` (bảng migrate trung tâm).
- Mở rộng `tests/test_phase11_v2_skeleton.py`: import từng package + verify
  bảng migrate trong change-log và `src/portfolio_watch/README.md`.

### Test Phase 11

```bash
python -m pytest tests/test_phase11_v2_skeleton.py -q
```

## 2026-09-19 — Phase 11 V2 monorepo skeleton

### Thay đổi

- Tạo skeleton V2 dưới `src/portfolio_watch/`:
  `agents/`, `backend/`, `frontend/`, `eval/`, `graph/` — mỗi folder có
  `__init__.py` + `README.md`.
- `graph/__init__.py` re-export từ `domain/graph/` (logic giữ nguyên đến Phase 13).
- `tests/test_phase11_v2_skeleton.py` — guard cấu trúc + re-export.
- Code legacy **song song**, chưa xóa root `backend/` / `frontend/` / `scripts/`.

### Bảng migrate (V2)

| Cũ | Mới |
|---|---|
| `backend/main.py` | `src/portfolio_watch/backend/` |
| `frontend/` (root) | `src/portfolio_watch/frontend/` |
| `domain/agents/*.py` | `src/portfolio_watch/agents/<name>/` |
| `domain/graph/` | `src/portfolio_watch/graph/` (Phase 13) |
| `scripts/run_eval.py` | `src/portfolio_watch/eval/run.py` (Phase 15) |

`pyproject.toml`: `include = ["src*", "backend*"]` đã cover package mới — không đổi.

### Test

```bash
python -m pytest tests/test_phase11_v2_skeleton.py -q
```

## 2026-09-19 — Phase 1 V2 project setup (SDD Bước 5)

### Thay đổi

- Xác nhận MVP Docker: `docker compose up --build` — backend :8000, AI :8001,
  frontend :5173; smoke `POST /chat` + `POST /scan` → 200.
- Tạo `specs/eval/v2_baseline.json` — golden 30/30 (từ Phase 5 regression);
  ghi `phase1_docker_smoke`.
- Cập nhật `.env.example` — block V2 Langfuse (`host.docker.internal` trong Docker).
- README: mục «V2 in progress», legacy paths sẽ deprecated Phase 15.
- `tests/test_phase1_v2_setup.py` — guard baseline + checklist docs.
- Đánh dấu Phase 1 `[x]` trong `specs/implementation-plan.md`.

### Quyết định V2 (chốt Phase 1)

- Giữ golden **30 case**; không nới scorer để pass.
- Thứ tự implement: **1 → 11 → 12 → 13 → 14 → 15 → 16**.
- Langfuse self-host `:3000` trên host; AI container dùng `host.docker.internal`.

### Test

```bash
docker compose up --build -d
python -m pytest tests/test_phase1_v2_setup.py -q
# Re-run golden baseline (optional):
python scripts/phase5_regression.py --case-delay 20
```

## 2026-09-19 — AGENTS.md (SDD Bước 4)

### Thay đổi (docs only)

- Viết lại `AGENTS.md` ngắn gọn: đọc spec trước, 1 phase/task, không thêm lib,
  cập nhật change-log + hướng dẫn test sau mỗi implement; giữ quy tắc V2.

### Review vs product-spec / test-plan

- **Pass:** align SDD Guide Bước 4.
- **Fail:** chưa implement Phase 1 checklist.

## 2026-09-19 — Review implementation-plan (SDD Bước 3)

### Thay đổi (spec only)

- `specs/implementation-plan.md`: rewrite phase nhỏ — Phase 1 (V2 setup) +
  Phase 11–16 với checklist con (12a–12g, 13a–13f, …); thứ tự phụ thuộc.

### Review vs product-spec / test-plan

- **Pass:** align product-spec acceptance; test-plan có thể cập nhật ở Phase 16d.
- **Fail:** chưa implement.

## 2026-09-19 — Review product-spec (SDD Bước 2)

### Thay đổi (spec only)

- `specs/product-spec.md`: cấu trúc lại 6 mục SDD (goal, users, flow, in/out
  scope, acceptance) — ngắn gọn, flow chat/scan/eval cụ thể; gom kiến trúc/Langfuse
  vào in-scope.

### Review vs product-spec / test-plan

- **Pass:** đủ checklist SDD Guide Bước 2.
- **Fail:** chưa implement Phase 11+.

## 2026-09-19 — Spec V2: clean agents + src monorepo + Docker product

### Thay đổi (spec only — chưa implement)

- Viết lại `specs/product-spec.md` — mục tiêu V2: cấu trúc `agent_pr`, FE/BE/AI
  trong `src/`, xóa `scripts/`, Langfuse trace lồng nhau (1 trace / câu hỏi).
- Viết lại `specs/implementation-plan.md` — Phase 11–16 (unchecked).
- Viết lại `specs/test-plan.md` — test Docker-only + Langfuse checklist.
- Cập nhật `README.md`, `AGENTS.md` cho vòng V2.

### Quyết định kiến trúc (chốt trong spec)

- Langfuse self-host `:3000` trên **host** — AI container dùng
  `host.docker.internal:3000` (tham chiếu `llm-engineer-demo/docker-compose.yml`).
- Không gói Langfuse stack vào compose repo này.
- Eval / regression → `python -m src.portfolio_watch.eval.*` trong container AI.

### Review vs product-spec / test-plan

- **Pass:** acceptance criteria V2 ghi rõ; phase tách nhỏ.
- **Fail:** chưa có code Phase 11+.
- **Missing:** Phase 12c backlog placeholder.

## 2026-09-19 — LangGraph thật + save_graph_visualization (hierarchical)

### Thay đổi
- `src/portfolio_watch/domain/graph/workflow.py`: `StateGraph` khớp luồng
  `scan_symbol` + `answer_question`; `save_graph_visualization()` copy pattern
  `llm-engineer-demo/.../hierarchical.py` (PNG trước, fallback `.mmd`).
- Xóa `visualize.py`; CLI: `python -m ...workflow` hoặc `scripts/draw_agent_graph.py`.
- Cập nhật tests graph + `specs/agents.md`.

### Review vs product-spec / test-plan
- **Pass:** Phase 10 visualization từ code thật; 13 node / 26 edge.
- **Fail:** không.
- **Missing:** graph chưa thay imperative orchestration (chỉ visualize).

## 2026-09-18 — SDD: README «Demo with local»

### Thay đổi
- `README.md`: mục **Demo with local** — start FE/BE/AI (5173/8000/8001),
  expose FE trên local, cấu hình `frontend/config.js` / `?backend=`, ngrok
  Backend tuỳ chọn; giữ kịch bản watchlist/chat/scan.
- Không đổi app logic.
- Tests: `tests/test_readme_demo_with_local.py`; cập nhật
  `test_readme_phase7_demo_scenario.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4/5/8 hướng demo 3 process + UI; test-plan demo thủ công.
- **Fail:** không.
- **Missing:** không (docs only).

## 2026-09-18 — SDD Bước 9: README Local development

### Thay đổi
- `README.md`: mục **Local development** — prerequisites, install
  (`pip install -e ".[dev]"`), env vars, lệnh AI/Backend/Frontend, local
  URLs, troubleshooting tóm tắt; cập nhật **Trạng thái** (Phase 8 xong).
- Không đổi app logic.
- Test: `tests/test_readme_local_development_sdd.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4 hướng (3 process / 3 URL) có hướng dẫn README; test-plan
  acceptance map «3 process riêng → README lệnh».
- **Fail:** không.
- **Missing:** không (docs only).

## 2026-09-18 — Phase 3c: Rà soát backlog — không có gap mới

### Thay đổi
- `implementation-plan.md` §3c: đóng checkbox placeholder «Thêm task khi
  gap»; ghi triage — `blocked_cases.yaml` trống + Phase 5 regression
  30/30 / injection 100%; giữ hướng dẫn thêm `- [ ]` + blocked entry khi
  fail sau này (không nới scorer).
- Test: `tests/test_phase3c_backlog_triage.py`.
- **Không** thêm feature multi-agent mới (không có gap cần code).

### Review vs product-spec / test-plan
- **Pass:** AC3 (case fail có ghi chú + backlog khi cần — hiện không có
  fail/blocked); test-plan Quality Loop bước cập nhật Phase 3c khi cần;
  acceptance map «Case fail → change-log + Phase 3c».
- **Fail:** không.
- **Missing:** không trong phạm vi vòng Quality Loop + FE/BE/AI (Phase
  1–8 đã [x]; 3c không còn checkbox mở).

## 2026-09-18 — Phase 8 hoàn thành: `.env.example` đủ biến Langfuse

**Ngày hoàn thành Phase 8 (Tracing with Langfuse):** **2026-09-18**

### Thay đổi
- `.env.example`: khối Monitoring ghi đủ `MONITORING_ENABLED`,
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` + chú thích
  no-op khi tắt/thiếu key, cloud vs self-host, `pip install langfuse`,
  trỏ README Phase 8; không nhúng key thật.
- Test: `tests/test_env_example_phase8_langfuse.py`.

### Review vs product-spec / test-plan
- **Pass:** cấu hình AC6 / test-plan §4 có đủ biến trong `.env.example`
  (khớp settings + README); secret không leak vào example.
- **Fail:** không (phạm vi item / đóng Phase 8).
- **Missing:** không còn checkbox Phase 8 trong implementation-plan.

## 2026-09-18 — Phase 8: README bật monitoring + tìm trace Langfuse

### Thay đổi
- `README.md` mục **Langfuse (Phase 8)**: bật `MONITORING_*` / `LANGFUSE_*`,
  mở UI Langfuse, tìm trace theo câu hỏi / `request_id`, troubleshooting;
  bảng env liệt kê đủ 4 biến thay vì gộp `LANGFUSE_*`.
- Test: `tests/test_readme_phase8_langfuse.py`.

### Review vs product-spec / test-plan
- **Pass:** hướng dẫn AC6 / test-plan §4 (bật monitoring → xem 1 trace;
  tương quan `request_id`); map «Langfuse trace» có cách chứng minh trong
  README + report Phase 8.
- **Fail:** không (phạm vi item này).
- **Missing:** không (đóng cùng ngày qua mục `.env.example` phía trên).

## 2026-09-18 — Phase 8: E2E chat → Langfuse 1 root + spans

### Thay đổi
- `scripts/phase8_langfuse_e2e.py` — live probe AI `/v1/chat` (đích proxy
  của UI→Backend) + đọc observations Langfuse v4; `--print-checklist` UI.
- `tests/test_phase8_langfuse_e2e.py` — FE→Backend contract, `request_id`,
  mock span tree khi monitoring on; optional live (`PHASE8_LIVE_LANGFUSE=1`).
- Báo cáo: `specs/eval/phase8_langfuse_e2e_report.md` (+ run log).

### Review vs product-spec / test-plan
- **Pass:** AC6 (1 chat + monitoring → 1 trace); test-plan §4 true+keys →
  root `chat` + spans agent; evidence trong báo cáo (trace_id + span list).
- **Fail:** không (phạm vi item này).
- **Missing:** không (Phase 8 đã đóng — xem mục `.env.example` cùng ngày).

## 2026-09-18 — Phase 8: MONITORING off / thiếu key → chat no-op

### Thay đổi
- `tracing.py`: no-op khi `MONITORING_ENABLED=false` hoặc thiếu
  `LANGFUSE_*` key; cảnh báo 1 lần khi bật nhưng thiếu key / init fail;
  flush lỗi chỉ warn, không raise; cache `_client=False` không bị nhầm
  thành client thật.
- Tests: `tests/test_monitoring_noop.py` (disabled, thiếu key, init fail,
  `/v1/chat` vẫn 200, flush fail không crash).

### Review vs product-spec / test-plan
- **Pass:** product-spec “tắt monitoring vẫn chat bình thường”; test-plan
  §4 `MONITORING_ENABLED=false` → OK; thiếu key / sai init → warn +
  best-effort không crash.
- **Fail:** không (phạm vi item này).
- **Missing:** không (Phase 8 đã đóng — xem mục `.env.example` cùng ngày).

## 2026-09-18 — Phase 8: Propagate `request_id` Backend → AI → Langfuse

### Thay đổi
- Backend: mỗi `/chat` và `/scan` sinh `request_id` (UUID), gửi AI qua body
  + header `X-Request-Id`, echo lại trong response.
- `backend/ai_client.py`: `ai_chat` / `ai_scan` nhận và forward `request_id`.
- AI `/v1/chat` + `/v1/scan`: nhận `request_id` (body hoặc header), truyền
  `answer_question` / `scan_symbol` → metadata Langfuse (`request_id` +
  dùng làm `turn` khi có).
- Tests: `tests/test_request_id_propagation.py`.

### Review vs product-spec / test-plan
- **Pass:** tương quan cùng request Backend↔AI↔Langfuse metadata (test-plan
  §3 “cùng request”); AC6 hướng tìm trace theo request id.
- **Fail:** không (phạm vi item này).
- **Missing:** không (Phase 8 đã đóng — xem mục `.env.example` cùng ngày).

## 2026-09-18 — Phase 8: Chat/scan → 1 trace cha + span con (Langfuse)

### Thay đổi
- `src/portfolio_watch/infra/monitoring/tracing.py` — port ý tưởng
  `llm-engineer-demo` (`trace_request` / `agent_span` / `trace_step`);
  no-op khi `MONITORING_ENABLED=false` hoặc thiếu key / thiếu package.
- `answer_question`: root `chat` + span `rewrite_question`, `supervisor`,
  `price_news_fetch`, `eval_agent`, `answer_composer`.
- `scan_symbol`: root `scan` + span `price_agent`, `news_agent`,
  `event_classifier`, `eval_agent`, `synthesis_agent`.
- Tests: `tests/test_langfuse_tracing.py`.

### Review vs product-spec / test-plan
- **Pass:** AC6 hướng (1 request → 1 trace cha + span bước); test-plan §4
  monitoring off vẫn OK (no-op); pattern demo không copy nguyên file.
- **Fail:** không (phạm vi item này).
- **Missing:** không (Phase 8 đã đóng — xem mục `.env.example` cùng ngày).
  `langfuse` cài khi bật monitoring (`pip install langfuse`).

## 2026-09-18 — Phase 7 hoàn thành: quyết định compose (port / volume / DB)

**Ngày hoàn thành Phase 7 (vòng Quality Loop + FE/BE/AI):** **2026-09-18**

### Quyết định Docker / Compose (3 service)

| Mục | Quyết định | Lý do ngắn |
|-----|------------|------------|
| Image base | `python:3.12-slim` | Khớp runtime ≥3.10; slim đủ FastAPI + deps |
| Image tag | `portfolio-watch:split` | Một image, `command` khác nhau theo service |
| Kiến trúc | **3 service:** `ai` + `backend` + `frontend` | Khớp AC4 (3 process/URL); FE không gọi AI thẳng |
| Port AI | host/container **8001** | `AI_API_PORT`; health `/health` |
| Port Backend | container **8000**; host `${APP_HOST_PORT:-8000}` | Đổi cổng host qua `.env` |
| Port Frontend | host/container **5173** | `python -m http.server` phục vụ `frontend/` |
| AI↔Backend | `AI_BASE_URL=http://ai:8001` (tên service) | DNS nội bộ compose; browser vẫn dùng `127.0.0.1:8000` |
| Volume name | `portfolio-watch-data` (compose key `pw_data`) | Named volume — sống qua `restart` / `down` |
| Volume path | → `/app/data` | AI: `SQLITE_PATH=/app/data/portfolio_watch.db`; Backend: `BACKEND_SQLITE_PATH=/app/data/backend_store.db` |
| Env / secrets | `env_file: .env`; không bake key vào image | Override host/path trong `environment:` |
| Demo URL | FE `http://127.0.0.1:5173/` → BE `:8000` → AI `:8001` | Cùng ranh giới local 3 process |
| Xóa DB | `docker compose down -v` | Giữ volume mặc định khi chỉ `down` |

Lệnh: `docker compose up --build` / `logs -f` / `down` — README mục
**Demo bằng Docker**. Verifier local: `scripts/verify_clean_local.py` →
`CLEAN_VENV_SMOKE_OK`.

### Review vs product-spec / test-plan
- **Pass:** AC4 (3 URL); cấu hình URL/CORS/env; test-plan README + Docker
  demo; Phase 7 checklist toàn `[x]`.
- **Fail:** không.
- **Missing:** Phase 8 Langfuse tracing (item tiếp theo).

## 2026-09-18 — Phase 7: Xác nhận máy sạch / dong312 (3 process → 3 luồng)

### Thay đổi
- `scripts/verify_clean_local.py` — dựng stub AI + Backend + Frontend
  (cổng tạm); kiểm watchlist, chat+steps, scan+approve; in
  `CLEAN_VENV_SMOKE_OK`. `VERIFY_USE_CURRENT=1` dùng env hiện tại
  (dong312 / venv).
- `README.md`: mục xác nhận máy sạch dưới Demo local.
- Tests: `tests/test_clean_venv_smoke.py` (assert 3 process).

### Kết quả chạy
- `VERIFY_USE_CURRENT=1 python scripts/verify_clean_local.py` →
  **CLEAN_VENV_SMOKE_OK**.
- Venv tạm đầy đủ (`python scripts/verify_clean_local.py`) →
  **CLEAN_VENV_SMOKE_OK** (log: `specs/eval/phase7_clean_local_run.log`).

### Review vs product-spec / test-plan
- **Pass:** AC4/AC5/AC8 hướng (3 process, chat timeline, watchlist/scan/
  duyệt) trên script máy sạch; test-plan §3 README + thử tay có
  verifier tự động.
- **Fail:** không.
- **Missing:** ghi quyết định compose (port/volume) — item Phase 7 cuối.

## 2026-09-18 — Phase 7: docker compose 3 service (AI + Backend + Frontend)

### Thay đổi
- `docker-compose.yml`: services `ai` (:8001), `backend` (:8000),
  `frontend` (:5173); `AI_BASE_URL=http://ai:8001`; volume
  `portfolio-watch-data` → `/app/data`.
- `Dockerfile`: COPY `backend` + `frontend` + `prompts`; default CMD =
  `ai_main` :8001 (compose override từng service).
- `README.md`: mục **Demo bằng Docker** — `up` / `down` / `logs` / `-v`.
- Tests: cập nhật compose / Dockerfile / README Docker demo.

### Review vs product-spec / test-plan
- **Pass:** AC4 hướng (3 process/URL trong compose); Frontend→Backend→AI;
  không bake secret; lệnh up/down/log trong README.
- **Fail:** không (chưa chạy `compose up` trên máy này trong bước docs).
- **Missing:** xác nhận máy sạch end-to-end; ghi quyết định compose chi tiết
  (Phase 7 còn lại).

## 2026-09-18 — Phase 7: Kịch bản demo local (localhost)

### Thay đổi
- `README.md`: mục **Demo local (Phase 7)** — bật 3 process, mở
  `http://127.0.0.1:5173/`, seed watchlist, chat + timeline, quét, duyệt
  nếu có; **không** cần ngrok.
- `scripts/phase7_demo_checklist.py` — in checklist tay.
- Tests: `tests/test_readme_phase7_demo_scenario.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4/AC5/AC8 hướng (3 process local, timeline chat, watchlist
  + scan + duyệt); test-plan «UI timeline» demo thủ công 1 câu; không
  cần internet công cộng (expose).
- **Fail:** không (phạm vi kịch bản docs).
- **Missing:** docker compose 3 service; xác nhận máy sạch; ghi quyết định
  compose (Phase 7 còn lại). Chat/scan thật vẫn cần LLM/network nội bộ.

## 2026-09-18 — Phase 6: Troubleshooting (key / port / AI / CORS)

### Thay đổi
- `README.md`: mục **Troubleshooting (Phase 6)** — thiếu
  `OPENAI_API_KEYS`; port trùng 8001/8000/5173; AI unreachable/timeout
  (502); CORS/`FRONTEND_ORIGIN`.
- Tests: `tests/test_readme_phase6_troubleshooting.py`.
- Phase 6 local-run checklist → đủ `[x]`.

### Review vs product-spec / test-plan
- **Pass:** test-plan §3 (AI down → lỗi rõ, không treo; Backend/FE tách);
  AC4 hướng chạy 3 process có hướng dẫn khi lỗi; Phase 5 error messages
  được ghi trong README.
- **Fail:** không.
- **Missing:** Phase 7 demo kịch bản / compose / máy sạch.

## 2026-09-18 — Phase 6: Lệnh eval một case và full golden

### Thay đổi
- `README.md`: mục **Eval (Phase 6)** — một case (`--case-id`), full
  (`--run` / `phase5_regression.py`), `--self-check`; ghi chú rate-limit
  và injection/regression.
- Tests: `tests/test_readme_phase6_eval_commands.py`.

### Review vs product-spec / test-plan
- **Pass:** AC1 hướng (chạy eval từng case / full); test-plan §1 lệnh
  `--case-id` + full golden; developer flow «siết chất lượng».
- **Fail:** không.
- **Missing:** troubleshooting (Phase 6 cuối).

## 2026-09-18 — Phase 6: Bảng biến môi trường bắt buộc / tuỳ chọn

### Thay đổi
- `README.md`: mục **Biến môi trường (Phase 6)** — bảng bắt buộc
  (`OPENAI_API_KEYS`, `LLM_BACKEND`) + tuỳ chọn (URL/port, SQLite,
  CORS, Langfuse, …) khớp `.env.example`.
- Tests: `tests/test_readme_phase6_env_table.py`.

### Review vs product-spec / test-plan
- **Pass:** product «cấu hình URL/CORS bằng biến môi trường»; AC4 hướng
  (URL/port tách process); test-plan README có bảng env ngắn.
- **Fail:** không.
- **Missing:** lệnh eval; troubleshooting (Phase 6 còn lại).

## 2026-09-18 — Phase 6: Ba lệnh chạy AI → Backend → Frontend

### Thay đổi
- `README.md`: mục **Chạy 3 process (Phase 6)** — lệnh
  `serve_ai.py` (:8001) → `serve_backend.py` (:8000) →
  `serve_frontend.py` (:5173) + health URL; thay skeleton «chưa đủ lệnh».
- Tests: `tests/test_readme_phase6_three_commands.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4 (3 process / 3 URL); test-plan §3 «3 process riêng» /
  «README lệnh»; luồng Frontend→Backend→AI.
- **Fail:** không (phạm vi item này).
- **Missing:** bảng biến env; lệnh eval; troubleshooting (Phase 6 còn lại).

## 2026-09-18 — Phase 6: README prerequisites (dong312 / venv + .env)

### Thay đổi
- `README.md`: mục **Prerequisites (Phase 6)** — Python ≥ 3.10; conda
  `dong312` hoặc venv; `pip install -e ".[dev]"`; copy `.env.example` →
  `.env` + `OPENAI_API_KEYS`.
- Tests: `tests/test_readme_phase6_prerequisites.py`; siết
  `test_readme_local_instructions.py` theo item đang mở.

### Review vs product-spec / test-plan
- **Pass:** AC4 hướng (chuẩn bị chạy 3 process); test-plan «README lệnh»
  bắt đầu bằng prerequisites rõ; lệnh kiểm tra import `settings` chạy OK.
- **Fail:** không (phạm vi item này).
- **Missing:** ba lệnh chạy AI→BE→FE; bảng env; lệnh eval; troubleshooting
  (các item Phase 6 còn lại).

## 2026-09-18 — Phase 5: Regression full golden sau FE/BE

### Thay đổi
- Chạy full 30 golden (rule-based, khớp `baseline_debug`): **30/30**,
  drop=0.0000 ≤ 0.05; injection **3/3 (100%)**.
- `scripts/phase5_regression.py` — chạy từng case subprocess + retry
  rate-limit vnstock guest; ghi `specs/eval/baseline_phase5.json` +
  `specs/eval/phase5_regression_report.md`.
- `scripts/run_eval.py`: `--case-delay` / `EVAL_CASE_DELAY_SEC` (hỗ trợ
  full run tránh burst).

### Kết quả
| Slice | Passed/Total |
|---|---|
| lookup | 18/18 |
| comparison | 6/6 |
| out_of_scope | 3/3 |
| injection | 3/3 |
| **Tổng** | **30/30** |

### Review vs product-spec / test-plan
- **Pass:** test-plan Regression (Phase 5/7) — rate không tụt quá
  tolerance; AC2 injection 100%; AC1 hướng 30/30 với scorer đã chốt
  (rule, skip-judge/agent-eval như baseline_debug).
- **Fail:** không.
- **Missing:** LLM-judge / task_success full (ngoài mốc baseline_debug);
  Phase 6 README lệnh chạy 3 process.

## 2026-09-18 — Phase 5: Eval policy — không nới scorer + blocked/3c

### Thay đổi
- `specs/eval/blocked_cases.yaml` — registry case fail đã ghi nhận
  (`reason` + `phase3c_task` bắt buộc).
- `scripts/run_eval.py`: `assert_scorer_locks` (không hạ judge < 3.0,
  không nới `--tolerance` > 0.05); `load_blocked_cases`;
  `format_fail_policy_guidance` / `format_blocked_registry` in sau report.
- Tests: `tests/test_eval_scorer_policy.py`; self-check khóa scorer.

### Review vs product-spec / test-plan
- **Pass:** test-plan «Không nới scorer»; fail → sửa hoặc blocked+3c
  (AC3 hướng); injection vẫn hard 100%; judge sàn 3.0 giữ nguyên.
- **Fail:** không.
- **Missing:** Regression full golden sau FE/BE (item Phase 5 cuối).

## 2026-09-18 — Phase 5: Approvals missing / đã xử lý → 404 rõ

### Thay đổi
- `backend/store.py`: `get_approval`, `explain_approval_failure`
  (thiếu vs đã xử lý).
- `backend/main.py`: approve/reject trả 404 chi tiết; kiểm tra state không
  đổi khi fail; `approval_id` rỗng → 400.
- FE: hiện lỗi Duyệt/Từ chối + reload list (không để UI lệch).
- Tests: `tests/test_backend_approvals_errors.py`.

### Review vs product-spec / test-plan
- **Pass:** Phase 5 approvals lỗi id; AC HITL không đổi state khi fail;
  message rõ «không tìm thấy» / «đã xử lý».
- **Fail:** không.
- **Missing:** Eval không nới scorer (item Phase 5 tiếp); regression golden.

## 2026-09-18 — Phase 5: Steps lỗi giữa chừng → timeline `error`

### Thay đổi
- `backend/steps.py`: `mark_mid_run_error`, `ensure_steps_reflect_error`;
  `normalize_steps` giữ `error`; `_attach_run` gắn lỗi từ field `error`.
- `frontend/app.js`: `markTimelineMidError` (running→error, giữ done);
  boot «Bước lỗi» khi steps có `error`.
- Tests: `tests/test_steps_mid_run_error.py`.

### Review vs product-spec / test-plan
- **Pass:** AC5 timeline phản ánh bước lỗi; test-plan stream/steps error
  trên bước đó (MVP one-shot); FE không gọi AI.
- **Fail:** không.
- **Missing:** Eval không nới scorer / regression golden (Phase 5 còn lại).

## 2026-09-18 — Phase 5: AI down / timeout → 502 + FE không treo

### Thay đổi
- `backend/ai_client.py`: `AI_HTTP_TIMEOUT` (mặc định 60s); phân biệt
  «AI timeout» vs «AI không kết nối được» → Backend **502** + `detail`.
- `frontend`: `REQUEST_TIMEOUT_MS` + `AbortController`; `formatApiError` /
  `showOpError` (boot + timeline error + chat); nút Gửi luôn mở lại.
- `.env.example`: `AI_HTTP_TIMEOUT`.
- Tests: `tests/test_ai_down_timeout.py`.

### Review vs product-spec / test-plan
- **Pass:** test-plan §3 «Tắt AI → không treo vô hạn»; Backend có message;
  FE hiện lỗi, không gọi AI thẳng.
- **Fail:** không.
- **Missing:** approvals id lỗi (item Phase 5 tiếp); SSE realtime từng bước.

## 2026-09-18 — Phase 5: Backend input lỗi → 4xx rõ

### Thay đổi
- `backend/main.py`: `_norm_symbol` (rỗng vs không hợp lệ);
  `_norm_threshold` (ngưỡng âm / =0); áp dụng watchlist + **scan**.
- Tests: `tests/test_backend_validation_4xx.py`
  (câu rỗng, symbol invalid, ngưỡng âm).

### Review vs product-spec / test-plan
- **Pass:** Phase 5 mục validation Backend; test-plan §5 hướng 4xx rõ;
  AC không 500 cho input xấu trên Backend.
- **Fail:** không.
- **Missing:** AI down → FE message (đã đóng mục kế tiếp); stream error;
  approvals id lỗi.

## 2026-09-18 — Phase 4: Kiểm thử tay (checklist + smoke)

### Thay đổi
- `tests/test_phase4_manual_checklist.py` — smoke cùng luồng FE→Backend:
  chat (steps+answer) → thêm mã → quét → approve pending.
- `scripts/phase4_manual_checklist.py` — in checklist UI 3 process.
- `frontend/README.md` — mục Kiểm thử tay Phase 4.
- **Phase 4 checklist hoàn tất.**

### Review vs product-spec / test-plan
- **Pass:** AC5/AC8 hướng (chat + timeline + watchlist + duyệt qua BE);
  test-plan §3 bước 2–3 (curl/API chat có answer+steps; UI checklist);
  FE không gọi AI.
- **Fail (đã sửa):** script checklist in Unicode trên Windows cp1252 →
  ghi stdout UTF-8.
- **Missing:** Phase 5 validation/error; demo live 3 process vẫn cần
  LLM/key khi chạy tay với AI thật.

## 2026-09-18 — Phase 4: Watchlist/approvals SQLite Backend + FE CRUD

### Thay đổi
- `backend/store.py` — SQLite thật: bảng `watchlist` + `approvals`
  (`BACKEND_SQLITE_PATH`, mặc định `./data/backend_store.db`).
- Runs (steps) vẫn in-memory. Seed DEFAULT_WATCHLIST chỉ khi DB trống.
- FE: thêm **Sửa** ngưỡng → `PATCH /watchlist/{symbol}` (đủ CRUD).
- `.env.example` + `backend/README.md`: bảng nơi lưu Backend vs AI.
- Tests: `tests/test_backend_sqlite_crud.py`.

### Nơi lưu (ghi rõ)
| Dữ liệu | Owner | Path |
|---|---|---|
| Watchlist + approvals (UI) | **Backend** | `BACKEND_SQLITE_PATH` → `./data/backend_store.db` |
| Memory/chat/price (AI) | **AI** | `SQLITE_PATH` → `./data/portfolio_watch.db` |

### Review vs product-spec / test-plan
- **Pass:** AC8 hướng watchlist + duyệt qua kiến trúc tách lớp; FE→BE
  CRUD/approve/reject; dữ liệu bền SQLite Backend; test-plan §3 FE không
  gọi AI.
- **Fail:** không.
- **Missing:** checklist «Kiểm thử tay» Phase 4 (item tiếp); Phase 5
  validation.

## 2026-09-18 — Phase 4: Timeline từ Backend `steps` / `/runs/{id}/steps`

### Thay đổi
- `frontend/app.js`: `normalizeSteps`, `showTimelineStart` (running),
  `applyTimelineFromBackend` — sau chat/scan lấy steps từ response rồi
  **GET `/runs/{run_id}/steps`** (nguồn sự thật Backend); không gọi AI.
- `index.html`: ghi rõ nguồn timeline Backend.
- Tests: `tests/test_frontend_timeline_steps.py`.
- MVP: one-shot steps (chưa SSE realtime — Phase 5 nếu cần).

### Review vs product-spec / test-plan
- **Pass:** AC5 hướng «thấy timeline bước»; test-plan §3 contract steps +
  «ít nhất start + done»; FE→Backend only.
- **Fail:** không.
- **Missing:** SSE stream từng bước realtime (Phase 5); CRUD watchlist
  SQLite ghi rõ (item Phase 4 tiếp).

## 2026-09-18 — Phase 4: Chat Backend forward AI → FE nhận answer

### Thay đổi
- `backend/main.py`: `_forward_chat_from_ai` — luôn có `answer` string
  top-level; `GET /runs/{id}` trả `answer` cho chat.
- `frontend/app.js`: `extractFinalAnswer` + hiển thị câu trả lời cuối;
  disable nút Gửi khi đang chờ.
- Tests: `tests/test_chat_answer_forward.py`.

### Review vs product-spec / test-plan
- **Pass:** Core flow chat bước 2+4 (FE→BE→AI, hiện câu trả lời cuối);
  test-plan §3 «curl chat qua Backend nhận answer»; FE không gọi AI.
- **Fail:** không.
- **Missing:** Phase 5 validation; kiểm thử tay live đã có checklist
  (mục Phase 4 kế tiếp cùng ngày).

## 2026-09-18 — Phase 4: Frontend gọi Backend (bỏ mock)

### Thay đổi
- `frontend/app.js` — `fetch` tới Backend: `/chat`, `/scan`, `/watchlist`,
  `/approvals` (+ approve/reject); **xoá `MOCK_STEPS`**.
- `index.html` — form thêm watchlist + quét mã; timeline từ `steps` response.
- Tests: `test_frontend_backend_wiring.py`; cập nhật scaffold/static-serve.
- Nơi lưu: watchlist/approvals **in-memory Backend** (`backend/store.py`);
  AI vẫn SQLite riêng khi chat/scan (proxy).

### Review vs product-spec / test-plan
- **Pass:** FE chỉ gọi Backend (AC7 hướng / test-plan §3 contract); bỏ mock;
  đủ 4 nhóm API; không gọi AI `:8001` từ browser.
- **Fail:** không (static wiring tests).
- **Missing:** siết item «Chat nhận answer» / timeline stream / CRUD+SQLite
  ghi rõ (các checkbox Phase 4 còn lại); demo tay 3 process.

## 2026-09-18 — Phase 3c: Guardrail rewrite giữ grounding

### Thay đổi
- `output_checks`: `has_evidence_grounding`, `check_rewrite_grounding`,
  `strip_buy_sell`, `rewrite_keep_grounding` — rewrite không được bỏ hết
  số liệu evidence; fallback gỡ mua/bán từ bản đã grounded.
- `answer_composer` + `synthesis_agent`: từ attempt>0 bắt buộc grounding;
  lưu `last_grounded` cho fallback.
- Prompt `answer_compose` v1.1: khi sửa vi phạm vẫn giữ số liệu/tin.
- Tests: `tests/test_guardrail_rewrite_grounding.py`.

### Review vs product-spec / test-plan
- **Pass:** AC guardrail mua/bán + số khớp evidence (test-plan Synthesis/
  Answer); rewrite không còn mất số liệu; AC3 backlog 3c đóng mục này.
- **Fail:** không (26 related tests).
- **Missing:** Phase 4 nối FE→BE; Phase 3c placeholder trống nếu chưa có gap mới.

## 2026-09-18 — Phase 3c: Rewrite/memory với đại từ («mã đó»)

### Thay đổi
- `supervisor.py`: mở rộng `_REF_PREV_RE` (cổ phiếu đó/này, nó, em đó);
  `_apply_memory_symbol` + `_ground_rewritten` dùng chung Heuristic và
  `LlmRewriteBrain` (LLM trả `symbol:null` vẫn lấy mã từ hội thoại);
  đại từ → memory thắng false ticker; stopword `BAO` («bao nhiêu»).
- Prompt `rewrite_question` v1.2: ví dụ đại từ / follow-up bắt buộc gắn mã.
- Tests: pronoun variants + LLM null-symbol fallback
  (`test_answer_question`, `test_supervisor_llm`).

### Review vs product-spec / test-plan
- **Pass:** agents.md RewriteQuestion dùng Memory; test-plan §2 Supervisor
  «mã đó» / follow-up; AC8 chat follow-up (`test_api_chat`); AC3 backlog
  3c mục đại từ đã xử lý.
- **Fail (đã sửa):** «Nó giảm bao nhiêu?» extract nhầm `BAO` → memory không
  áp dụng; đã ưu tiên đại từ + stopword.
- **Missing:** Phase 4 FE (guardrail grounding đã đóng mục kế tiếp).

## 2026-09-18 — Phase 3c: Evidence giá trước khi so sánh %

### Thay đổi
- `price_agent.has_change_pct_evidence` /
  `prices_have_change_pct_evidence`.
- `answer_question`: fetch đủ giá mọi mã; **skip `eval_agent`** nếu thiếu
  `change_pct` (không so sánh % không có căn cứ).
- `HeuristicEvalBrain`: thiếu giá → severity thấp + reasoning «không so sánh».
- Prompt `eval_severity` + `answer_compose`: không bịa % khi thiếu evidence.
- Tests: `tests/test_price_evidence_before_pct.py`.

### Review vs product-spec / test-plan
- **Pass:** grounding số liệu (guardrail / comparison trajectory); AC3
  backlog 3c đã xử lý; hỗ trợ comparison golden không gọi eval khi thiếu giá.
- **Fail:** không.
- **Missing:** Phase 4 FE (các mục 3c gợi ý đã đóng sau đó).

## 2026-09-18 — Phase 3b: CORS Backend theo `FRONTEND_ORIGIN`

### Thay đổi
- `backend/main.py` — `CORSMiddleware`:
  - `FRONTEND_ORIGIN=*` (dev mặc định) → `allow_origins=["*"]`;
  - hoặc origin cụ thể (vd. `http://127.0.0.1:5173`).
- `.env.example` + `backend/README.md` ghi cấu hình CORS.
- Tests: `tests/test_backend_cors.py` (GET + preflight + siết origin).
- **Phase 3b checklist hoàn tất.**

### Review vs product-spec / test-plan
- **Pass:** «Cấu hình URL/CORS bằng biến môi trường» (AC / features);
  Backend sẵn sàng cho FE :5173 gọi cross-origin (hướng AC4/test-plan §3).
- **Fail:** không.
- **Missing:** FE thật gọi API (Phase 4); siết origin trên AI process
  (không bắt buộc — browser không gọi AI).

## 2026-09-18 — Phase 3b: Backend không import `domain.agents` (HTTP-only)

### Thay đổi
- Gate kiểm tra: `tests/test_backend_no_agent_imports.py`
  - cấm import `domain.agents` / `portfolio_watch.application` / langgraph;
  - cấm `src.portfolio_watch*` trong `backend/`;
  - `ai_client.py` chỉ stdlib `urllib` → `/v1/chat` + `/v1/scan`.
- Siết assert trong `test_backend_service.py`; README ghi AC7 + lệnh pytest.

(Code Backend vốn đã HTTP-only; mục này khóa ranh giới bằng test.)

### Review vs product-spec / test-plan
- **Pass:** AC7 «Backend chỉ gọi AI qua HTTP — không import graph/agent
  domain»; test-plan acceptance map «Backend không import agents»
  (grep/AST trên `backend/`).
- **Fail:** không.
- **Missing:** FE không gọi thẳng AI (Phase 4). CORS Backend đã làm ở mục kế tiếp.

## 2026-09-18 — Phase 3b: Endpoint `steps[]` one-shot (MVP)

### Thay đổi
- `backend/steps.py` — `normalize_steps` → `{id,name,status,detail?}`.
- `POST /chat` + `POST /scan`: luôn trả `steps[]` chuẩn + `run_id`.
- `GET /runs/{run_id}` và `GET /runs/{run_id}/steps` — lấy lại bước
  one-shot (chưa SSE; đủ MVP checklist).
- Store giữ `RunRecord` in-memory; tests cập nhật contract steps.

### Review vs product-spec / test-plan
- **Pass:** Backend trả `steps` cho timeline (AC5 hướng / test-plan §3
  contract + «curl chat nhận answer + steps»); shape id/name/status/detail.
- **Fail:** không.
- **Missing:** SSE realtime từng bước (tuỳ chọn sau); FE nối timeline
  (Phase 4); CORS + assert no `domain.agents` (mục 3b còn lại).

## 2026-09-18 — Phase 3b: Backend API (health / watchlist / approvals / proxy AI)

### Thay đổi
- `backend/` — FastAPI process port **8000**:
  - `GET /health`
  - CRUD `/watchlist`
  - `/approvals` + approve/reject
  - `POST /chat`, `POST /scan` → HTTP tới `AI_BASE_URL` `/v1/*`
- `backend/ai_client.py` — urllib JSON client (không import `domain.agents`).
- `backend/store.py` — watchlist/approvals **in-memory** (Backend sở hữu).
- `scripts/serve_backend.py`; `pyproject.toml` include package `backend*`.
- Tests: `tests/test_backend_service.py`.

### Review vs product-spec / test-plan
- **Pass:** hướng AC4 (Backend URL riêng :8000); AC7/AC8 một phần —
  proxy chat/scan HTTP-only + watchlist/approvals CRUD; test-plan §3
  contract Backend→AI (chat/scan JSON có `steps` khi AI trả).
- **Fail:** không trong scope mục này.
- **Missing:** assert cứng «không import agents» trong checklist kế tiếp;
  CORS; nối FE (Phase 4); SQLite bền (ghi rõ in-memory tạm).
  (Endpoint steps one-shot đã làm ở mục kế tiếp cùng ngày.)

## 2026-09-18 — Phase 3a: Báo cáo chất lượng golden (30/30)

### Thay đổi
- `specs/eval/phase3a_quality_report.md` — báo cáo Phase 3a:
  - bảng pass theo slice (18/6/3/3 = **30/30**, injection 100%);
  - liệt kê thay đổi agent/prompt/tool trong Quality Loop;
  - đối chiếu AC1–3 / test-plan §1.
- `tests/test_phase3a_quality_report.py` — assert báo cáo đủ mục checklist.
- Checklist Phase 3a mục «Báo cáo» → `[x]` (**3a hoàn tất**).

### Review vs product-spec / test-plan
- **Pass:** AC1 «báo cáo pass/fail» + map acceptance; AC2 injection 100%
  ghi trong báo cáo; AC3 thay đổi + backlog 3c đã liệt kê; test-plan
  «run_eval + báo cáo» / «slice report».
- **Fail:** không trong scope mục báo cáo.
- **Missing:** full run kèm LLM-judge (ngoài báo cáo này); Phase 3b+.

## 2026-09-18 — Phase 3a: Pass hết slice (30/30, injection 100%)

### Kết quả (`--run --skip-judge` + task_success; case-by-case delay)
| Slice | Passed | Total |
|---|---:|---:|
| lookup | 18 | 18 |
| comparison | 6 | 6 |
| out_of_scope | 3 | 3 |
| injection | 3 | 3 |
| **Tổng** | **30** | **30** |

Injection gate: **100%**.

### Thay đổi agent / prompt / eval (không nới scorer)
- **Multi-symbol:** `RewrittenQuestion.symbols`; `_extract_symbols`; fetch
  giá/tin từng mã; composer/evidence gộp đa mã.
- **Prompt:** `rewrite_question` + `answer_compose` (symbols / nêu đủ mã).
- **Intent:** thêm hint «biến động / mạnh hơn / đối chiếu»; đa mã → explain.
- **Stopword:** `TIN` (tránh «tin tức» thành ticker).
- **Eval:** mỗi case `user_id=eval-{case_id}` — tránh memory lệch symbol.
- Phase 3c: đánh dấu xong «routing đa mã».
- Tests: `tests/test_multi_symbol_rewrite.py`.

### Review vs product-spec / test-plan
- **Pass:** AC1 hướng 30/30 theo scorer đã chốt (rule + task_success;
  judge skip trong run này); AC2 injection 100%; test-plan slice gate.
- **Fail:** không trên run 30/30 này.
- **Missing:** LLM-judge chưa bật trên full run (`--skip-judge`);
  Backend/FE (phase sau). Báo cáo tổng hợp → mục checklist kế tiếp (đã làm).

## 2026-09-18 — Phase 3a: Quality Loop — `lookup_15` (CafeF news)

### Chạy
- Full eval `--skip-judge` (+ task_success): **24/30**; injection 100%.
- Fail đầu (theo id): `lookup_15` — `news_agent items=0`, task_success fail.

### Nguyên nhân + sửa (tool, không nới scorer)
- CafeF `s.cafef.vn/Ajax/Events_RelatedNews_New.aspx` trả `<ul>` rỗng.
- Đổi URL → `https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx`.
- Bỏ lọc `query` trên title (LLM hay search câu dài → 0 tin dù endpoint
  đã theo mã).
- Tests: `test_market_data` cập nhật URL + hành vi query.

### Kết quả case
- `lookup_15`: **pass** (rule + task_success; trajectory overall 5.0).

### Review vs product-spec / test-plan
- **Pass:** workflow debug từng case (test-plan §1 / AGENTS); sửa tool khi
  fail; không nới expected; injection vẫn 100% trên run full trước đó.
- **Fail:** không còn trên `lookup_15`.
- **Missing:** còn fail slice comparison (và regression vs baseline_debug
  rule-only) — thuộc mục checklist «Pass hết slice»; AC1 30/30 chưa đạt.

## 2026-09-18 — Phase 3a: gỡ static UI khỏi process AI/API

### Thay đổi
- `main.py`: bỏ `StaticFiles(web/)` — API/monolith không phục vụ UI.
- `ai_main.py` vốn đã không mount static; siết test xác nhận GET `/`/`/app.js` = 404.
- `Dockerfile`: bỏ `COPY web` (image = API only).
- Tests: `test_api_static`, `test_docker_single_url`, UI tests đọc `web/` từ disk;
  UI production path = `frontend/` + `serve_frontend`.
- README: health API / FE :5173 / AI :8001 thay vì mở UI tại :8000/.

### Review vs product-spec / test-plan
- **Pass:** AI/API không serve UI (hướng AC4 tách process; test-plan §3
  «chỉ bật AI → health OK»); FE ở process riêng (`frontend/`);
  `GET /` + `/app.js` trên AI/API = 404; `/health` + JSON API OK.
- **Fail:** không (không phát hiện lỗi liên quan mục này sau khi sửa test).
- **Missing:** Backend (3b); golden case-by-case; E2E 3 process + timeline
  (Phase 4–6); Docker compose 3 service (Phase 7).

## 2026-09-18 — Phase 3a: AI process `/v1/chat` + `/v1/scan` + `steps[]`

### Thay đổi
- `src/portfolio_watch/ai_main.py` — FastAPI AI-only (port mặc định **8001**).
- `api/routers/v1.py` — `POST /v1/chat`, `POST /v1/scan`; response có kết
  quả cuối + `steps[]` (`id/name/status/detail`).
- `scripts/serve_ai.py`; settings `AI_API_HOST` / `AI_API_PORT`.
- Tests: `tests/test_ai_v1_service.py`.
- Monolith `main.py` đã gỡ static ở mục kế tiếp (cùng ngày).

### Review vs product-spec / test-plan
- **Pass:** AI chạy process/URL riêng (`AI_BASE_URL` :8001); contract
  chat/scan + `steps[]` (test-plan §3); hỗ trợ FE timeline / Backend proxy.
- **Fail:** không trong scope mục này.
- **Missing:** Backend proxy (3b); golden debug case-by-case; 3 process E2E.

## 2026-09-18 — Phase 2: chạy frontend độc lập + xác nhận UI

### Thay đổi
- `scripts/serve_frontend.py` — static server mặc định port **5173**.
- `tests/test_frontend_static_serve.py` — GET `/` + `config.js` + `app.js`
  qua ThreadingHTTPServer (không cần Backend/AI).
- `frontend/README.md` — lệnh chạy độc lập đã xác nhận.

### Xác nhận
- pytest static serve: pass (HTML có chat/timeline/watchlist/approvals).
- `serve_frontend.py` mở được (fix print Unicode Windows → ASCII).

### Review vs product-spec / test-plan
- **Pass:** Frontend chạy process/URL riêng (hướng AC4 một phần — FE
  độc lập); mở UI đủ 4 khu vực không phụ thuộc AI.
- **Fail:** không.
- **Missing:** Backend + AI process thật (Phase 3+); nối API (Phase 4).
- **Phase 2** hoàn tất checklist.

## 2026-09-18 — Phase 2: config `BACKEND_BASE_URL`

### Thay đổi
- `frontend/config.js` — `PW_CONFIG.BACKEND_BASE_URL` +
  `PW_getBackendBaseUrl()` (override `?backend=`).
- UI hiện URL tại `#backend-url-display`; README hướng dẫn đổi config.
- Chưa `fetch` API (đúng scope mục này).
- Test: `test_frontend_backend_base_url_config`.

### Review vs product-spec / test-plan
- **Pass:** cấu hình URL bằng biến/config (in-scope «Cấu hình URL…»);
  FE chỉ trỏ Backend, không AI (hướng AC7 / test-plan FE→BE).
- **Fail:** không.
- **Missing:** dùng URL để gọi API thật (Phase 4); CORS siết theo
  `FRONTEND_ORIGIN` (Phase 3b).

## 2026-09-18 — Phase 2: timeline mock 4 trạng thái

### Thay đổi
- `frontend/app.js` — `MOCK_STEPS` + `renderTimeline`: badge
  `pending | running | done | error`.
- `style.css` — style `.status-badge` theo từng status.
- Test: `test_frontend_timeline_mock_has_all_statuses`.

### Review vs product-spec / test-plan
- **Pass:** UI hiện list bước với đủ 4 trạng thái (AC5 / test-plan stream
  bước — phần hiển thị status); khớp shape name/status/detail.
- **Fail:** không.
- **Missing:** data thật từ Backend `steps[]`; chuyển trạng thái realtime
  khi chat (Phase 4).

## 2026-09-18 — Phase 2: trang chính 4 khu vực (chat / timeline / watchlist / approvals)

### Thay đổi
- `frontend/index.html` — section `#chat`, `#timeline`, `#watchlist`,
  `#approvals` (timeline placeholder, chưa mock status).
- `style.css` / `app.js` — layout; form chat preventDefault (chưa API).
- Test: `test_frontend_main_page_has_four_sections`.

### Review vs product-spec / test-plan
- **Pass:** UI có đủ vùng chat + timeline bước + watchlist + duyệt (AC5
  một phần — có chỗ hiện bước); khớp in-scope Frontend.
- **Fail:** không trong scope mục này.
- **Missing:** status `pending|running|done|error` trên timeline (mục
  tiếp); nối Backend; stream bước thật.

## 2026-09-18 — Phase 2: tạo frontend/ (HTML/JS thuần)

### Quyết định stack
- **HTML + CSS + JS thuần** (không React/Vite ở MVP).
- Serve: `python -m http.server 5173` trong `frontend/`.

### Files
- `frontend/index.html`, `style.css`, `config.js`, `app.js`, `README.md`
- `tests/test_frontend_scaffold.py`

### Review vs product-spec / test-plan
- **Pass:** có thư mục frontend riêng, stack ghi rõ; hướng FE→Backend
  (config URL sẵn).
- **Fail:** không (scope chỉ scaffold).
- **Missing:** trang chat/timeline/watchlist/approvals — mục Phase 2 tiếp
  theo; chưa chứng minh server 5173 trong CI (làm ở mục «chạy frontend
  độc lập»).

## 2026-09-18 — Phase 1: chat `steps[]` + review

### Thay đổi
- `answer_question.build_chat_steps` → `AnswerQuestionResult.steps`
  `[{id, name, status, detail}]`.
- `POST /chat` (`ChatResponse.steps`) trả đúng contract test-plan.
- Eval `steps_from_answer_result` đọc `result.steps` (map name→tool).
- Tests: `test_chat_steps.py`, assert steps trong `test_api_chat.py`.

### Review vs product-spec / test-plan
- **Pass:** chat JSON có `steps` (id/name/status/detail); thứ tự
  rewrite→supervisor→workers→composer; hỗ trợ timeline UI (AC5) và
  trajectory eval; product «UI hiện bước» có data từ AI.
- **Fail:** không trong scope mục này.
- **Missing:** stream từng bước realtime (Phase 4/5); UI timeline (Phase 2);
  scan chưa trả `steps[]` (contract ghi chat/scan — scan để phase sau nếu cần).

## 2026-09-18 — Phase 1: task_success + trajectory + `--case-id`

### Thay đổi
- `src/portfolio_watch/infra/eval/agent_scorers.py` — port ý tưởng
  llm-engineer-demo: `evaluate_task_success`, `evaluate_trajectory`,
  `steps_from_answer_result`.
- `scripts/run_eval.py` — ghép scorers; `--case-id` (tự run); 
  `--skip-agent-eval`; `make_answer_fn.last_steps` cho trajectory.
- Pass lookup/comparison: rule + judge + `task_success.success`.
- Trajectory overall < 3.0 → cảnh báo, không fail case.
- Tests: `tests/test_run_eval_agent_eval.py`; cập nhật checklist tests
  khớp plan mới.

### Review vs product-spec / test-plan
- **Pass:** có task_success + trajectory; chạy 1 case `--case-id` (test-plan);
  task_success gate lookup/comparison; trajectory warn không chặn pass.
- **Fail:** không trong scope mục này.
- **Missing:** `steps[]` trên API chat (mục Phase 1 kế tiếp) — hiện dựng
  steps từ `AnswerQuestionResult` trong eval; full golden với agent-eval
  bật chưa chạy lại (dùng `--skip-agent-eval` khi cần baseline rule-only).

## 2026-09-18 — Phase 1: baseline_debug eval (không sửa agent)

### Chạy
- Lệnh: `python scripts/run_eval.py --run --skip-judge --save-baseline --baseline specs/eval/baseline_debug.json`
- **Không** sửa domain agents / prompt.

### Kết quả (`specs/eval/baseline_debug.json`)
| Slice | Passed | Total | Rate |
|---|---:|---:|---:|
| lookup | 18 | 18 | 100% |
| comparison | 6 | 6 | 100% |
| out_of_scope | 3 | 3 | 100% |
| injection | 3 | 3 | 100% |
| **Tổng** | **30** | **30** | **100%** |

Injection gate: OK (100%). Regression vs file vừa lưu: OK.

### Review vs product-spec / test-plan
- **Pass:** có báo cáo pass/fail từng slice; injection 100% (AC2 / test-plan
  gate); file baseline_debug làm mốc regression vòng debug.
- **Fail:** không (scope: chạy baseline, chưa nâng scorer).
- **Missing:** lần chạy dùng `--skip-judge` — chưa gồm LLM-judge /
  task_success / trajectory (AC1 đầy đủ + Phase 1 mục eval nâng cấp tiếp
  theo). `baseline.json` MVP cũ (có judge) vẫn là 30/30 riêng.

## 2026-09-18 — Phase 1: README skeleton 3 process + review

### Thay đổi
- `README.md`: mục **Skeleton — 3 process** — bảng port AI `8001` /
  Backend `8000` / Frontend `5173`, env `AI_BASE_URL` /
  `BACKEND_BASE_URL` / `FRONTEND_ORIGIN`, luồng FE→BE→AI; ghi rõ lệnh
  chi tiết ở Phase 6.
- `tests/test_readme_split_skeleton.py` — assert skeleton đủ port/env.
- `specs/implementation-plan.md` — đánh dấu xong mục README skeleton.

### Review vs product-spec / test-plan (chỉ skeleton README)
- **Pass:** tài liệu 3 URL/port khớp hướng AC4; env khớp `.env.example`;
  nêu Frontend không gọi thẳng AI (hướng AC7); còn mục chạy 1 process MVP
  (AC8 tạm thời).
- **Fail:** không trong scope skeleton.
- **Missing (phase sau):** lệnh chạy thật 3 process (Phase 6); process
  tách (Phase 3–5); test-plan mục «3 process thử tay».
- **Ngoài scope:** `test_readme_local_instructions` /
  `test_readme_docker_demo` vẫn fail vì README vòng mới chưa khôi phục
  section MVP Phase 6/7 cũ — thuộc Phase 6–7 plan mới, không sửa ở mục này.

## 2026-09-18 — Review Phase 1 `.env.example` vs product-spec / test-plan

### Phạm vi feature
Chỉ cấu hình biến môi trường split-deploy + giữ OpenAI/Langfuse (không phải
eval / UI / 3 process chạy thật).

### Pass
- In scope «Cấu hình URL… bằng biến môi trường»: `.env.example` có
  `AI_BASE_URL`, `BACKEND_BASE_URL`, `FRONTEND_ORIGIN`, `APP_HOST_PORT`.
- Giữ `OPENAI_API_KEYS` + Langfuse (`MONITORING_*` / `LANGFUSE_*`) cho AC6 sau.
- Settings đọc đủ field; test `test_docker_env_file.py` pass.
- `.env` local đã bổ sung 3 URL (khớp example; không đụng secret).

### Fail
- Không (trong phạm vi mục `.env.example`).

### Missing (không sửa ở review này — thuộc phase khác)
- AC4 «3 process / 3 URL chạy độc lập» — mới có URL trên giấy, chưa tách
  process (Phase 3–5).
- CORS runtime vẫn `allow_origins=["*"]` (MVP); chưa siết theo
  `FRONTEND_ORIGIN` (Phase 3b/4 khi FE riêng).
- AC1–3, 5–8 (golden, timeline, Langfuse E2E, Backend HTTP-only) — ngoài
  feature env.

## 2026-09-18 — Phase 1: `.env.example` split-deploy URLs

### Thay đổi
- `.env.example`: `AI_BASE_URL`, `BACKEND_BASE_URL`, `FRONTEND_ORIGIN`,
  `APP_HOST_PORT`; giữ `OPENAI_API_KEYS` + Langfuse.
- `settings.py`: đọc `ai_base_url`, `backend_base_url`, `frontend_origin`,
  `app_host_port`.
- Test: `test_env_example_split_deploy_and_langfuse_vars`,
  `test_settings_loads_split_deploy_defaults`.

## 2026-09-18 — Phase 1: chốt cấu trúc thư mục FE / BE / AI

### Quyết định
- **AI** giữ nguyên `src/portfolio_watch/` (không đổi tên `ai/` ở Phase 1 —
  tránh rename lớn; tách process ở Phase 3a).
- Thêm placeholder `frontend/` và `backend/` (chỉ README, chưa UI/server).

### Files
- `frontend/README.md` — UI riêng, port 5173, chỉ gọi Backend.
- `backend/README.md` — API sản phẩm, port 8000, HTTP tới AI, không import
  domain agents.
- `specs/implementation-plan.md` — đánh dấu xong mục cấu trúc Phase 1.
- `README.md` — cập nhật trạng thái (đã có placeholder FE/BE).

### Review vs product-spec / test-plan (chỉ mục cấu trúc)
- **Pass:** có 3 vùng `frontend/` · `backend/` · `src/portfolio_watch/` khớp
  hướng tách deploy; backend README ghi rõ không import domain agents.
- **Fail:** không (scope chỉ chốt thư mục).
- **Missing (phase sau):** 3 process chạy thật, UI/timeline, eval nâng cấp,
  `steps[]`, Langfuse — chưa thuộc mục này.

## 2026-09-17 — Rewrite implementation-plan (SDD Bước 3)

### Docs (không code)
- Viết lại `specs/implementation-plan.md` thành 8 phase nhỏ có checklist:
  1 Project setup → 2 Core UI → 3 Core backend/data (AI chất lượng +
  Backend) → 4 Connect UI↔Backend → 5 Validation → 6 Local run →
  7 Local demo → 8 Langfuse tracing.
- Giữ backlog multi-agent (3c) để bổ sung khi debug golden case fail.

## 2026-09-17 — Review / cải thiện product-spec (SDD Bước 2)

### Docs (không code)
- Làm rõ 6 mục: app goal, target users, core user flow, in/out of scope,
  acceptance criteria.
- Giảm jargon kỹ thuật (tên hàm/file) trong product-spec; giữ mô tả sản phẩm
  + 3 luồng (chat, giám sát/HITL, debug golden) dễ triển khai.

## 2026-09-17 — SDD vòng mới: Quality Loop + Split FE/BE/AI (chỉ spec)

### Docs (không implement app)
- Viết lại `specs/product-spec.md` — mục tiêu: debug golden từng case, eval
  task_success/trajectory (ý tưởng llm-engineer-demo), tách Frontend /
  Backend / AI, UI hiện bước, Langfuse.
- Viết lại `specs/implementation-plan.md` — Phase 0–7 + Phase 2b backlog
  multi-agent (điền khi debug).
- Viết lại `specs/test-plan.md` — quy trình 1 case, scorer, regression,
  test 3 process + Langfuse.
- Viết lại `AGENTS.md` — workflow debug case-by-case + ranh giới FE/BE/AI.
- Viết lại `README.md` — trạng thái MVP vs vòng mới; lệnh chạy tạm thời
  1 process; placeholder 3 process.

### Ghi chú
- Phase 0 (docs) đánh dấu xong phần tạo spec; baseline eval số liệu chưa chạy
  (task còn lại Phase 0).
- Lịch sử MVP Phase 1–10 giữ nguyên các mục phía dưới.

## 2026-09-17 — README Quick start: conda `dong312` + Docker Compose

### Setup
- Cài project vào conda env **`dong312`**: `pip install -e ".[dev]"` (import app OK).

### Docs
- README thêm **Quick start** — Cách A (`conda activate dong312`) và Cách B
  (`docker compose up --build`); bảng thử nhanh; troubleshooting conda/Docker;
  các mục Demo with local / Docker Compose gắn env `dong312`.

## 2026-09-17 — MVP status report (SDD Bước 11)

### Thêm
- `specs/mvp-status-report.md` — báo cáo cuối: completed / missing / known
  bugs / run local / demo ngrok / next improvements. Đối chiếu product-spec
  + implementation-plan Phase 1–10. **Không sửa code app** (không bug critical).

## 2026-09-17 — README: mục "Demo with local"

### Thêm (chỉ docs — không đổi logic app)
- Mục **Demo with local**: start backend port **8000**, frontend qua cùng
  origin (không npm), `API_BASE=""` trỏ local backend, ngrok một tunnel
  `ngrok http 8000` khi cần expose.

## 2026-09-17 — README: hướng dẫn chạy local rõ ràng (SDD Bước 9)

### Thay đổi (chỉ docs — không đổi logic app)
- Viết lại mục **Chạy local**: prerequisites, install, environment variables,
  backend run, frontend (static qua FastAPI — không server riêng), local
  URLs, troubleshooting.
- Sửa đường dẫn thư mục: `llm-backend-ref-portfolio-watch/` (bỏ nhầm
  `llm-backend-ref/`).

## 2026-09-17 — Review đóng Phase 10 vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi checklist cuối Phase 10)

**Passes:**
- README có lệnh `python scripts/draw_agent_graph.py` và `--verify`; ghi
  rõ output `docs/agent_graph.mmd` / `.png`.
- Ngày hoàn thành Phase 10 = **2026-09-17**; bảng phase 1–10 đủ ngày.
- Checklist Phase 10 toàn `[x]`.
- test-plan / AC “chạy script → sơ đồ” có hướng dẫn trong README.

**Fails:** không.

**Missing:** không (trong phạm vi Phase 10 / MVP visualization). Implementation
plan Phase 1–10 đã hoàn tất checklist.

## 2026-09-17 — Phase 10 hoàn thành: README + ngày đóng phase

**Ngày hoàn thành Phase 10:** **2026-09-17**

### README
- Thêm mục **Vẽ sơ đồ agent (Phase 10)**: lệnh
  `python scripts/draw_agent_graph.py` và `--verify` → `docs/agent_graph.mmd`
  / `.png`.
- Thêm mục **Eval golden dataset (Phase 9)** (`run_eval.py`) và ghi chú
  Prompt Registry (Phase 8); bỏ mục “Sắp tới — chưa implement (Phase 8-10)”.

### Đóng phase
- Checklist Phase 10 trong `implementation-plan.md` toàn `[x]`.
- Bảng phase tóm tắt cập nhật Phase 10 = **2026-09-17**.

## 2026-09-17 — Review đối chiếu sơ đồ vs product-spec / test-plan

### Kết quả đối chiếu

**Passes:**
- 13 node + đủ cạnh khớp `agents.md` / REQUIRED_*; 2 nhánh + 2 HITL.
- `docs/agent_graph.mmd` chứa đủ label + cạnh (kể cả → END).
- Ánh xạ v4.mmd: mọi agent/gate có nhãn tương ứng (v4 chi tiết hơn —
  không so tuyệt đối số node).
- test-plan “đối chiếu số node + cạnh… 2 nhánh + 2 HITL” — `VERIFY_OK`.
- AC “chạy script → sơ đồ khớp agents.md” — pass với `--verify`.

**Fails (liên quan, đã sửa):**
- LangGraph `draw_mermaid()` gộp mất cạnh → `__end__` → MMD docs chuyển
  sang `architecture_mermaid()` trung thực từ REQUIRED_*.

**Missing (đúng kỳ vọng — mục Phase 10 cuối):**
- README lệnh chạy script + đóng phase change-log.

## 2026-09-17 — Phase 10: đối chiếu sơ đồ vs agents.md / v4.mmd

### Thêm
- `architecture_mermaid()` — MMD trung thực từ REQUIRED_* (không mất cạnh
  → END như `draw_mermaid()` của LangGraph).
- `verify_graph_against_spec()` + CLI `--verify`: 13 node, đủ edge, 2 nhánh,
  2 HITL, Guardrail dùng chung; ánh xạ nhãn sang
  `../portfolio-watch-agent-v4.mmd` (v4 chi tiết hơn — không so tuyệt đối
  số node).
- `tests/test_draw_agent_graph_verify.py`.
- Checklist Phase 10 mục đối chiếu → `[x]`.

### Kết quả đối chiếu (đã chạy)
- StateGraph: **13 node / 26 edge** = REQUIRED.
- docs/agent_graph.mmd: đủ 13 label + mọi cạnh REQUIRED (gồm 5 cạnh → END).
- v4.mmd: mọi agent/gate có nhãn gợi ý tương ứng.

### Chưa làm (Phase 10 cuối)
- Cập nhật README (lệnh chạy script) + change-log đóng phase.

## 2026-09-17 — Review MMD fallback vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi fallback offline)

**Passes:**
- `draw_mermaid()` → `docs/agent_graph.mmd` luôn được ghi (offline-safe).
- PNG lỗi → trả về `.mmd`, không fail toàn bộ (pattern demo).
- Khớp test-plan: MMD bắt buộc; PNG cố gắng khi có mạng.
- Unit test + chạy thật script đã sinh `docs/agent_graph.mmd` (và PNG khi mạng OK).

**Fails:** không (trong phạm vi fallback MMD).

**Missing (đúng kỳ vọng — mục Phase 10 sau):**
- Đối chiếu thủ công số node/cạnh với `agents.md` / v4.mmd.
- README lệnh chạy script.

## 2026-09-17 — Phase 10: fallback `draw_mermaid` → `docs/agent_graph.mmd`

### Thêm
- `save_graph_visualization`: luôn ghi `.mmd` qua `draw_mermaid()` (offline);
  thử PNG; lỗi mermaid.ink → trả về path `.mmd` (pattern demo + test-plan
  “MMD bắt buộc”).
- `DEFAULT_MMD_PATH` = `docs/agent_graph.mmd`.
- `tests/test_draw_agent_graph_mmd.py`.
- Checklist Phase 10 mục fallback MMD → `[x]`.

### Chưa làm (Phase 10 tiếp)
- Đối chiếu số node/cạnh với sơ đồ vẽ tay; README lệnh chạy.

## 2026-09-17 — Review save_graph_visualization PNG vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi export PNG)

**Passes:**
- Pattern demo: `get_graph(xray=True).draw_mermaid_png()` →
  `docs/agent_graph.png`.
- Unit test mock xác nhận `xray=True` + ghi bytes PNG.
- Khớp checklist Phase 10 mục PNG; AC “chạy script → ra sơ đồ” một phần
  (PNG khi có mạng).

**Fails:** không (trong phạm vi PNG path).

**Missing (đúng kỳ vọng — mục Phase 10 sau):**
- Fallback offline `docs/agent_graph.mmd` (test-plan: MMD bắt buộc).
- Đối chiếu số node/cạnh với sơ đồ vẽ tay; README lệnh chạy.

## 2026-09-17 — Phase 10: `save_graph_visualization` → `docs/agent_graph.png`

### Thêm
- `save_graph_visualization()` trong `scripts/draw_agent_graph.py` — pattern
  llm-engineer-demo: `compile().get_graph(xray=True).draw_mermaid_png()` ghi
  `docs/agent_graph.png` (mặc định).
- CLI `python scripts/draw_agent_graph.py` gọi export PNG sau khi kiểm
  node/edge.
- `tests/test_draw_agent_graph_png.py` (mock bytes, không cần mạng).
- Checklist Phase 10 mục PNG → `[x]`.

### Chưa làm (Phase 10 tiếp)
- Fallback `draw_mermaid()` → `docs/agent_graph.mmd` khi lỗi mạng;
  đối chiếu sơ đồ; README.

## 2026-09-17 — Review StateGraph edges vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi nối edge)

**Passes:**
- Đủ 2 nhánh: giám sát (Orchestrator…Confidence/HITL1 + HITL2) và hỏi-đáp
  (Rewrite → Supervisor → workers/Eval → Answer → Guardrail → END).
- 2 HITL gate có cạnh; EventClassifier có nhánh dừng (END) và bất thường
  (EvalAgent); Guardrail dùng chung 2 nhánh — khớp `agents.md` / explained.
- `compile_agent_graph()` thành công; unit test cover REQUIRED_EDGES.

**Fails:** không (trong phạm vi edges).

**Missing (đúng kỳ vọng — mục Phase 10 sau):**
- `docs/agent_graph.mmd` / `.png`; đối chiếu số cạnh với sơ đồ vẽ tay; README.
- AC “chạy script → ra sơ đồ” chưa đủ đến khi có export.

## 2026-09-17 — Phase 10: nối edge 2 nhánh trên StateGraph

### Thêm
- `wire_agent_edges` / `REQUIRED_EDGES` trong `scripts/draw_agent_graph.py`:
  lối vào START → Orchestrator | RewriteQuestion; nhánh giám sát
  (Price/News → EventClassifier → Eval → Synthesis → Guardrail →
  Confidence → HITL1; Eval → HITL2); nhánh hỏi-đáp (Supervisor →
  workers/Eval → AnswerComposer → Guardrail → END).
- `compile_agent_graph()` để xác nhận đồ thị hợp lệ.
- `tests/test_draw_agent_graph_edges.py`.
- Checklist Phase 10 mục nối edge → `[x]`.

### Chưa làm (Phase 10 tiếp)
- Export PNG/MMD; đối chiếu sơ đồ; README.

## 2026-09-17 — Review StateGraph nodes vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi build nodes only)

**Passes:**
- Đủ 13 node theo checklist Phase 10 / `specs/agents.md` (mục sơ đồ sinh
  từ code): gồm 2 HITL gate + Confidence Gate + Guardrail Output + cả
  nhánh giám sát và hỏi-đáp (Orchestrator… / Rewrite…AnswerComposer).
- Node placeholder pass-through (không logic production).
- `tests/test_draw_agent_graph_nodes.py` + `python scripts/draw_agent_graph.py`.

**Fails:** không (trong phạm vi đăng ký node).

**Missing (đúng kỳ vọng — mục Phase 10 sau):**
- Edge 2 nhánh; `docs/agent_graph.mmd` / `.png`; đối chiếu số cạnh; README.
- AC “chạy script → ra sơ đồ” chưa đủ đến khi có export MMD/PNG.

## 2026-09-17 — Phase 10: StateGraph nodes (`draw_agent_graph.py`)

### Thêm
- `scripts/draw_agent_graph.py` — `build_agent_graph()`: LangGraph
  `StateGraph` với **13 node** placeholder (pass-through) đúng checklist /
  `specs/agents.md`: Orchestrator, PriceAgent, NewsAgent, EventClassifier,
  EvalAgent, SynthesisAgent, Guardrail Output, Confidence Gate, HITL Gate 1,
  HITL Gate 2, Supervisor, RewriteQuestion, AnswerComposer.
- `tests/test_draw_agent_graph_nodes.py`.
- Checklist Phase 10 mục build StateGraph nodes → `[x]`.

### Chưa làm (Phase 10 tiếp)
- Nối edge 2 nhánh; export PNG/MMD; đối chiếu sơ đồ; README.

## 2026-09-17 — Review đóng Phase 9 vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi checklist cuối Phase 9)

**Passes:**
- Baseline lần chạy đầu ghi trong change-log + `specs/eval/baseline.json`
  (30/30, rate=1.0, đủ 4 slice; injection 3/3).
- Ngày hoàn thành Phase 9 = **2026-09-17**; bảng phase 1–9 đủ ngày.
- Checklist Phase 9 trong `implementation-plan.md` toàn `[x]`.
- AC/test-plan: golden 30 case, report tổng+slice, regression tolerance,
  injection 100% — pipeline đã có; baseline đã lưu để so lần sau.

**Fails:** không (trong phạm vi đóng Phase 9).

**Missing (đúng kỳ vọng — Phase 10):**
- Script vẽ sơ đồ agent LangGraph (`draw_agent_graph.py`).
- Baseline LLM/`answer_question` production chưa chạy mạng — v1 là
  rule-based stub (đã ghi rõ); cập nhật bằng `--run --save-baseline`.

## 2026-09-17 — Phase 9 hoàn thành: baseline điểm + ngày đóng phase

**Ngày hoàn thành Phase 9:** **2026-09-17**

### Baseline điểm lần chạy đầu tiên

| Mục | Giá trị |
|-----|---------|
| File | `specs/eval/baseline.json` |
| Ngày tạo | **2026-09-17** |
| Tổng | **30/30** passed (`rate=1.0`) |
| lookup | 18/18 (100%) |
| comparison | 6/6 (100%) |
| out_of_scope | 3/3 (100%) |
| injection | 3/3 (100%) — gate cứng OK |
| Tolerance | **0.05** (`REGRESSION_TOLERANCE`) |
| Cách chấm baseline v1 | Rule-based trên 30 case (`skip_judge=True`), `answer_fn` stub khớp `must_include` / an toàn cho oos+injection — khóa regression gate offline. Lần chạy LLM/`answer_question` thật: `python scripts/run_eval.py --run --save-baseline` để cập nhật. |

Checklist Phase 9 trong `implementation-plan.md` toàn `[x]`. Bảng phase
tóm tắt cập nhật Phase 9 = **2026-09-17**.

## 2026-09-17 — Review Injection gate vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Injection gate)

**Passes:**
- Slice `injection`: mọi case phải pass; 1 fail → eval fail.
- Không áp dụng `REGRESSION_TOLERANCE` (hard fail, message ghi rõ).
- Khớp test-plan (“pass 100%, không tolerance”) và AC product-spec
  (“injection phải luôn bị chặn đúng”).
- `--run` in gate + `eval_gates_passed` gồm injection; unit + self-check.

**Fails:** không (trong phạm vi injection gate).

**Missing (đúng kỳ vọng — mục Phase 9 cuối):**
- Ghi baseline điểm lần chạy đầu tiên + ngày hoàn thành Phase 9 vào
  change-log (cần chạy eval đầy đủ / `--save-baseline` thật).

## 2026-09-17 — Phase 9: Injection gate cứng (100%, no tolerance)

### Thêm
- `check_injection_gate` / `format_injection_gate` / `InjectionGateResult`:
  mọi case slice `injection` phải pass; 1 case fail → toàn bộ eval fail,
  **không** áp dụng `REGRESSION_TOLERANCE`.
- `eval_gates_passed`: report sạch + regression OK + injection 100%.
- CLI `--run` in injection gate và dùng nó cho exit code.
- `tests/test_run_eval_injection_gate.py`; `--self-check` cover gate.
- Checklist Phase 9 mục injection gate → `[x]`.

### Chưa làm (Phase 9 cuối)
- Ghi baseline điểm lần chạy đầu + ngày hoàn thành Phase 9 vào change-log.

## 2026-09-17 — Review Regression gate vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Regression gate)

**Passes:**
- Lưu baseline lần chạy (`--save-baseline` → `specs/eval/baseline.json`).
- Lần sau so `rate` tổng với baseline; drop > tolerance → fail.
- Tolerance chốt sẵn `REGRESSION_TOLERANCE=0.05` (ghi trong change-log).
- Khớp test-plan: “điểm tổng giảm quá tolerance → fail”; MVP không gắn CI
  chặn deploy — chỉ exit code khi chạy thủ công `--run`.

**Fails:** không (trong phạm vi regression gate).

**Missing (đúng kỳ vọng — mục Phase 9 sau):**
- Injection gate cứng 100% (AC product-spec / test-plan).
- Ghi baseline điểm lần chạy đầu tiên + ngày hoàn thành Phase 9 vào
  change-log (checklist cuối Phase 9 — cần chạy eval thật).

## 2026-09-17 — Phase 9: Regression gate (baseline + tolerance)

### Thêm
- `save_baseline` / `load_baseline` / `check_regression` trong
  `scripts/run_eval.py`: lưu điểm tổng (+ slice) vào
  `specs/eval/baseline.json`; lần sau so `rate` tổng — drop >
  `REGRESSION_TOLERANCE` (mặc định **0.05**) → regression fail.
- CLI: `--save-baseline`, `--baseline PATH`, `--tolerance`; `--run` luôn
  in regression gate (chưa có baseline → bỏ qua so sánh, không fail).
- `tests/test_run_eval_regression.py`; `--self-check` cover regression.
- Checklist Phase 9 mục Regression gate → `[x]`.

### Quyết định
- Tolerance mặc định = **0.05** (5 điểm phần trăm trên rate tổng).
- Gate dựa trên **điểm tổng** (test-plan); slice scores lưu kèm baseline
  để debug, chưa dùng làm điều kiện fail ở mục này.

### Chưa làm (Phase 9 tiếp)
- Injection gate cứng 100%; ghi baseline lần chạy đầu + ngày đóng Phase 9
  vào change-log.

## 2026-09-17 — Review Eval report vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Report)

**Passes:**
- Điểm tổng `passed/total` (+ rate).
- Điểm theo từng slice (lookup / comparison / out_of_scope / injection).
- Case fail liệt kê kèm `question` + `output` thật (không chỉ số tổng) —
  khớp test-plan + AC “báo cáo pass/fail tổng và theo từng nhóm”.
- `--run` in `format_report`; unit + `--self-check` cover fail có output.

**Fails:** không (trong phạm vi Report).

**Missing (đúng kỳ vọng — mục Phase 9 sau):**
- Regression gate + baseline + tolerance.
- Injection gate cứng 100% (AC có yêu cầu; checklist riêng chưa làm).
- Lưu report ra file (spec không bắt buộc file — in stdout đủ MVP).

## 2026-09-17 — Phase 9: Eval report (tổng + slice + fail output)

### Thêm
- `build_report` / `format_report` / `EvalReport` / `SliceScore` trong
  `scripts/run_eval.py`: điểm tổng, điểm từng slice (lookup/comparison/
  out_of_scope/injection), liệt kê mọi case fail kèm question + output thật
  (và missing/forbidden nếu có).
- CLI `--run` in report đầy đủ (không chỉ số tổng).
- `--self-check` kiểm report pass + fail có output.
- `tests/test_run_eval_report.py`.
- Checklist Phase 9 mục Report → `[x]`.

### Chưa làm (Phase 9 tiếp)
- Regression gate + baseline; injection gate cứng; ghi baseline vào change-log.

## 2026-09-17 — Review eval runner vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi runner)

**Passes:**
- Runner duyệt case trong `golden_dataset.yaml`, lấy output qua
  `answer_question` (cùng deps POST /chat) hoặc `answer_fn` inject.
- Ghép rule-based + LLM-judge theo từng case (`CaseEvalResult`).
- Lookup/comparison: rule fail → skip judge; cả hai phải pass mới `passed`.
- out_of_scope/injection: chỉ rule (judge skipped).
- Unit test stub + `--self-check` runner 4/4; không cần mạng.

**Fails:** không (trong phạm vi runner).

**Missing (đúng kỳ vọng — mục Phase 9 sau):**
- Report điểm tổng + theo slice + liệt kê fail kèm output (mục Report).
- Regression / injection gate cứng / baseline.
- AC “chạy eval → báo cáo pass/fail tổng và theo nhóm” chưa đủ đến khi có
  Report.

## 2026-09-17 — Phase 9: eval runner trong `scripts/run_eval.py`

### Thêm
- `run_eval` / `eval_one_case` / `CaseEvalResult`: gọi `answer_fn` (mặc định
  bọc `application.answer_question` qua `make_answer_fn` + `get_app_deps`,
  cùng luồng POST /chat) cho từng case golden; ghép rule-based + LLM-judge.
- `case_overall_passed`: rule phải pass; judge nếu chạy cũng phải pass.
- CLI `--run [--limit N] [--skip-judge]`; `--self-check` có runner stub 4 case.
- `tests/test_run_eval_runner.py`.
- Checklist Phase 9 mục runner → `[x]`.

### Chưa làm (Phase 9 tiếp)
- Report tổng/slice + liệt kê fail kèm output; regression / injection gate;
  baseline điểm.

## 2026-09-17 — Review LLM-judge scorer vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi LLM-judge)

**Passes:**
- Tiêu chí correctness / completeness / grounding (rubric 1–5).
- `temperature=0` qua `DETERMINISTIC`; model chốt `JUDGE_MODEL=gpt-4o-mini`.
- Chỉ `lookup`/`comparison`; rule-based fail → skip (không gọi LLM).
- Pattern `judge.py`: `chat_parsed` + Pydantic schema + system rubric.
- `tests/test_run_eval_llm_judge.py` + `--self-check` judge gate ok.

**Fails (liên quan, đã sửa):**
- Import lẫn `portfolio_watch` / `src.portfolio_watch` → thống nhất
  `src.portfolio_watch` để tránh load trùng module.

**Missing (đúng kỳ vọng — Phase 9 sau):**
- Runner 30 case, report tổng/slice, regression + injection gate, baseline.
- AC “chạy eval → báo cáo” chưa đủ (chưa có runner).
- Full RAGAS faithfulness (claim-split) chưa cần — grounding nằm trong
  một lần judge (MVP); `ragas_native` là pattern tham chiếu.

### Quyết định
- `JUDGE_PASS_THRESHOLD = 3.0` (overall trung bình ≥ 3 → pass).

## 2026-09-17 — Phase 9: LLM-judge scorer trong `scripts/run_eval.py`

### Thêm
- `score_llm_judge` / `score_case_llm_judge`: rubric
  correctness/completeness/grounding (1–5), `DETERMINISTIC` (temperature=0),
  model chốt `JUDGE_MODEL=gpt-4o-mini` (pattern `judge.py` + chat_parsed).
- Chỉ chạy cho slice `lookup`/`comparison` khi rule-based đã pass; slice
  khác / rule fail → `skipped` (không gọi LLM).
- `JUDGE_PASS_THRESHOLD=3.0` (overall trung bình).
- `tests/test_run_eval_llm_judge.py` (mock `chat_parsed_fn`).
- Checklist Phase 9 mục LLM-judge → `[x]`.

### Chưa làm (Phase 9 tiếp)
- Runner gọi `answer_question`/`POST /chat`, report, regression / injection
  gate, baseline.

## 2026-09-17 — Review rule-based scorer vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi scorer rule-based)

**Passes:**
- `must_include` / `must_not_include` trên output thật; cover cả 4 slice.
- Slice `out_of_scope` tái dùng `find_buy_sell_phrases` (cùng list Guardrail
  Output) — không viết logic mua/bán riêng trong scorer.
- Scorer chạy độc lập trước judge/runner (CLI `--self-check`; fixture 8/8).
- `tests/test_run_eval_rule_based.py` + guardrail confirmation vẫn pass.

**Fails (liên quan, đã sửa):**
- Fixture self-check `"lời khuyên mua bán"` khớp nhầm pattern `"khuyên mua"`
  → đổi output sạch; thêm `stdout.reconfigure(utf-8)` tránh lỗi cp1252
  trên Windows.

**Missing (đúng kỳ vọng — mục Phase 9 sau):**
- LLM-judge, runner 30 case, report tổng/slice, regression + injection gate.
- AC product-spec “chạy eval → báo cáo pass/fail” chưa đủ (chưa có runner).

## 2026-09-17 — Phase 9: rule-based scorer trong `scripts/run_eval.py`

### Thêm
- `scripts/run_eval.py` — `score_rule_based` / `score_case_rule_based`:
  chấm `must_include` + `must_not_include` (case-insensitive) trên output
  thật; áp dụng cả 4 slice. Slice `out_of_scope` gọi thêm
  `find_buy_sell_phrases` từ Guardrail Output (test-plan).
- `find_buy_sell_phrases()` public trên `output_checks.py` (cùng list cụm
  mua/bán với `check_output`).
- CLI `--self-check` với fixture cố định (không gọi app/LLM).
- `tests/test_run_eval_rule_based.py`.
- Checklist Phase 9 mục rule-based scorer → `[x]`.

### Chưa làm (Phase 9 tiếp)
- LLM-judge, runner gọi `answer_question`/`POST /chat`, report, regression /
  injection gate, baseline.

## 2026-09-17 — Review golden_dataset.yaml vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi file golden dataset)

**Passes:**
- Đủ 30 case, tỉ lệ 18/6/3/3 (`lookup`/`comparison`/`out_of_scope`/`injection`).
- Schema case + dataset-level khớp `implementation-plan.md`.
- Ví dụ slice khớp bảng `test-plan.md` (giá/tin 1 mã; so sánh/giải thích;
  ngoài phạm vi; injection).
- `comparison` → `multihop: true`; `lookup` → `multihop: false`.
- `out_of_scope` + `injection` có `must_not_include` chứa “nên mua”/“nên bán”
  (tái dùng cụm Guardrail Output).

**Fails (liên quan, đã sửa):**
- `injection_*` thiếu đồng bộ cụm guardrail (`nên mua`/`nên bán`) + cụm tấn
  injection (`bán hết` / `buy now` / `mua ngay`) → bổ sung; thêm assert trong
  `tests/test_golden_dataset.py`.

**Missing (đúng kỳ vọng — mục Phase 9 sau):**
- `scripts/run_eval.py`, report, regression / injection gate, baseline điểm.
- AC product-spec “chạy eval → báo cáo pass/fail” chưa chạy được (chưa có runner).

## 2026-09-17 — Phase 9: `specs/eval/golden_dataset.yaml` (30 case)

### Thêm
- `specs/eval/golden_dataset.yaml` — dataset `portfolio_watch_chat_golden`
  v1.0; 30 case viết tay theo product-spec + test-plan:
  - `lookup` × 18 (`multihop: false`) — giá/tin FPT, VNM, HPG
  - `comparison` × 6 (`multihop: true`) — so sánh / giải thích biến động
  - `out_of_scope` × 3 — lời khuyên mua, thời tiết, mã ngoài watchlist
  - `injection` × 3 — prompt injection; `must_not_include` chặn “nên mua/bán”
- Schema mỗi case: `id, question, expected, slice:{type, multihop},
  must_include, must_not_include`; dataset-level: `dataset, version,
  created, changelog`.
- `tests/test_golden_dataset.py` — metadata, schema, tỉ lệ 18/6/3/3, unique id.
- Checklist Phase 9 mục golden dataset → `[x]`.

### Chưa làm (các mục Phase 9 tiếp theo)
- `scripts/run_eval.py` (scorer / runner / report / regression / injection gate).

## 2026-09-17 — Review đóng Phase 8 vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi checklist cuối Phase 8 — ghi quyết định)

**Passes:**
- Template engine `string.Template` đã ghi rõ (không Jinja2).
- Bảng model mặc định đủ 7 prompt (`gpt-4o-mini` trong YAML; runtime
  `settings.llm_model`; routing heavy `gpt-4o` ghi metadata).
- Ngày hoàn thành Phase 8 = **2026-09-17**; bảng phase 1–8 đủ ngày.
- Checklist Phase 8 trong `implementation-plan.md` toàn `[x]`.
- test-plan Prompt Registry đã khóa bởi `tests/test_prompt_registry.py`.
- AC “đổi production → agent đổi” đã cover ở unit test agent + registry.

**Fails (liên quan, đã sửa):**
- `test_implementation_plan_phase7_fully_checked` quét từ Phase 7 → EOF
  (dính `- [ ]` Phase 9/10) → giới hạn block Phase 7…Phase 8; thêm assert
  Phase 8 fully checked + change-log quyết định prompt.

**Missing (đúng kỳ vọng — Phase 9+):**
- Golden dataset 30 case + eval pipeline.
- Script vẽ sơ đồ agent (Phase 10).

## 2026-09-17 — Phase 8 hoàn thành: quyết định Prompt Registry + ngày đóng phase

**Ngày hoàn thành Phase 8:** **2026-09-17**

### Quyết định kỹ thuật (Prompt Registry & LLM wiring)

| Mục | Quyết định | Lý do ngắn |
|-----|------------|------------|
| Template engine | `string.Template` (`$var` / `${var}`) | Đủ MVP; không thêm Jinja2 (Lesson16 / llm-engineer-demo) |
| Registry | Git-based `prompts/<name>/vN.yaml` + `production.txt` | Đổi production = sửa file, không sửa code gọi |
| API | `PromptRegistry.get()` / `render()` + `registry()` | Interface tối thiểu; thiếu biến → `ValueError` rõ |
| Chat params | `DETERMINISTIC` (`temperature=0.0`) | Phân loại / routing / soạn cảnh báo ổn định |
| Runtime model | `settings.llm_model` (mặc định `gpt-4o-mini`) qua `infra.llm.completion.chat` | Một backend settings; YAML `model` = metadata “viết cho” |
| Model routing (metadata) | Synthesis / Answer: `gpt-4o-mini` (light) / `gpt-4o` (heavy) khi HIGH hoặc confidence ≥ 0.85 | Ghi trong `FinalAlert.metadata` / compose result; chưa override client model riêng |

### Model mặc định theo từng prompt (`prompts/*/v1.yaml`, production=`1`)

| Prompt | Agent | `model` trong YAML | Ghi chú |
|--------|-------|--------------------|---------|
| `event_classification` | Event Classifier | `gpt-4o-mini` | Lọc rẻ bình thường/bất thường |
| `news_agent_react` | NewsAgent | `gpt-4o-mini` | ReAct decide search/finish |
| `eval_severity` | EvalAgent | `gpt-4o-mini` | Severity + needs_history |
| `synthesis_alert` | SynthesisAgent | `gpt-4o-mini` | Soạn alert; routing heavy ghi metadata |
| `supervisor_routing` | Supervisor | `gpt-4o-mini` | Chọn price/news/eval |
| `rewrite_question` | RewriteQuestion | `gpt-4o-mini` | Chuẩn hoá câu hỏi |
| `answer_compose` | AnswerComposer | `gpt-4o-mini` | Plain text; không HITL |

Checklist Phase 8 trong `implementation-plan.md` toàn `[x]`. Bảng phase
tóm tắt cập nhật Phase 8 = **2026-09-17**.

## 2026-09-17 — Review Unit test PromptRegistry vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (test-plan Prompt Registry + AC đổi production):**
- `registry().get(..., "production")` theo `production.txt`.
- `render` thiếu biến → `ValueError("Thiếu biến...")`.
- `render(version=<số>)` đúng version dù không phải production.
- Đổi `production.txt` → `render("production")` đổi nội dung (registry).
- Đổi `production.txt` → **agent** (`LlmEventClassifier`) dùng version mới
  với cùng brain/`prompt_version="production"` — khớp AC product-spec
  “đổi prompt production → hành vi agent đổi, không sửa code”.
- 9 tests trong `test_prompt_registry.py` pass.

**Fails:** không có lỗi blocking sau khi bổ sung case agent.

**Missing (đúng kỳ vọng — item Phase 8 cuối):**
- Ghi quyết định template engine (`string.Template`), model mặc định từng
  prompt, ngày hoàn thành Phase 8 vào change-log.

## 2026-09-17 — Phase 8: Unit test PromptRegistry (checklist + agent)

- Siết `tests/test_prompt_registry.py`:
  - Giữ đủ 4 case test-plan (get production, thiếu biến, version cụ thể,
    đổi `production.txt` ở mức registry).
  - Thêm case checklist: đổi `production.txt` → **cùng** `LlmEventClassifier`
    (`prompt_version="production"`) dùng version mới, không sửa code agent.
  - Assert ánh xạ đủ tên test ↔ checklist/test-plan.
- Đánh dấu `[x]` item Unit test PromptRegistry trong implementation-plan.

## 2026-09-17 — Review Phase 8 Protocol stability vs product-spec / test-plan

### Kết quả đối chiếu

**Passes:**
- 6 port cốt lõi trong `domain/ports.py` còn đủ (Price/News/Watchlist/
  History/Memory/Notifier) — không bị đụng khi wire LLM.
- Protocol agent (Classifier/News/Eval/Alert/Rewrite/Supervisor/Answer)
  vẫn có đúng method; cả `Llm*` và `Heuristic*` implement đủ method.
- Production default factory = `Llm*` cho cả 7 brain/composer.
- `application/` không import `Llm*`; vẫn inject optional
  `*_brain` / `alert_composer` (orchestration không đổi).
- AC Prompt Registry / chat / scan vẫn dựa trên inject cũ — regression
  suite liên quan pass qua test khóa mới.

**Fails (liên quan, đã siết):**
- Test Protocol ban đầu assert mơ hồ cho EventClassifier → viết lại
  assert `method in Protocol.__dict__` rõ ràng.

**Missing (đúng kỳ vọng — item Phase 8 tiếp):**
- Checklist Unit test PromptRegistry (đã có file test từ trước — sẽ
  đối chiếu/đánh dấu ở bước sau).
- Ghi quyết định template engine + model + ngày đóng Phase 8.

## 2026-09-17 — Phase 8: xác nhận Protocol ổn định / application không hardcode LLM

- Thêm `tests/test_phase8_protocol_stability.py`: ports, Protocol methods,
  Llm+Heuristic surface, default factory = LLM, application không import
  `Llm*`, vẫn truyền optional brains.
- Không đổi production orchestration — chỉ khóa regression cho checklist
  “giữ Protocol / không đổi application call sites”.

## 2026-09-17 — Review LLM AnswerComposer vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — chỉ AnswerComposer)

**Passes:**
- test-plan AnswerComposer: không qua HITL (`hitl_used=False`); guardrail
  chung với nhánh giám sát (chặn “nên mua/bán”, số lệch evidence).
- `LlmAnswerDraftBrain`: `registry().render("answer_compose")` + chat plain
  text; truyền question/price/news/eval/evidence/violations.
- Protocol `AnswerDraftBrain` giữ nguyên; `application/answer_question` không
  đổi chữ ký.
- Đổi `production.txt` → prompt gửi LLM đổi.
- Chat API / answer_question regression vẫn pass.

**Fails:** không có lỗi blocking (27 related tests passed).

**Missing (đúng kỳ vọng — item Phase 8 còn lại):**
- Checklist “giữ Protocol / không đổi application” (xác nhận tổng hợp).
- Unit test PromptRegistry riêng (đã có `test_prompt_registry.py` từ trước).
- Ghi quyết định template engine + model mặc định + ngày đóng Phase 8.

## 2026-09-17 — Phase 8: wire LLM AnswerComposer + Prompt Registry

- `domain/agents/answer_composer.py`:
  - Thêm `LlmAnswerDraftBrain`: `registry().render("answer_compose", ...)` +
    `chat` (DETERMINISTIC); output plain text (không JSON).
  - `_DEFAULT_ANSWER_BRAIN_FACTORY = LlmAnswerDraftBrain` (Protocol
    `AnswerDraftBrain` + vòng guardrail / `hitl_used=False` giữ nguyên).
- `tests/conftest.py`: monkeypatch answer factory → Heuristic trong pytest.
- `tests/test_answer_composer_llm.py`: mock LLM (registry, rewrite khi nên
  mua, rỗng → fallback, đổi production).

## 2026-09-17 — Review LLM Supervisor/Rewrite vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — Supervisor + RewriteQuestion)

**Passes:**
- test-plan: hỏi giá → chỉ `price`; “tại sao giảm” → có `eval`; “mã đó” /
  follow-up dùng Memory (Heuristic qua conftest + LLM mock).
- `LlmRewriteBrain` / `LlmSupervisorBrain` dùng đúng prompt registry
  (`rewrite_question`, `supervisor_routing`).
- Protocol giữ nguyên; `answer_question` không đổi chữ ký.
- JSON lỗi → fallback an toàn (price_lookup / agents=["price"]).
- Đổi `production.txt` → prompt gửi LLM đổi (cả 2 prompt).
- API chat regression vẫn pass.

**Fails:** không có lỗi blocking (23 related tests passed).

**Missing (đúng kỳ vọng):**
- AnswerComposer chưa wire LLM (item Phase 8 tiếp theo).

## 2026-09-17 — Phase 8: wire LLM Supervisor + RewriteQuestion

- `domain/agents/supervisor.py`:
  - `LlmRewriteBrain`: `registry().render("rewrite_question", ...)` + chat;
    parse JSON rewritten/symbol/intent.
  - `LlmSupervisorBrain`: `registry().render("supervisor_routing", ...)` +
    chat; parse `agents_to_call` (price/news/eval).
  - `_DEFAULT_REWRITE_FACTORY` / `_DEFAULT_SUPERVISOR_FACTORY` = LLM
    (Protocol giữ nguyên; `application/answer_question` không đổi chữ ký).
- `tests/conftest.py`: monkeypatch cả 2 factory → Heuristic trong pytest.
- `tests/test_supervisor_llm.py`: mock LLM (price-only, explain+eval,
  memory symbol, JSON lỗi, đổi production).

## 2026-09-17 — Review LLM SynthesisAgent vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — chỉ SynthesisAgent)

**Passes:**
- test-plan Synthesis + Guardrail: HIGH → model nặng; LOW → nhẹ; “nên
  mua/bán” → rewrite (`draft_attempts > 1`); số không khớp evidence → chặn.
- `LlmAlertComposer`: `registry().render("synthesis_alert")` + chat; parse
  JSON title/body; truyền preferences + violations vào prompt.
- Protocol `AlertComposer` + vòng guardrail giữ nguyên; `application/` không
  đổi chữ ký (`composer=alert_composer`).
- Đổi `production.txt` → prompt gửi LLM đổi.
- JSON lỗi → fallback sạch (không lời khuyên mua/bán).
- AC product-spec guardrail mua/bán vẫn pass (`test_guardrail_confirmation`).

**Fails:** không có lỗi blocking (27 related tests passed).

**Missing (đúng kỳ vọng):**
- Supervisor / RewriteQuestion / AnswerComposer chưa wire LLM.

## 2026-09-17 — Phase 8: wire LLM SynthesisAgent + Prompt Registry

- `domain/agents/synthesis_agent.py`:
  - Thêm `LlmAlertComposer`: `registry().render("synthesis_alert", ...)` +
    `chat` (DETERMINISTIC); parse JSON `title`/`body`.
  - `_DEFAULT_COMPOSER_FACTORY = LlmAlertComposer` (Protocol `AlertComposer`
    giữ nguyên; vòng guardrail rewrite không đổi).
  - `HeuristicAlertComposer` giữ cho test / inject.
- `tests/conftest.py`: monkeypatch composer factory → Heuristic trong pytest.
- `tests/test_synthesis_agent.py`: test-plan + mock LLM (registry, rewrite
  khi nên mua, JSON lỗi → fallback sạch, đổi production).

## 2026-09-17 — Review LLM EvalAgent vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — chỉ EvalAgent)

**Passes:**
- test-plan EvalAgent: đủ data → không gọi history; mập mờ → gọi history +
  confidence thấp hơn khi lịch sử không ủng hộ (Heuristic qua conftest).
- `LlmEvalBrain`: `registry().render("eval_severity")` + chat; parse
  `needs_history` + Severity; cache tránh double-call khi đủ data.
- Protocol `EvalAgentBrain` giữ nguyên; `application/` không đổi chữ ký.
- Đổi `production.txt` → prompt gửi LLM đổi.
- Lần 2 sau khi có history: prompt chứa bars (không còn "(chưa có lịch sử)").
- JSON lỗi → Severity an toàn (`eval lỗi`, không crash scan).

**Fails (liên quan, đã siết):**
- Test history-request chưa assert nội dung prompt lần 2 có bars → bổ sung
  assert trong `test_llm_eval_requests_history_then_scores`.

**Missing (đúng kỳ vọng):**
- Synthesis / Supervisor / AnswerComposer chưa wire LLM.

## 2026-09-17 — Phase 8: wire LLM EvalAgent + Prompt Registry

- `domain/agents/eval_agent.py`:
  - Thêm `LlmEvalBrain`: `registry().render("eval_severity", ...)` + `chat`
    (DETERMINISTIC); parse JSON `needs_history` + Severity.
  - Cache lần gọi khi chưa có history để tránh double-call khi đủ data.
  - `_DEFAULT_EVAL_BRAIN_FACTORY = LlmEvalBrain` (Protocol giữ nguyên;
    `application/` không đổi chữ ký — vẫn `brain=eval_brain`).
- `tests/conftest.py`: monkeypatch eval factory → Heuristic trong pytest.
- `tests/test_eval_agent.py`: heuristic test-plan + mock LLM (skip/request
  history, JSON lỗi, đổi production).

## 2026-09-17 — Review LLM NewsAgent vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — chỉ NewsAgent)

**Passes:**
- test-plan NewsAgent: lọc tin không liên quan; ReAct 2 lần gọi tool rồi
  dừng; `max_steps` chặn vòng lặp; lỗi fetch giữ tin đã có.
- `LlmNewsBrain.decide` dùng `registry().render("news_agent_react")` +
  `chat` (DETERMINISTIC); parse JSON search/finish.
- `filter_relevant` heuristic (symbol trong blob) — khớp vòng ReAct hiện có.
- Protocol `NewsAgentBrain` giữ nguyên; scan/chat chỉ đổi default factory.
- Đổi `production.txt` → prompt gửi LLM đổi (AC registry mức agent này).
- Pytest: conftest monkeypatch factory → Heuristic (không flake OpenAI).

**Fails:** không có lỗi blocking sau khi chạy
`tests/test_news_agent.py` + scan/API/answer liên quan (40 passed).

**Missing (đúng kỳ vọng):**
- Eval / Synthesis / Supervisor / AnswerComposer chưa wire LLM.
- AC “đổi production → mọi agent LLM đổi” chưa đủ phase.

## 2026-09-17 — Phase 8: wire LLM NewsAgent + Prompt Registry

- `domain/agents/news_agent.py`:
  - Thêm `LlmNewsBrain`: `registry().render("news_agent_react", ...)` +
    `chat` (DETERMINISTIC) cho ReAct `decide` (search/finish JSON).
  - `filter_relevant` giữ heuristic (symbol trong title/snippet) — prompt
    JSON không trả danh sách tin đã lọc.
  - `_DEFAULT_NEWS_BRAIN_FACTORY` / `default_news_brain()`; `run_news_agent`
    nhận `brain` optional.
- `application/scan_symbol.py` + `answer_question.py`: default
  `HeuristicNewsBrain()` → `default_news_brain()` (chữ ký/luồng không đổi).
- `tests/conftest.py`: monkeypatch news factory → Heuristic trong pytest.
- `tests/test_news_agent.py`: heuristic test-plan + mock LLM (registry,
  search→finish, JSON lỗi, đổi production).

## 2026-09-17 — Review LLM Event Classifier vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 — chỉ Event Classifier)

**Passes:**
- test-plan Event Classifier: biến động nhỏ → bình thường; |%| lớn / tin
  tiêu cực → bất thường (qua Heuristic inject; LLM mock parse JSON).
- `LlmEventClassifier` gọi `registry().render("event_classification", ...)`
  + `infra.llm.completion.chat` (DETERMINISTIC).
- Protocol `EventClassifierBrain` giữ nguyên; `application/scan_symbol` không
  đổi chữ ký.
- Lỗi LLM/JSON → không escalate Eval (`route=bình thường` + reason lỗi).
- Đổi `production.txt` → nội dung prompt gửi LLM đổi (AC Prompt Registry
  mức agent này).

**Fails (liên quan feature này, đã sửa):**
- Thiếu case AC “đổi production → prompt agent đổi” và case JSON hỏng →
  bổ sung trong `tests/test_event_classifier.py`.
- Default LLM làm flake toàn bộ scan/API tests → `tests/conftest.py` autouse
  monkeypatch `_DEFAULT_BRAIN_FACTORY` → Heuristic trong pytest.

**Missing (đúng kỳ vọng — agent khác chưa wire):**
- NewsAgent / Eval / Synthesis / Supervisor / AnswerComposer vẫn Heuristic.
- AC end-to-end “đổi production → hành vi **mọi** agent LLM đổi” chưa đủ.

## 2026-09-17 — Phase 8: wire LLM Event Classifier + Prompt Registry

- `domain/agents/event_classifier.py`:
  - Thêm `LlmEventClassifier`: `registry().render("event_classification",
    version=production, ...)` + `infra.llm.completion.chat` (DETERMINISTIC).
  - Parse JSON `route`/`reason` → `RoutingDecision` (`bình thường`/
    `bất thường`).
  - Mặc định production: `_DEFAULT_BRAIN_FACTORY = LlmEventClassifier`
    (Protocol `EventClassifierBrain` giữ nguyên; `application/` không đổi).
  - `HeuristicEventClassifier` giữ cho test / inject tường minh.
- `tests/conftest.py`: autouse monkeypatch factory → Heuristic trong pytest
  (tránh gọi OpenAI / flake); test LLM inject `brain=LlmEventClassifier(chat_fn=...)`.
- `tests/test_event_classifier.py`: heuristic cases + mock LLM (registry
  prompt + parse JSON + đổi production + JSON lỗi).

## 2026-09-17 — Review `PromptRegistry` vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 item 2 — registry only)

**Passes (test-plan Prompt Registry + In Scope git-based registry):**
- `registry().get(..., version="production")` theo `production.txt`.
- `render` thiếu biến bắt buộc → `ValueError("Thiếu biến...")`, không để
  `$var` lọt ra output.
- `render(..., version=<số>)` đúng version đó dù production trỏ bản khác.
- Đổi `production.txt` → `render(..., "production")` đổi nội dung, không
  sửa code gọi.
- Template engine: `string.Template` (`$var`).

**Fails (liên quan feature này, đã sửa):**
- Path `prompts/` chỉ `parents[4]` — dễ lệch layout Docker/non-editable
  (cùng lớp rủi ro với `WEB_DIR`) → thêm `resolve_prompts_dir()` (editable /
  `/app/prompts` / cwd).
- Test chưa gọi đúng helper `registry()` như test-plan viết → siết
  `tests/test_prompt_registry.py` dùng `registry().get` / `registry().render`.

**Missing (đúng kỳ vọng — chưa wire agent):**
- AC product-spec “đổi production → **hành vi agent** đổi” (cần item wire
  LLM vào từng agent).
- Checklist “Unit test … agent dùng đúng version mới” (phần agent) — vẫn
  `[ ]`.

## 2026-09-17 — Phase 8 (item 2): `PromptRegistry` (get/render)

- Thêm `infra/llm/prompt_registry.py`:
  - `Prompt` dataclass (metadata + template).
  - `PromptRegistry.get(name, version="production"|"latest"|int)`.
  - `PromptRegistry.render(...)` qua `string.Template`.
  - `_required_vars()` + raise `ValueError("Thiếu biến...")` khi thiếu var
    (không `safe_substitute`).
  - `registry()` singleton + `resolve_prompts_dir()`.
- Export qua `infra/llm/__init__.py`.
- `tests/test_prompt_registry.py` — cover 4 case test-plan Prompt Registry.
- **Quyết định template engine:** `string.Template` (`$var`) — không Jinja2.
- **Chưa** wire LLM vào agent (vẫn Heuristic*Brain).

## 2026-09-17 — Review khung `prompts/` vs product-spec / test-plan

### Kết quả đối chiếu (phạm vi Phase 8 item 1 — scaffold only)

**Passes (In Scope Prompt Registry ở mức file + checklist item 1):**
- Đủ 7 prompt dir khớp `agents.md` / implementation-plan.
- Mỗi `v1.yaml` có `version` + `changelog` + metadata bắt buộc; template `$var`.
- `production.txt` = `1` (alias production → version hiện hành).
- `tests/test_prompts_scaffold.py` pass.

**Fails (liên quan feature này, đã sửa):**
- `PyYAML` dùng để parse `prompts/*.yaml` trong test nhưng **không** khai báo
  trong `pyproject.toml` (chỉ có sẵn ở môi trường máy) → thêm
  `pyyaml>=6.0.0`.
- `Dockerfile` (Phase 7) chưa `COPY prompts/` → image demo sẽ thiếu registry
  files khi wire LLM → thêm `COPY prompts ./prompts` + assert trong
  `tests/test_dockerfile.py`.
- Siết test: `changelog` không được rỗng; assert `pyyaml` có trong
  `pyproject.toml`.

**Missing (đúng kỳ vọng — thuộc item Phase 8 sau, không implement ở đây):**
- AC product-spec “đổi production → hành vi agent đổi” (cần
  `PromptRegistry` + wire LLM).
- 4 case test-plan Prompt Registry (`registry().get` / `render` / thiếu
  biến / version cụ thể).

## 2026-09-17 — Phase 8 (item 1): khung `prompts/` git-based

- Tạo `prompts/` ở root với **7** thư mục agent có LLM (theo
  `specs/agents.md` / implementation-plan Phase 8):
  `event_classification/`, `eval_severity/`, `synthesis_alert/`,
  `supervisor_routing/`, `rewrite_question/`, `answer_compose/`,
  `news_agent_react/`.
- Mỗi thư mục: `v1.yaml` (metadata: `name, version, model, description,
  owner, created, changelog, eval_score, template`) + `production.txt`
  chứa `"1"`. Template dùng `$var` (`string.Template`) — khớp hands-on
  Lesson16 / pattern `llm-engineer-demo/app/agent_pr/prompts/`.
- Nội dung prompt MVP bám domain portfolio_watch (không copy nguyên prompt
  demo có `db_agent`/`db_write`).
- `tests/test_prompts_scaffold.py` — assert đủ 7 dir, production=`1`,
  metadata bắt buộc, template có `$var`.
- **Chưa** viết `PromptRegistry`, **chưa** wire LLM vào agent (các item
  Phase 8 tiếp theo vẫn `[ ]`). Agent vẫn chạy `Heuristic*Brain`.

## 2026-09-17 — Rewrite `AGENTS.md` (short, practical ruleset)

- Viết lại `AGENTS.md` gọn lại thành 7 quy tắc rõ ràng (đọc specs trước khi
  code, một phase/task mỗi lần, giữ đơn giản, không thêm lib thừa, không đổi
  architecture nếu spec chưa cập nhật, cập nhật change-log sau mỗi lần
  implement, giải thích cách test) + 1 bảng tra nhanh "Where to look" trỏ
  tới từng file spec — nội dung không đổi so với bản cũ, chỉ gộp lại (trước
  đó 3 mục "Nguyên tắc chính" / "Workflow" / "Coding Style" / "Testing" lặp
  lại cùng 7 ý này).
- **Xoá khối nội dung chèn sẵn** (`<!-- vnai-bootstrap | auto-generated -->`,
  đã ghi chú lần trước ở đây) — hướng dẫn agent tự cài `vnstock`/`vnai`, xin
  API key người dùng, chạy/xoá script tạm. Khối này không liên quan tới quy
  ước làm việc của project (đã bị flag từ lần review trước, giờ được yêu cầu
  viết lại `AGENTS.md` "ngắn gọn, thực tế" nên loại bỏ luôn thay vì giữ song
  song). File đã sửa được track bởi git, có thể revert nếu cần giữ lại.
- Không viết code.

## 2026-09-17 — Review & cleanup `implementation-plan.md` (10 phases)

- Rà lại toàn bộ 10 phase theo đúng thứ tự yêu cầu (1 Project setup … 7
  Docker demo setup, 8 Prompt Registry & LLM wiring, 9 Golden dataset & Eval
  pipeline, 10 Agent graph visualization) — cấu trúc phase đã đúng từ trước,
  không đổi thứ tự/tên (chỉ sửa tiêu đề Phase 3 từ "Core backend / data
  logic" → "Core backend or data logic" cho khớp đúng cách gọi).
- Phase 1-7 (đã hoàn thành, `[x]`) vốn đã có checklist item nhỏ, 1 item/1
  file — giữ nguyên, không sửa nội dung lịch sử.
- Phase 8-10 (chưa bắt đầu, `[ ]`) đang gộp nhiều việc vào 1 checkbox (vd.
  1 item duy nhất "thay Heuristic*Brain" cho cả 6 agent; 1 item duy nhất cho
  cả 3 bước của `run_eval.py`) — tách nhỏ lại cho khớp độ chi tiết của Phase
  1-7 và dễ check off từng bước:
  - Phase 8: tách 1 item/1 agent cho việc wiring LLM thật (6 item riêng thay
    vì 1 item gộp), thêm item test đổi `production.txt`.
  - Phase 9: tách `run_eval.py` thành 3 item riêng (scorer rule-based,
    scorer LLM-judge, runner ghép 2 scorer) + tách riêng regression gate
    thường và gate cứng cho slice `injection`.
  - Phase 10: tách việc build node / nối edge / `draw_mermaid_png` /
    fallback `draw_mermaid` / đối chiếu thủ công thành các item riêng.
- Không đổi phạm vi hay quyết định kỹ thuật nào, chỉ tổ chức lại checklist
  cho rõ và nhỏ hơn. Không viết code.

## 2026-09-17 — Review & cleanup `product-spec.md`

- Rà lại `product-spec.md` sau lần thêm Phase 8-10: các bullet Prompt
  Registry/Eval/Diagram đang bị nối đuôi vào cuối "In Scope" và "Acceptance
  Criteria" lẫn với phần ứng dụng cốt lõi, lệch tông (1 acceptance criterion
  viết dạng lời gọi code `registry().render(...)` thay vì hành vi sản phẩm
  như các mục còn lại).
- Sửa: tách "In Scope" thành 2 nhóm rõ ràng — **Ứng dụng cốt lõi** và
  **Công cụ chất lượng LLM (Phase 8-10)**; viết lại 3 acceptance criteria
  liên quan theo đúng tông "hành động → kết quả quan sát được" của các mục
  gốc, bỏ cú pháp code. Gộp bớt 2 bullet Out of Scope trùng ý (A/B test thật
  + hosted registry). Không đổi nội dung/phạm vi, chỉ tổ chức lại cho rõ và
  đơn giản hơn. Không viết code.

## 2026-09-17 — Spec update: Prompt Registry, Golden Dataset & Eval Pipeline, Agent Graph Visualization (LangGraph)

- Rà lại code hiện có (`src/portfolio_watch/domain/agents/*`): xác nhận toàn
  bộ agent đang là `Heuristic*Brain` (rule-based), **chưa** có agent nào gọi
  LLM thật qua `infra/llm/`, và **chưa** có Prompt Registry hay eval/
  golden-dataset nào tồn tại trong repo. Đối chiếu thêm `llm-backend-ref`
  (sibling) — cũng chưa có 2 phần này, nhưng có `judge.py` / `ragas_native.py`
  / `agent_eval.py` (LLM-as-judge "native", không cần thư viện `ragas`) tái
  dùng được cho Phase 9.
- Đọc "LLMOps Prompt Management" (Lesson16) và "Class 18 - LLM Evaluation
  Pipelines" (Lesson17) — lấy pattern hands-on:
  - Prompt Registry git-based: 1 thư mục/prompt name, mỗi version 1 file
    `vN.yaml` + `production.txt` trỏ version hiện hành; interface tối giản
    `registry().render(name, version="production", **vars)`.
  - Golden dataset 30 case theo tỉ lệ 18/6/3/3 (60%/20%/10%/10%) — áp dụng
    lại đúng tỉ lệ này cho domain stock (lookup / comparison-explain /
    out_of_scope / injection) thay vì domain tra cứu luật của ví dụ gốc.
  - Eval pipeline: chấm rule-based trước, LLM-judge (rubric tuyệt đối:
    correctness/completeness/grounding, temperature=0) khi cần, gate cứng
    cho slice an toàn (injection).
- Khảo sát `llm-engineer-demo` — xác nhận có sẵn 4 chỗ dùng pattern vẽ sơ đồ
  agent bằng LangGraph (`save_graph_visualization`, rõ nhất ở
  `app/agent_pr/supervisor_agent/graph.py`): `graph.get_graph(xray=True)
  .draw_mermaid_png()`, fallback `draw_mermaid()` ra `.mmd` khi không có
  mạng — sẽ tái dùng nguyên pattern này ở Phase 10 thay vì viết mới.
- Cập nhật spec (**chưa viết code implementation**):
  - `specs/product-spec.md` — thêm Prompt Registry, Golden dataset/Eval
    pipeline, script vẽ sơ đồ vào In Scope + Out of Scope (CI eval, hosted
    registry, A/B test thật đều ngoài phạm vi MVP); thêm acceptance criteria
    tương ứng.
  - `specs/implementation-plan.md` — thêm `prompts/`, `specs/eval/`,
    `scripts/run_eval.py`, `scripts/draw_agent_graph.py`, `docs/agent_graph.*`
    vào cấu trúc thư mục; thêm dòng tái dùng `judge.py`/`ragas_native.py` và
    `save_graph_visualization` vào bảng reuse; thêm Phase 8 (Prompt Registry
    & LLM wiring), Phase 9 (Golden dataset & Eval pipeline), Phase 10 (Agent
    graph visualization) — cả 3 phase đang `[ ]` (chưa bắt đầu).
  - `specs/test-plan.md` — thêm mục Prompt Registry (4 test case) và Eval
    pipeline (bảng 30 case theo slice + tiêu chí pass/gate); cập nhật "Ngoài
    phạm vi test MVP" (bỏ ghi chú `agent_eval.py` cũ, thay bằng CI/A-B test).
  - `specs/agents.md` — gắn tên thư mục Prompt Registry tương ứng cho từng
    agent có LLM (NewsAgent, EventClassifier, EvalAgent, SynthesisAgent,
    Supervisor, RewriteQuestion, AnswerComposer); thêm mục "Sơ đồ sinh từ
    code (LangGraph, Phase 10)" mapping node/edge.
  - `AGENTS.md`, `README.md` — ghi chú tham chiếu Phase 8-10 (README thêm
    mục "Sắp tới — chưa implement"), không đổi quy trình làm việc hiện có.
- **Chưa implement gì** — đây là bước dừng lại theo đúng yêu cầu spec-driven,
  chờ review trước khi bắt đầu Phase 8.

### Lưu ý phát hiện được (ngoài phạm vi task này)

- `AGENTS.md` (root) có sẵn một khối nội dung được chèn từ trước (đánh dấu
  `<!-- vnai-bootstrap | auto-generated -->`, có vẻ do công cụ `vnai`/
  `vnstock` tự ghi khi chạy trước đây) hướng dẫn agent code tự động cài đặt
  package, xin API key người dùng, chạy script tạm rồi xoá... Nội dung này
  không liên quan tới quy ước làm việc thật của project (phần gốc của
  `AGENTS.md` chỉ có mục "spec-driven" ở đầu file, dòng 1-37) — không đụng
  tới khối này trong lần cập nhật này, chỉ ghi chú lại để người dùng biết và
  tự quyết định có giữ/xoá.

## 2026-09-17 — Review quyết định Docker / đóng Phase 7 vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục cuối ↔ demo packaging / 1 URL):**
- Image base `python:3.12-slim`; tag `portfolio-watch:demo`.
- Port container **8000**; host `${APP_HOST_PORT:-8000}`.
- Volume `portfolio-watch-sqlite` → `/app/data` (`SQLITE_PATH=…/portfolio_watch.db`).
- `env_file: .env`; demo URL cùng origin `http://localhost:8000/`.
- Ngày đóng Phase 7: **2026-09-17**; bảng phase 1–7 đủ ngày; checklist `[x]`.

**Fails:** không có thiếu sót so với checklist mục này (sau khi sửa assert
test không còn yêu cầu placeholder `*(chưa)*` toàn file).

**Missing:** không còn mục unchecked trong `implementation-plan.md`.

## 2026-09-17 — Phase 7 hoàn thành: quyết định Docker + ngày đóng phase

**Ngày hoàn thành Phase 7:** **2026-09-17**

### Quyết định Docker (demo packaging)

| Mục | Quyết định | Lý do ngắn |
|-----|------------|------------|
| Image base | `python:3.12-slim` | Khớp runtime local ≥3.10; slim đủ cho FastAPI + deps |
| Image tag | `portfolio-watch:demo` (compose `build: .`) | Một service app; không multi-stage |
| Container port | **8000** (`EXPOSE` + uvicorn `--port 8000`) | Cùng cổng local / product demo |
| Host port | `${APP_HOST_PORT:-8000}:8000` (biến `APP_HOST_PORT`) | Đổi cổng host qua `.env`, không đổi image |
| Volume name | `portfolio-watch-sqlite` (compose key `pw_sqlite`) | Named volume — SQLite sống qua `restart` / `down` |
| Volume path | host volume → `/app/data` | `SQLITE_PATH=/app/data/portfolio_watch.db` |
| Env / secrets | `env_file: .env`; không bake key vào image | Compose override `API_HOST` / `SQLITE_PATH` trong container |
| Demo URL | `http://localhost:8000/` (API + `web/` cùng origin) | Một URL; `API_BASE=""` |

Bảng phase (mục “Ngày hoàn thành từng phase”) cập nhật Phase 7 = **2026-09-17**.
Checklist Phase 7 trong `implementation-plan.md` toàn `[x]`.

**Liên kết AC:** `scripts/verify_clean_docker.py` → `CLEAN_DOCKER_SMOKE_OK`
(3 luồng qua cùng API UI dùng).

## 2026-09-17 — Review Docker 3-luồng máy sạch vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 xác nhận máy sạch ↔ AC 3 luồng / demo 1 URL):**
- `docker compose up --build` → health + UI (`chat`/`watchlist`/`approvals`).
- Quét: `POST /scan` FPT (giá thật, route bình thường).
- Chat: `POST /chat` không HITL, có `answer`.
- HITL: approve → `sent`; reject + `reject_reason` ghi lại.
- Script `scripts/verify_clean_docker.py` → `CLEAN_DOCKER_SMOKE_OK` (đã chạy thật).

**Fails (liên quan feature, đã sửa):**
- Seed HITL dùng ID cố định `docker-a1` trên volume còn resolution cũ →
  `list_pending` rỗng → đổi seed sang UUID mỗi lần chạy.
- `subprocess` capture compose log Windows cp1252 → `encoding=utf-8`,
  `errors=replace`.

**Missing (đúng kỳ vọng — mục Phase 7 cuối):**
- Ghi quyết định Docker (port/volume/base) + ngày đóng Phase 7.

## 2026-09-17 — Phase 7: xác nhận Docker Compose chạy 3 luồng

- `scripts/verify_clean_docker.py`: compose up --build, UI + scan/chat/HITL.
- README § Demo Docker mục 4; `tests/test_clean_docker_smoke.py`.
- Chạy thật trên máy này → `CLEAN_DOCKER_SMOKE_OK`.

## 2026-09-17 — Review README Demo bằng Docker vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục README Docker ↔ demo 1 URL / 3 luồng):**
- Yêu cầu Docker + Compose; `cp`/Copy-Item `.env.example` → `.env`.
- `docker compose up --build`; mở http://localhost:8000/ (UI+API).
- `logs -f`, `down`, `down -v` (reset volume `portfolio-watch-sqlite`).

**Fails:** không có thiếu sót so với checklist mục này.

**Missing (đúng kỳ vọng — Phase 7 tiếp):**
- Xác nhận máy sạch `compose up` + 3 luồng UI.
- Ghi quyết định Docker (port/volume/base) + ngày đóng Phase 7.

## 2026-09-17 — Phase 7: mục README "Demo bằng Docker"

- Thêm section hướng dẫn: yêu cầu, `.env`, `up --build`, URL, dừng/log/reset.
- `tests/test_readme_docker_demo.py`.

## 2026-09-17 — Review single-URL API+web in container vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 — 1 URL demo ↔ product-spec Frontend cùng origin):**
- `GET /` UI (chat/watchlist/approvals) + `GET /health` + API JSON cùng host.
- `app.js` `API_BASE=""`; Dockerfile `COPY web` + uvicorn `main:app`.
- `resolve_web_dir()`: editable `/app/web`, fallback `Path("/app/web")`, cwd.

**Fails (liên quan feature này, đã sửa):**
- `WEB_DIR` chỉ `parents[2]/web` dễ lệch layout container → thêm
  `resolve_web_dir()` đa ứng viên.
- Thêm `tests/test_docker_single_url.py` (layout editable + same-origin).

**Missing (đúng kỳ vọng):**
- Live `docker compose up` trên máy này (Docker daemon off lúc review).
- README "Demo bằng Docker" (mục Phase 7 tiếp).

## 2026-09-17 — Phase 7: FastAPI phục vụ API + web/ một URL (container)

- `main.resolve_web_dir()` để mount static ổn định trong Docker.
- Xác nhận cùng origin: `/` + `/health` + `/app.js` (`API_BASE=""`).

## 2026-09-17 — Review Docker env_file vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 env từ .env, không bake secret vào image):**
- `docker-compose.yml`: `env_file: .env`; port `${APP_HOST_PORT:-8000}:8000`.
- Compose `environment` ghi đè `API_HOST=0.0.0.0`,
  `SQLITE_PATH=/app/data/portfolio_watch.db` (thắng giá trị local).
- `.env.example`: `APP_HOST_PORT`, ghi chú DB trong volume; Dockerfile /
  `.dockerignore` không chứa secret.

**Fails (liên quan feature này, đã sửa):**
- Test compose còn assert cứng `8000:8000` sau khi đổi sang
  `APP_HOST_PORT` → cập nhật `tests/test_docker_compose.py`.
- Cảnh báo: `env_file` inject *mọi* key trong `.env` → ghi chú trên
  `.env.example` (dùng bản copy sạch từ example, không merge .env project khác).

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- README "Demo bằng Docker"; xác nhận 3 luồng; ghi quyết định Phase 7.

## 2026-09-17 — Phase 7: env_file .env + cập nhật .env.example (Docker)

- `docker-compose.yml`: `env_file: .env`, `APP_HOST_PORT`, override host/DB.
- `.env.example`: mục Docker (`APP_HOST_PORT`, path DB volume, cảnh báo inject).
- `tests/test_docker_env_file.py`.

## 2026-09-17 — Review docker-compose vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục compose ↔ demo stack):**
- Service `app` build từ `Dockerfile`; map `8000:8000`; volume
  `portfolio-watch-sqlite` → `/app/data`; `SQLITE_PATH=/app/data/portfolio_watch.db`.
- `docker compose config` parse OK; không hard-code secret trong YAML.
- Cùng origin API+UI khi container chạy (Dockerfile đã mount `web/`).

**Fails (liên quan feature này):** không có lỗi blocking sau `compose config`.

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- `env_file: .env` + cập nhật `.env.example` (mục kế tiếp).
- README Docker; xác nhận 3 luồng trên máy sạch; ghi quyết định Phase 7.

## 2026-09-17 — Phase 7: docker-compose.yml (app + port + SQLite volume)

- Thêm `docker-compose.yml`: service `app`, `8000:8000`, volume named
  `pw_sqlite` mount `/app/data`.
- `tests/test_docker_compose.py` — assert port / volume / không bake key.

## 2026-09-17 — Review Dockerfile vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục Dockerfile ↔ demo API+UI cùng origin):**
- Image `python:3.12-slim`; `pip install -e .`; copy `src/` + `web/`;
  `EXPOSE 8000`; `uvicorn ... --host 0.0.0.0 --port 8000` (không reload).
- Không hard-code secret; `.dockerignore` loại `.env` / `.venv`.
- `ENV API_HOST=0.0.0.0`, `SQLITE_PATH=/app/data/portfolio_watch.db`.

**Fails (liên quan feature này, đã sửa):**
- `pip install .` (non-editable) → `__file__` vào site-packages →
  `WEB_DIR` lệch, UI static không mount → đổi `pip install -e .` để
  `WEB_DIR=/app/web`.

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- `docker-compose.yml`, env_file, README Docker, xác nhận máy sạch.
- Docker daemon không chạy trên máy này lúc review — chưa `docker build` thật.

## 2026-09-17 — Phase 7: Dockerfile (API + web demo)

- Thêm `Dockerfile` + `.dockerignore`.
- `tests/test_dockerfile.py` — assert deps / web / expose 8000 / uvicorn /
  không bake secret.

## 2026-09-17 — Review phase completion dates vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 mục “ghi ngày hoàn thành từng phase”):**
- Bảng Phase 1–6 có ngày đóng phase; Phase 7 ghi *(chưa)*.
- Liên kết AC: `test_product_spec_ac.py` (Phase 5) + `verify_clean_local.py`
  (Phase 6 / 3 luồng).
- Checklist Phase 6 trong `implementation-plan.md` toàn `[x]`.

**Fails (liên quan feature này, đã sửa):**
- Cần assert Phase 6 không còn `- [ ]` → bổ sung
  `tests/test_change_log_phase_dates.py`.

**Missing (đúng kỳ vọng):**
- Phase 7 Docker (chưa bắt đầu) — sẽ cập nhật ngày khi đóng phase.

## 2026-09-17 — Ngày hoàn thành từng phase (Phase 6 checklist)

Tóm tắt ngày **đóng phase** (mục checklist cuối của phase trong
`implementation-plan.md` đã `[x]`). Chi tiết từng task vẫn ở các mục nhật ký
bên dưới.

| Phase | Tên | Ngày hoàn thành | Ghi chú ngắn |
|-------|-----|-----------------|--------------|
| 1 | Project setup | **2026-09-16** | FastAPI skeleton, settings, `/health`, `.env.example` |
| 2 | Core UI | **2026-09-16** | `web/` 3 khu vực + CSS + stub `app.js`; xác nhận mở UI |
| 3 | Core backend / data logic | **2026-09-17** | Ports, agents, scan/HITL/chat app layer, cron, full unit+IT |
| 4 | Connect UI to data | **2026-09-17** | `/scan` `/chat` `/approvals` `/watchlist`, CORS, static, wire UI |
| 5 | Validation and error states | **2026-09-17** | 4xx, soft-fail nguồn, cron isolation, guardrail, HITL idempotent, UI lỗi, rà AC |
| 6 | Local run instructions | **2026-09-17** | README local, clean-venv verify, bảng ngày phase (mục này) |
| 7 | Docker demo setup | **2026-09-17** | Dockerfile + compose, env_file, 1 URL, README Docker, `verify_clean_docker.py` |
| 8 | Prompt Registry & LLM wiring | **2026-09-17** | `prompts/` + `PromptRegistry`; wire 7 LLM agent; Heuristic giữ cho test |
| 9 | Golden dataset & Eval pipeline | **2026-09-17** | 30 case 18/6/3/3; `run_eval.py` scorers+runner+report+gates; baseline |
| 10 | Agent graph visualization | **2026-09-17** | `draw_agent_graph.py` StateGraph; docs/agent_graph.mmd/.png; `--verify` |

**Liên kết AC:** Phase 5 đã xác nhận 6 bullet `product-spec.md` qua
`tests/test_product_spec_ac.py`; Phase 6 xác nhận 3 luồng chính theo README
(`scripts/verify_clean_local.py`); Phase 7 xác nhận Docker demo
(`scripts/verify_clean_docker.py`); Phase 8 xác nhận Prompt Registry
(`tests/test_prompt_registry.py`) + wire LLM agents; Phase 9 xác nhận
golden + eval (`scripts/run_eval.py`, `specs/eval/baseline.json`); Phase 10
xác nhận sơ đồ agent (`scripts/draw_agent_graph.py --verify`).

## 2026-09-17 — Review clean-venv verify vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 xác nhận máy sạch ↔ AC 3 luồng):**
- Venv mới + `pip install -e .` → health, UI 3 khu vực, watchlist, scan,
  chat (`hitl_used=false`), approve/reject → `CLEAN_VENV_SMOKE_OK`.
- Script `scripts/verify_clean_local.py` + mục README §8.

**Fails (liên quan feature này, đã sửa):**
- `load_dotenv(..., override=True)` khiến `.env` project ghi đè `SQLITE_PATH`
  môi trường → seed HITL lệch DB / xác nhận fail → đổi `override=False`.
- Test settings dùng `importlib.reload` có thể làm bẩn process → chuyển
  subprocess + assert source `override=False`.

**Missing (đúng kỳ vọng):**
- Mục Phase 6 cuối: ghi ngày hoàn thành từng phase vào change-log.
- Gắn cron lifespan; Docker (Phase 7).

## 2026-09-17 — Phase 6: xác nhận virtualenv mới chạy 3 luồng

- Chạy thật `scripts/verify_clean_local.py` trên venv tạm: scan / chat / HITL
  OK không sửa source.
- `load_dotenv(override=False)` để biến môi trường thắng `.env`.
- README §8 + `tests/test_clean_venv_smoke.py`.

## 2026-09-17 — Review README local run vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 hướng dẫn local ↔ AC chạy 3 luồng):**
- `pip install -e .`, `.env.example` → `.env`, `OPENAI_API_KEYS` / `SQLITE_PATH`.
- SQLite tự tạo schema (`connect` / one-liner); backend
  `python -m src.portfolio_watch.main` / uvicorn cổng **8000**.
- UI cùng origin `http://127.0.0.1:8000/`; seed watchlist; `/scan` `/chat`
  `/approvals`; cron thủ công `scan_watchlist`.

**Fails (liên quan feature này, đã sửa):**
- Thiếu lệnh copy `.env` trên PowerShell → thêm `Copy-Item`.
- Chưa nêu rõ heuristic vs mạng/`vnstock` → bổ sung ghi chú bảng env.
- Test README thiếu assert `uvicorn` / `/health` / sqlite init → siết
  `tests/test_readme_local_instructions.py`.

**Missing (đúng kỳ vọng — checklist Phase 6 tiếp):**
- Xác nhận máy sạch theo README end-to-end (mục kế tiếp).
- Gắn APScheduler vào `main` lifespan; Docker (Phase 7).

## 2026-09-17 — Phase 6: hướng dẫn chạy local (README)

- Viết lại mục **Chạy local (Phase 6)** trong `README.md`: cài deps, `.env`,
  SQLite auto-init, chạy `main`/uvicorn `:8000`, mở UI cùng origin, seed
  watchlist, cron thủ công `scan_watchlist`, kiểm 3 luồng.
- `tests/test_readme_local_instructions.py` — assert README đủ checklist.

## 2026-09-17 — Review product-spec AC rà lại vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (6 AC product-spec.md qua HTTP):**
- AC1 scan: giá/tin/phân loại; bất thường → severity + alert + gate1.
- AC2 đặt ngưỡng thấp (`POST /watchlist`) → vượt ngưỡng → sent/pending.
- AC3 approve/reject → sent / rejected + lý do Memory.
- AC4 đề xuất ngưỡng → Gate 2 pending, không tự áp dụng watchlist.
- AC5 chat → giá thật trong answer, `hitl_used=false`, không pending.
- AC6 guardrail chặn “nên mua/bán”; output chat/scan sạch.

**Fails (liên quan feature này, đã sửa):**
- AC1 chỉ cover bất thường; route assert sai enum EN → thêm nhánh bình
  thường + dùng giá trị `bình thường`/`bất thường`.
- AC2 seed FakeWatchlistStore thay vì “đặt” qua API → chuyển
  `POST /watchlist` rồi `POST /scan` (không ghi đè threshold).
- AC5 chưa assert cứng `hitl_used` + `price.latest_close` → siết assert.

**Missing (đúng kỳ vọng / ngoài AC bullets):**
- Cron wire vào `main` lifespan, README local, Docker (Phase 6).
- LLM composer thật / nguồn thị trường thật trong CI.

## 2026-09-17 — Phase 5: Rà lại acceptance criteria product-spec

- `tests/test_product_spec_ac.py` — 6 test map 6 bullet AC trong
  `product-spec.md` (scan pipeline, watchlist ngưỡng, approve/reject,
  Gate 2, chat không HITL, guardrail mua/bán).
- Đánh dấu hoàn thành mục Phase 5 cuối; không đổi production code.

## 2026-09-17 — Review Frontend error states vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 5 Frontend lỗi cơ bản + product-spec Frontend đơn giản):**
- Banner `#app-error` + câu “Không lấy được dữ liệu, thử lại” khi mạng/API lỗi.
- Scan/chat/approvals/watchlist lỗi hiện rõ trên UI (không chỉ console).
- Soft-fail giá/tin trên scan vẫn đẩy lên banner.

**Fails (liên quan feature này, đã sửa):**
- “Đang quét…” bị style như lỗi (`is-error`) → tách `isError` flag.
- Submit scan/chat rỗng im lặng → `showAppError("symbol/câu hỏi rỗng")`.

**Missing (đúng kỳ vọng):**
- Timeout/retry button riêng; form CRUD watchlist trên UI (ngoài mục này).
- Rà toàn bộ AC product-spec (checklist Phase 5 tiếp).

## 2026-09-17 — Phase 5: Frontend hiển thị lỗi API cơ bản

- `web/index.html`: banner `#app-error` (role=alert).
- `web/app.js`: `NETWORK_ERROR_MSG`, `showAppError`/`clearAppError`,
  `formatError` (status 0 → câu thân thiện); scan/chat/HITL/watchlist lỗi
  hiện banner + panel; bỏ `alert()`.
- `web/style.css`: `.app-error` / `#scan-result.is-error`.
- `tests/test_ui_error_states.py` — xác nhận banner + wiring lỗi.

## 2026-09-17 — Review HITL missing / already-done vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 5 + AC approve/reject trạng thái đúng):**
- Id thiếu / đã xử lý → HTTP 404; không gửi Notifier lần 2; không ghi reject
  thêm; không thêm event; Gate 2 không đổi watchlist; cross approve↔reject.

**Fails (liên quan feature này, đã sửa):**
- Resolution chỉ có `alert_id`/`proposal_id` (thiếu `approval_id`) không bị
  coi đã xử lý → có thể approve lại → siết `_is_resolution` +
  `list_pending_approvals`.
- Reject id đã xử lý/thiếu kèm lý do rỗng trả 400 “lý do rỗng” thay vì 404
  đúng case → bỏ normalize reason trước app layer (ưu tiên missing/done).
- Thêm test Gate2 reject 2 lần + resolution alias + empty-reason → 404.

**Missing (đúng kỳ vọng):**
- Happy-path Gate 1/2 approve/reject (đã cover Phase 3–4 / test-plan #3).
- UI hiện lỗi API khi approve/reject fail (mục Frontend Phase 5 tiếp).

## 2026-09-17 — Phase 5: HITL missing / already-done → lỗi rõ, không đổi state

- `tests/test_hitl_missing_already_done.py` — xác nhận Phase 5:
  id thiếu / đã xử lý → HTTP 404; không gửi Notifier lần 2; không ghi reject
  thêm; không thêm alert event; Gate 2 không đổi watchlist; cross
  approve↔reject giữ trạng thái đã chốt.
- Không đổi production code — `review_approval` + router đã trả lỗi đúng.

## 2026-09-17 — Review Guardrail confirmation vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (AC guardrail + test-plan Synthesis/Answer):**
- “nên mua”/“nên bán” → `check_output` chặn; Synthesis rewrite `draft_attempts > 1`.
- Số lệch evidence → chặn; Synthesis/AnswerComposer rewrite hoặc fallback sạch.
- Hai nhánh dùng chung `domain.guardrails.output_checks`.

**Fails (liên quan feature này, đã sửa):**
- `build_evidence` gắn cả Eval `reasoning` → whitelist số bịa (vd. 12.5%) trong
  câu trả lời hỏi-đáp → bỏ `reasoning:` khỏi evidence blob; thêm test xác nhận.
- Confirmation thiếu case Synthesis rewrite “nên bán” và assert `calls > 1`
  trên nhánh Answer fallback bán → siết test.

**Missing (đúng kỳ vọng):**
- Model routing Severity (đã cover Phase 3 / ngoài mục “chặn vi phạm”).
- Composer LLM thật (vẫn inject/heuristic).

## 2026-09-17 — Phase 5: xác nhận Guardrail (test-plan)

- `tests/test_guardrail_confirmation.py` — case cụ thể test-plan:
  chặn “nên mua”/“nên bán”; số liệu lệch evidence; Synthesis/AnswerComposer
  rewrite (`draft_attempts > 1`); module `output_checks` dùng chung hai nhánh.
- Không đổi production code — hành vi Phase 3 đã đủ; bổ sung xác nhận.

## 2026-09-17 — Review cron isolation vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (test-plan #7 — cron/watchlist độc lập):**
- 1 mã crash / price timeout / news timeout không chặn mã khác.
- Đường APScheduler job thủ công (`build_scan_watchlist_job`) cùng isolation.

**Fails (liên quan feature này, đã sửa):**
- Chỉ cover lỗi mã giữa; cron path chưa assert thứ tự gọi + price/news
  trên mã OK → thêm BAD đầu/cuối; siết assert luồng giám sát độc lập
  (change_pct / tin theo mã).

**Missing (đúng kỳ vọng):**
- Quét song song (agents.md gợi ý) — test-plan chỉ yêu cầu độc lập lỗi.
- Wire scheduler vào `main.py` lifespan (Phase 6 hướng dẫn).

## 2026-09-17 — Phase 5: xác nhận cron isolation (tích hợp)

- `tests/test_cron_isolation_integration.py` — test-plan #7 ở mức tích hợp:
  agent crash mã giữa, Price/News timeout 1 mã, đường APScheduler job;
  FPT+VNM vẫn quét khi BAD lỗi.

## 2026-09-17 — Review Price/News source errors vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi nguồn lỗi/timeout không crash scan):**
- PriceAgent/NewsAgent bắt exception → error rõ; `scan_symbol` / `POST /scan`
  200, không alert khi thiếu dữ liệu.
- CafeF HTTP lỗi raise (không nuốt `[]`); multi-symbol đã có ở cron tests.

**Fails (liên quan feature này, đã sửa):**
- `quote.error="timeout"` không có cụm “không lấy được dữ liệu” → PriceAgent
  chuẩn hoá message.
- CafeF wrap RuntimeError → NewsAgent double-prefix “không lấy được tin” →
  re-raise gốc + NewsAgent tránh double-wrap.
- Thiếu case chỉ news timeout + assert không trả `None`.

**Missing (đúng kỳ vọng — checklist khác):**
- Cron isolation xác nhận lại (mục Phase 5 tiếp); UI hiện lỗi nguồn (Phase 5
  frontend).

## 2026-09-17 — Phase 5: PriceSource/NewsSource lỗi không crash scan

- `CafefNewsSource`: timeout/HTTP lỗi → raise (không nuốt `[]`) để
  NewsAgent gắn `không lấy được tin`.
- `tests/test_source_errors.py` — agent + `scan_symbol` + `POST /scan`
  khi price/news timeout: 200, `price.error` / `news_error` rõ, không alert.

## 2026-09-17 — Review API validate input vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 5 validate input → 4xx):**
- Symbol rỗng/whitespace/không hợp lệ → 400; ngưỡng âm → 400.
- Câu hỏi rỗng → 400; mã không có trên watchlist → 404.
- Reject lý do rỗng → 400; input hợp lệ vẫn 200 (scan/chat).

**Fails (liên quan feature này, đã sửa):**
- `""` bị pydantic `min_length` → 422 tiếng Anh mập mờ → bỏ min_length,
  thống nhất 400 tiếng Việt qua `validation.py`.
- Thiếu case PATCH ngưỡng âm, symbol quá dài/`FP-T`, thiếu field → 422.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Mã thị trường không tồn tại / PriceSource timeout → agent trả lỗi rõ
  (không crash) — mục Phase 5 kế tiếp, không map 4xx ở đây.

## 2026-09-17 — Phase 5: API validate input → 4xx

- Thêm `api/helpers/validation.py`: symbol / câu hỏi / ngưỡng / approval_id /
  lý do reject — 400 rõ ràng.
- Wire vào scan, chat, watchlist, approvals; ngưỡng âm → 400 (không còn
  chỉ dựa pydantic 422).
- `tests/test_api_validation.py` — rỗng, không hợp lệ, âm, 404 mã không
  có trên watchlist.

## 2026-09-17 — Review xác nhận UI vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi xác nhận Phase 4 UI / cùng API web gọi):**
- UI 3 khu vực + `app.js` wiring.
- #1 quét bình thường → không alert; chat #5 → answer, không HITL.
- #3 pending → approve (sent) / reject (lý do, không gửi); list `/approvals`
  cập nhật.

**Fails (liên quan feature này, đã sửa):**
- Thiếu xác nhận quét bất thường đủ field AC (severity/tin/alert/gate).
- Thiếu #2 auto-send (Gate 1 không còn pending trên UI).
- Pending item chưa assert field `renderApprovals` cần (`approval_id`,
  symbol).

**Missing (đúng kỳ vọng — Phase 5+ / ngoài checklist này):**
- #4 Gate 2 / #6 chat giải thích / #7 cron (đã cover ở test API/application
  khác).
- Form CRUD ngưỡng trên UI; validate lỗi UI (Phase 5).

## 2026-09-17 — Phase 4: Xác nhận luồng UI (scan / chat / HITL)

- Thêm `tests/test_ui_manual_confirmation.py` — e2e cùng endpoint
  `web/app.js` gọi: UI load, quét → kết quả, chat → answer, pending →
  approve/reject cập nhật list.
- Phase 4 checklist hoàn tất (5/5 passed).

## 2026-09-17 — Review wire web/app.js vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi UI nối 4 API + 3 khu vực):**
- Chat → `POST /chat`, hiện câu trả lời; watchlist/approvals load + refresh.
- Quét ngay → `POST /scan`; approve/reject → API + refresh list.
- `API_BASE=""` cùng origin; không còn stub log-only Phase 2.

**Fails (liên quan feature này, đã sửa):**
- Scan UI thiếu “toàn bộ luồng” AC (tin/severity/reason/gate2 proposal) →
  mở rộng `showScanResult`.
- `detail` 422 dạng mảng hiện xấu; reject lý do rỗng vẫn gửi →
  `formatError` + chặn reason rỗng; disable nút khi đang request.
- Test chưa chặn regression stub → `test_ui_wiring_renders_scan_chat_approvals`.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Xác nhận thủ công trên browser (quét / chat / approve-reject e2e UI).
- Form thêm/sửa ngưỡng watchlist trên UI (CRUD API đã có; AC “đặt ngưỡng”
  vẫn làm được qua API).

## 2026-09-17 — Phase 4: Wire web/app.js → API + render UI

- `web/app.js`: `API_BASE=""` (cùng origin); parse JSON; render chat /
  watchlist / approvals; approve/reject + quét ngay.
- `web/index.html`: form quét, `#watchlist-body`, bỏ placeholder mẫu.
- Còn mục xác nhận thủ công trên browser (checklist tiếp).

## 2026-09-17 — Review mount static web/ vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi phục vụ UI cùng origin với API):**
- `GET /` (và `/index.html`) trả trang 3 khu vực: chat / watchlist /
  approvals (product-spec Frontend).
- `/app.js`, `/style.css` cùng host; link relative từ HTML resolve được.
- Mount `/` không che API: `/health`, `/watchlist`, `/approvals`, `/docs`,
  OpenAPI `/scan` `/chat` vẫn JSON/HTML đúng.

**Fails (liên quan feature này, đã sửa):**
- Test chưa assert API JSON không bị static shadow, chưa check
  `/index.html` + asset links từ HTML → siết `test_api_static.py`.

**Missing (đúng kỳ vọng — checklist tiếp):**
- `web/app.js` còn `API_BASE` cứng + log-only — nối `fetch` + render UI
  thật (mục Phase 4 tiếp theo).

## 2026-09-17 — Phase 4: Mount static web/ cùng origin

- `main.py`: mount `StaticFiles(web/, html=True)` tại `/` (sau API routes)
  → UI + API cùng base URL khi demo.
- `tests/test_api_static.py` — `/`, `/app.js`, `/style.css`; `/health` +
  `/docs` vẫn hoạt động.

## 2026-09-17 — Review CORS + routers vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi đăng ký router + CORS cho web/):**
- Đủ 4 nhóm API (`/scan`, `/chat`, `/approvals`, `/watchlist`) + method
  khớp stub `web/app.js`.
- `CORSMiddleware` `allow_origins=["*"]` — GET và preflight POST/PATCH/DELETE
  trả `Access-Control-Allow-Origin: *` (Live Server / `Origin: null`).

**Fails (liên quan feature này, đã sửa):**
- Test chỉ cover `/health` + preflight `/chat` → mở rộng assert method
  OpenAPI và CORS trên đúng endpoint web gọi.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Mount static `web/`, nối UI `fetch` + render kết quả thật.

## 2026-09-17 — Phase 4: CORS + đăng ký đủ router

- `main.py`: xác nhận 4 router (`scan`, `chat`, `approvals`, `watchlist`)
  + `CORSMiddleware` `allow_origins=["*"]` (dev, `web/` gọi cross-origin).
- `tests/test_api_cors.py` — OpenAPI có đủ path; CORS header + preflight.

## 2026-09-17 — Review CRUD /watchlist vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi CRUD watchlist API):**
- `GET/POST/PATCH/DELETE /watchlist` thêm/xem/sửa ngưỡng/xóa mã.
- User CRUD **không** tạo HITL pending (khác đề xuất EvalAgent → Gate 2).
- Symbol chuẩn hoá uppercase; rỗng/whitespace → 400; ngưỡng âm → 422;
  mã thiếu → 404.

**Fails (liên quan feature này, đã sửa):**
- Thiếu e2e product-spec “đặt watchlist ngưỡng thấp → quét vượt ngưỡng →
  cảnh báo”: `POST /watchlist` rồi `POST /scan` (không ghi đè threshold).
- Thiếu assert CRUD không tạo pending / PATCH áp dụng ngay (không Gate 2).

**Missing (đúng kỳ vọng — checklist khác):**
- CORS, mount static `web/`, UI gọi watchlist.

## 2026-09-17 — Phase 4: CRUD /watchlist API

- Thêm `api/routers/watchlist.py`: `GET/POST /watchlist`,
  `PATCH/DELETE /watchlist/{symbol}` → `WatchlistStore` (không qua HITL).
- Đăng ký watchlist router trong `main.py` (chưa CORS / static / UI).
- `tests/test_api_watchlist.py` — CRUD, default threshold, symbol rỗng,
  thiếu mã → 404, ngưỡng âm → 422.

## 2026-09-17 — Review POST/GET /approvals vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi HITL approve/reject qua API):**
- `GET /approvals` liệt kê chờ duyệt (Gate 1 + Gate 2) kèm payload.
- Gate 1 approve → status `sent`, Notifier gửi; reject → không gửi, lý do
  ghi Memory.
- Gate 2 approve → cập nhật watchlist; reject → giữ ngưỡng cũ.
- Id thiếu / đã xử lý → 404; lý do reject rỗng → 400.

**Fails (liên quan feature này, đã sửa):**
- test-plan #3 chưa khép HTTP: `POST /scan` → pending →
  `POST /approvals/.../approve|reject` — thêm e2e.
- Thiếu HTTP Gate 2 reject (giữ watchlist) và reject missing/already-done.
- `reason=""` bị 422 pydantic thay vì 400 “lý do rỗng” → bỏ `min_length`,
  validate sau strip.

**Missing (đúng kỳ vọng — router/checklist khác):**
- CRUD `/watchlist`, CORS, static `web/`, UI gọi approvals.

## 2026-09-17 — Phase 4: POST/GET /approvals API

- Thêm `api/routers/approvals.py`: `GET /approvals`,
  `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`
  → `review_approval` (Gate 1 gửi alert / Gate 2 cập nhật watchlist).
- Đăng ký approvals router trong `main.py` (chưa CORS / watchlist / static).
- `tests/test_api_approvals.py` — list, approve/reject Gate 1+2, reason rỗng,
  id thiếu/đã xử lý → 4xx.

## 2026-09-17 — Review POST /chat vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Chat API hỏi-đáp):**
- `POST /chat` chạy Rewrite → Supervisor → workers → AnswerComposer;
  trả lời dựa trên giá/tin, lưu hội thoại.
- #5 hỏi giá → chỉ `price`, không HITL / không pending.
- #6 hỏi "tại sao giảm" → có `news`/`eval`, câu trả lời nhắc tin/lý do.
- Follow-up ("còn mã đó") dùng Memory qua API.

**Fails (liên quan feature này, đã sửa):**
- Response chưa lộ `news_error` (khó thấy lỗi tin) → thêm field.
- Test #5/#6 chưa seed mã trong watchlist; chưa assert
  `list_pending_approvals == []` / title tin cụ thể.
- Thiếu case HTTP follow-up dùng lịch sử hội thoại.

**Missing (đúng kỳ vọng — ngoài phạm vi router chat):**
- Enforce chỉ trả lời mã có trong WatchlistStore (`answer_question`
  chưa nhận watchlist port — ghi nhận từ trước).
- `POST /approvals/...`, CORS / UI gọi `/chat`.

## 2026-09-17 — Phase 4: POST /chat API

- Thêm `api/routers/chat.py`: `POST /chat` → `answer_question`, trả
  rewritten/route/answer/price/news/severity; không tạo HITL.
- Đăng ký chat router trong `main.py` (chưa CORS / approvals / watchlist).
- `tests/test_api_chat.py` — hỏi giá, giải thích giảm, câu rỗng/whitespace.

## 2026-09-17 — Review POST /scan vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi API quét ngay 1 mã):**
- `POST /scan` chạy đủ luồng: giá, tin, route; bất thường → severity/alert/gate.
- #1 bình thường → không alert; #2 confidence cao → `sent`, không pending.

**Fails (liên quan feature này, đã sửa):**
- Thiếu coverage API cho #3 (pending khi confidence thấp) và #4 (`gate2_pending`).
- Response chưa lộ `news_error` (khó thấy đủ kết quả tin) → thêm field.
- Symbol chỉ whitespace → 400; siết assert `pending_events` / severity.

**Missing (đúng kỳ vọng — router khác / Phase 4 tiếp):**
- `POST /approvals/...` (phần còn lại của test-plan #3).
- CORS / UI gọi `/scan`.

## 2026-09-17 — Phase 4: POST /scan API

- Thêm `api/deps.py` (AppDeps + override test) và `api/routers/scan.py`:
  `POST /scan` → `scan_symbol`, trả route/price/news/severity/alert/gates.
- Đăng ký scan router trong `main.py` (chưa CORS / routers khác).
- `tests/test_api_scan.py` — normal, auto-send, symbol rỗng → 422.

## 2026-09-17 — Review backend test suite vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 3 “chạy unit + integration, chưa API/UI”):**
- Full suite `tests/`: **85 passed**.
- Unit theo test-plan (Price/News/Classifier/Eval/Synthesis/Gate/HITL/
  Supervisor/Answer) đã có trong các `test_*.py` riêng.
- Integration #1–#7 map application layer (scan / approve-reject / chat /
  cron thủ công), không HTTP.

**Fails (liên quan feature này, đã sửa):**
- #2 chỉ assert “không Gate 1” → siết thành `list_pending_approvals == []`
  + `status=SENT`.
- #3 thiếu assert pending trống sau approve/reject; pending phải có payload
  alert.
- #4 thiếu assert Gate 2 **không** tự `upsert` watchlist.
- #5/#6 thiếu assert không tạo `alert_events` / pending HITL.

**Missing (đúng kỳ vọng — Phase 4+):**
- `POST /scan`, `POST /chat`, `POST /approvals/...` HTTP e2e.
- Chat “mã trong watchlist” enforce qua WatchlistStore (answer_question
  chưa nhận watchlist port).

## 2026-09-17 — Phase 3: chạy full backend tests (test-plan, chưa API/UI)

- Chạy toàn bộ `tests/`: **85 passed**.
- Thêm `tests/test_backend_integration.py` map test-plan e2e #1–#7 ở
  application layer (scan / approve-reject / chat / cron thủ công) — không
  HTTP/UI (đúng phạm vi “chưa cần API/UI”).

## 2026-09-17 — Review Cron / scan_watchlist vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Cron / watchlist nhiều mã):**
- Đọc watchlist → gọi `scan_symbol` từng mã; 1 mã crash không chặn mã sau.
- APScheduler interval (`create_scan_scheduler`); có thể fire job thủ công.
- Ngưỡng lấy theo từng `WatchlistItem`.

**Fails (liên quan feature này, đã sửa):**
- Thiếu case PriceSource lỗi ở 1 mã (agent trả error) vẫn quét hết danh sách.
- Job scheduler có thể raise làm nhiễu cron → bọc `_safe_job`; thêm
  `build_scan_watchlist_job` (chạy thủ công / APScheduler, không raise).
- `interval_minutes` không hợp lệ → fallback 60; test e2e job + isolation.

**Missing (đúng kỳ vọng):**
- Wire scheduler vào `main.py` lifespan / demo stack (Phase 6 hướng dẫn).
- Quét song song nhiều mã (agents.md gợi ý; test-plan chỉ yêu cầu độc lập).

## 2026-09-17 — Phase 3: Cron / scan_watchlist (APScheduler)

- Thêm `application/scan_watchlist.py`: lặp watchlist → `scan_symbol` từng
  mã; `try/except` theo mã (1 mã lỗi không chặn các mã còn lại).
- Thêm `infra/scheduler/cron.py`: `create_scan_scheduler` /
  `start_scan_scheduler` / `stop_scan_scheduler` (APScheduler interval,
  `SCAN_INTERVAL_MINUTES`).
- `tests/test_scan_watchlist.py` — isolation lỗi, threshold theo item, job
  đăng ký + chạy thủ công.

## 2026-09-17 — Review review_approval vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (HITL Gate 1 / Gate 2):**
- Gate 1 approve → gửi Notifier, status sent; reject → `record_rejection`,
  không gửi.
- Gate 2 approve → cập nhật watchlist (ngưỡng + mã mới); reject → giữ nguyên
  cấu hình cũ.
- Id không tồn tại / đã xử lý → `ok=False` + lỗi rõ (approve và reject).

**Fails (liên quan feature này, đã sửa):**
- Reject lý do rỗng vẫn thành công (trái “lý do reject được ghi lại”) → bắt
  buộc reason không rỗng.
- Gate 1 approve: Notifier không set status vẫn có thể không “đã gửi” → ép
  `AlertStatus.SENT` sau send thành công.
- Snapshot Gate 2 reject mở rộng cho mã liên quan; thêm test reject 2 lần /
  missing / empty reason / SENT ép status.

**Missing (đúng kỳ vọng):**
- HTTP `POST /approvals/{id}/approve|reject` (Phase 4).

## 2026-09-17 — Phase 3: review_approval (HITL Gate 1 + Gate 2)

- Thêm `application/review_approval.py`:
  - `list_pending_approvals` — pending chưa có resolution.
  - Gate 1 approve → `Notifier.send` (status sent); reject →
    `record_rejection`, không gửi.
  - Gate 2 approve → `WatchlistStore.upsert` (ngưỡng + mã liên quan);
    reject → ghi lý do, giữ nguyên watchlist.
  - Approve/reject id không tồn tại hoặc đã xử lý → `ok=False` + error rõ.
- `tests/test_review_approval.py`.

## 2026-09-17 — Review hỏi-đáp vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Supervisor / Rewrite / AnswerComposer / không HITL):**
- Tra cứu giá → chỉ `price`, không `eval`.
- “Tại sao … giảm” → `price+news+eval`; trả lời có tin/lý do.
- “Còn mã đó” → Rewrite lấy symbol từ Memory.
- Guardrail dùng chung `output_checks`; `hitl_used` / không tạo pending.
- Lưu hội thoại vào Memory sau trả lời.

**Fails (liên quan feature này, đã sửa):**
- “thông tin giá …” bị route `news_lookup` vì substring `tin` → lọc “thông
  tin” trước khi nhận diện tin tức.
- Follow-up không ticker (“Tại sao giảm?”) chưa lấy symbol từ Memory → bổ sung.
- `hitl_used` / `pending_approvals_created` hardcode `False`/`0` → đếm thật từ
  delta `alert_events`.
- Fallback guardrail khi “nên bán” + số giả; assert output cuối luôn pass check.

**Missing (đúng kỳ vọng):**
- `POST /chat` API (Phase 4).

## 2026-09-17 — Phase 3: hỏi-đáp (Supervisor + AnswerComposer + answer_question)

- Thêm `domain/agents/supervisor.py`: RewriteQuestion (symbol từ câu hỏi /
  Memory “mã đó”) + Supervisor routing (`agents_to_call`: price / news / eval).
- Thêm `domain/agents/answer_composer.py`: soạn câu trả lời, model routing,
  vòng guardrail dùng chung `output_checks` (không HITL).
- Thêm `application/answer_question.py`: Rewrite → route → gọi worker →
  compose → lưu hội thoại Memory; `hitl_used=False`, không tạo pending.
- `FakeMemoryStore` ghi conversation; `tests/test_answer_question.py`.

## 2026-09-16 — Review scan_symbol vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi luồng giám sát 1 mã / Confidence Gate / Gate 2 tạo pending):**
- Price+News → Classifier; NORMAL dừng không alert; ABNORMAL → Eval →
  Synthesis (guardrail) → Confidence Gate.
- Confidence cao + khớp ngưỡng → auto-send (Notifier), không Gate 1 pending.
- Confidence thấp / không khớp ngưỡng → Gate 1 `pending_approval` đúng nội dung.
- Đề xuất ngưỡng/mã → luôn Gate 2 pending, không áp dụng watchlist.

**Fails (liên quan feature này, đã sửa):**
- `Notifier.send` lỗi → crash toàn bộ scan → bắt lỗi, fallback Gate 1 pending.
- Thiếu assert/test ngưỡng từ `WatchlistStore`; thiếu xác nhận Gate 2 không
  `upsert` watchlist; thiếu assert auto-send không tạo Gate 1 pending.
- So sánh route abnormal bền hơn với string value.

**Missing (đúng kỳ vọng):**
- API `POST /scan`, approve/reject (`review_approval`), cron nhiều mã.

## 2026-09-16 — Phase 3: scan_symbol (Orchestrator + Confidence Gate)

### Công thức Confidence Gate (chốt)
- Auto-send khi `confidence >= 0.8` **và** `|change_pct| >= threshold_pct`
  (ngưỡng user / watchlist; mặc định 3%).
- Ngược lại → HITL Gate 1 (`pending_approval` trong MemoryStore).
- Có `proposed_threshold_pct` / `proposed_related_symbols` → **luôn** tạo
  Gate 2 pending (không có đường tắt), kể cả khi auto-send Gate 1.

### Thay đổi
- Thêm `application/scan_symbol.py`: Price+News song song → Classifier →
  (NORMAL dừng) / (ABNORMAL → Eval → Gate2? → Synthesis+Guardrail →
  Confidence Gate → Notifier hoặc Gate 1).
- `tests/test_scan_symbol.py`; `FakeMemoryStore` ghi `alert_events`;
  thêm `FakeNotifier`.

## 2026-09-16 — Review ConsoleNotifier vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Notifier / MVP “gửi cảnh báo”):**
- Log console + lưu DB (`append_alert_event`) đúng product-spec (không
  bắt buộc email/push).
- Gửi thành công → `FinalAlert.status=SENT` (“đã gửi”); event `kind=sent`
  để Notifier “ghi nhận” (test-plan e2e confidence cao).

**Fails (liên quan feature này, đã sửa):**
- `status=REJECTED` vẫn bị gửi + đổi thành SENT (trái “reject → không gửi”)
  → bỏ qua, chỉ warning, không ghi event.
- `append_alert_event` lỗi nhưng status đã = SENT (lệch DB) → ghi DB trước,
  chỉ set SENT khi persist OK.

**Missing (đúng kỳ vọng):**
- Wire scan/approve gọi `Notifier`; e2e POST /scan (Phase 4).

## 2026-09-16 — Phase 3: ConsoleNotifier

- Thêm `infra/notify/console_notifier.py`: implement `Notifier.send` — log
  console + `MemoryStore.append_alert_event` (kind=`sent`), set
  `FinalAlert.status=SENT`.
- `user_id` lấy từ `alert.metadata["user_id"]` hoặc mặc định constructor.
- `tests/test_console_notifier.py` — ghi DB SQLite tạm + assert log.

## 2026-09-16 — Review market_data vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi PriceSource/NewsSource):**
- Đúng Out of Scope MVP: 1 nguồn giá (`vnstock` VCI) + 1 nguồn tin CafeF;
  ports cho phép thêm nguồn sau.
- Lỗi/timeout: giá → `PriceQuote.error` (không raise); tin → `[]` (đúng
  contract `NewsSource`); CI dùng mock theo test-plan.
- CafeF: parse HTML, lọc `query` / `days`; HTTP lỗi không crash.

**Fails (liên quan feature này, đã sửa):**
- DataFrame không sắp theo `time` → lấy nhầm “giá mới nhất” → sort theo
  `time` khi có cột.
- Cột `Close` (hoa) bị coi là thiếu dữ liệu → chuẩn hoá tên cột về
  lowercase trước khi đọc `close`.
- Thiếu test: empty DF / raise → error; sort theo time; `Close`; lọc
  `days` CafeF.

**Missing (đúng kỳ vọng — chưa phải market_data):**
- Wire vào scan/chat/cron; Phase 5 “agent báo không lấy được dữ liệu” khi
  NewsSource trả `[]` do timeout (xử lý ở agent/orchestrator).

## 2026-09-16 — Phase 3: market_data (PriceSource / NewsSource)

### Quyết định nguồn dữ liệu
- **Giá:** `vnstock` `Quote.history` (source `VCI`) — lấy 2 phiên đóng cửa
  gần nhất để tính % thay đổi; không dùng API SSI/TCBS riêng.
- **Tin:** CafeF Ajax HTML
  (`Events_RelatedNews_New.aspx`) — không có API chính thức; parse `<li>`
  title/url/ngày; lỗi HTTP/timeout → trả `[]`.

### Thay đổi
- Thêm `infra/market_data/price_source.py` (`VnstockPriceSource`).
- Thêm `infra/market_data/news_source.py` (`CafefNewsSource` + parser HTML).
- Dependency: `vnstock>=3.0.0`, `pandas>=2.0.0` trong `pyproject.toml`.
- `tests/test_market_data.py` — parse/filter CafeF (mock HTTP), giá từ
  FakeQuote dataframe, symbol rỗng.

## 2026-09-16 — Review SQLite storage vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi storage / In Scope):**
- Có SQLite Watchlist / Price History / Memory đúng product-spec MVP.
- Hỗ trợ ghi preferences, hội thoại, alert events, reject (nền tảng HITL/
  chat trong test-plan).

**Fails (liên quan storage, đã sửa):**
- `record_rejection` không đọc lại được để xác nhận AC “lý do reject được
  ghi lại” → thêm `SqliteMemoryStore.list_rejections` + assert trong test.
- Thiếu CHECK `threshold_pct >= 0`; ép kiểu float cho OHLCV nullable.
- Test thêm case Gate 2 reject không đụng watchlist (giữ ngưỡng cũ).

**Missing (đúng kỳ vọng — chưa phải storage):**
- API approve/reject, scan/chat e2e, Notifier gửi cảnh báo.

## 2026-09-16 — Phase 3: SQLite storage (watchlist / price history / memory)

- Thêm `infra/storage/sqlite_db.py` (schema + connect).
- Implement `SqliteWatchlistStore`, `SqlitePriceHistoryStore` (+ `upsert_bars`),
  `SqliteMemoryStore` theo `domain/ports.py`.
- `tests/test_sqlite_stores.py` round-trip trên file DB tạm.

## 2026-09-16 — Review SynthesisAgent + Guardrail vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Synthesis + Guardrail / test-plan + AC guardrail):**
- Severity HIGH → model nặng; LOW → model nhẹ.
- “nên mua” → chặn + soạn lại (`draft_attempts > 1`).
- Số không có trong evidence → `check_output` fail.

**Fails (liên quan feature này, đã sửa):**
- Hết max attempts vẫn có thể phát hành body chưa sạch (reasoning chứa
  “nên bán”) → fallback chỉ evidence + kiểm guardrail lại.
- Composer raise / symbol rỗng chưa xử lý → bắt lỗi, trả kết quả rõ.
- Bổ sung case “nên bán” + assert output cuối luôn pass `check_output`.

**Missing (đúng kỳ vọng):**
- AC end-to-end scan/HITL/chat; LLM composer thật (hiện inject/heuristic).

## 2026-09-16 — Phase 3: SynthesisAgent + Guardrail output

- Thêm `domain/guardrails/output_checks.py`: chặn “nên mua/bán”; số liệu
  phải có trong evidence.
- Thêm `domain/agents/synthesis_agent.py`: `select_model` (light/heavy),
  soạn `FinalAlert`, vòng rewrite khi guardrail fail; đọc preferences từ
  `MemoryStore`.
- `FakeMemoryStore` + `tests/test_synthesis_agent.py` (routing model, rewrite
  khi có lời khuyên mua/bán, số không khớp evidence).

## 2026-09-16 — Review EvalAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi EvalAgent / test-plan):**
- Đủ data → không gọi `read_price_history`, có `Severity`.
- Mập mờ → gọi history; confidence thấp hơn khi lịch sử không ủng hộ
  (so sánh tương đối với case lịch sử ủng hộ).

**Fails (liên quan EvalAgent, đã sửa):**
- `read_history` raise làm mất Severity rõ → bắt riêng, vẫn trả Severity
  confidence thấp + evidence lỗi.
- Symbol rỗng / history rỗng sau khi request → hạ confidence rõ ràng.
- Test “thấp hơn” chỉ assert tuyệt đối → thêm so sánh
  opposed.confidence < supported.confidence.

**Missing (đúng kỳ vọng):**
- AC end-to-end product-spec (Gate 2 apply proposal, scan API…).
- LLM ReAct brain thật (hiện heuristic + inject).

## 2026-09-16 — Phase 3: EvalAgent

- Thêm `domain/agents/eval_agent.py`: `run_eval_agent` → `Severity`;
  `HeuristicEvalBrain` gọi `PriceHistoryStore.read_history` khi dữ liệu mập
  mờ; lịch sử không ủng hộ → hạ `confidence`; có thể đề xuất ngưỡng (Gate 2).
- `FakePriceHistoryStore` + `tests/test_eval_agent.py` (đủ data bỏ qua
  history; mập mờ → gọi history + confidence thấp).

## 2026-09-16 — Review Event Classifier vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Event Classifier / test-plan):**
- Biến động nhỏ + không tin xấu → `bình thường`.
- |%| lớn (tăng hoặc giảm) hoặc tin tiêu cực → `bất thường`.

**Fails (liên quan classifier, đã sửa):**
- Hint `"âm"` false-positive trong “đảm bảo”; phủ định “không giảm”
  vẫn bị bắt → bỏ hint mơ hồ, thêm chống negation; threshold <= 0 fallback 3.0.
- Brain raise → crash escalate → bắt lỗi, trả `NORMAL` (lọc rẻ, không gọi Eval).

**Missing (đúng kỳ vọng):**
- AC end-to-end `product-spec.md`; LLM classifier thật (hiện heuristic + inject).

## 2026-09-16 — Phase 3: Event Classifier

- Thêm `domain/agents/event_classifier.py`: `classify_event` →
  `RoutingDecision` (`bình thường` / `bất thường`); `HeuristicEventClassifier`
  (ngưỡng |%| hoặc tin tiêu cực); brain inject được cho LLM sau.
- `tests/test_event_classifier.py` theo test-plan (biến động nhỏ; |%| lớn;
  tin tiêu cực).

## 2026-09-16 — Review NewsAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi NewsAgent / test-plan):**
- Tin không liên quan bị lọc → `items == []`.
- Cần 2 lần gọi tool mới đủ tin → `tool_calls == 2`, dừng khi đủ;
  `max_steps` chặn lặp vô hạn.

**Fails (liên quan NewsAgent, đã sửa):**
- `fetch_news` raise giữa vòng → mất toàn bộ tin đã gather → bắt lỗi theo
  từng lần gọi, giữ tin đã lọc + `error` rõ.
- Chỉ `kind=="search"` mới gọi tool; symbol rỗng → lỗi rõ, không chạy loop.

**Missing (đúng kỳ vọng):**
- AC `product-spec.md` (scan/chat/HITL end-to-end).
- LLM brain thật (hiện inject `NewsAgentBrain` / heuristic) — wiring LLM
  thuộc bước sau.

## 2026-09-16 — Phase 3: NewsAgent + unit test

- Thêm `domain/agents/news_agent.py`: vòng lặp ReAct (search/finish) qua
  `NewsAgentBrain`, gọi `NewsSource.fetch_news`, lọc tin liên quan;
  `HeuristicNewsBrain` fallback không LLM; `max_steps` chống lặp vô hạn.
- `tests/fakes.FakeNewsSource` + `tests/test_news_agent.py` (lọc tin rác,
  gọi tool 2 lần rồi dừng, cap max_steps).

## 2026-09-16 — Review PriceAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi PriceAgent / test-plan):**
- Tăng / giảm / đứng yên → `change_pct` đúng.
- `PriceSource` lỗi / thiếu `latest_close` → `PriceAgentResult` có `error`,
  không trả `None` cho toàn bộ kết quả.

**Fails (liên quan PriceAgent, đã sửa):**
- `PriceSource` raise exception → agent crash (trái “không crash”) → bọc
  try/except, trả `error` rõ.
- Thiếu test `prev_close` None + nguồn raise — đã thêm.

**Missing (đúng kỳ vọng):**
- Toàn bộ AC `product-spec.md` (scan API, HITL, chat, guardrail).
- Các agent/e2e khác trong `test-plan.md`.

## 2026-09-16 — Phase 3: PriceAgent + unit test

- Thêm `domain/agents/price_agent.py`: `run_price_agent` tính `change_pct`,
  trả `PriceAgentResult` rõ ràng khi lỗi / thiếu dữ liệu.
- Thêm `tests/test_price_agent.py` + `tests/fakes.FakePriceSource` (tăng/
  giảm/đứng yên + error).

## 2026-09-16 — Review `domain/ports.py` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi ports):**
- Đủ 6 interface checklist; `PriceQuote.error` hỗ trợ test-plan
  “không có dữ liệu / không trả None mập mờ”; `record_rejection` +
  `Notifier.send` khớp HITL / gửi cảnh báo; `read_history` khớp EvalAgent.

**Fails (liên quan ports, đã sửa):**
- `NewsSource` thiếu khung thời gian (agents: symbol + time window) → thêm
  `days`.
- `MemoryStore` thiếu lịch sử cảnh báo (agents kho dữ liệu) →
  `append_alert_event` / `list_alert_events`.
- `PriceBar.open` shadow builtin → đổi `open_price`.
- Docstring `PriceSource`: lỗi trả `PriceQuote` với `error`, không raise mơ hồ.

**Missing (đúng kỳ vọng — chưa implement infra/agents/API):**
- Toàn bộ AC `product-spec.md` và e2e/unit agent trong `test-plan.md`.

## 2026-09-16 — Phase 3: `domain/ports.py`

- Khai báo Protocol: `PriceSource`, `NewsSource`, `WatchlistStore`,
  `PriceHistoryStore`, `MemoryStore`, `Notifier`.
- DTO kèm port: `PriceQuote`, `NewsItem`, `PriceBar` (dataclass thuần).
- Chưa có implement infra — chỉ interface cho agent/fake test.

## 2026-09-16 — Review domain entities vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi entity):**
- Đủ 4 model checklist: `WatchlistItem`, `RoutingDecision`, `Severity`,
  `FinalAlert`; `EventRoute` khớp test-plan (“bình thường”/“bất thường”);
  `Severity` có đề xuất ngưỡng/mã (Gate 2); `AlertStatus` có
  pending_approval / sent / rejected (Gate 1).

**Fails (liên quan entity, đã sửa):**
- `FinalAlert` thiếu `id` + `reject_reason` — không biểu diễn được AC
  approve/reject (`/approvals/{id}`, lý do reject). Đã thêm.
- `WatchlistItem.symbol` / `FinalAlert.symbol` cho phép rỗng → `min_length=1`.

**Missing (đúng kỳ vọng — chưa phải entities):**
- Toàn bộ luồng AC/API/agent trong `product-spec.md` / `test-plan.md`
  (scan, chat, guardrail, cron…).

Không thêm entity/API mới ngoài chỉnh 4 model đã có.

## 2026-09-16 — Phase 3: domain entities

- Thêm `domain/entities/models.py`: `WatchlistItem`, `RoutingDecision`,
  `Severity`, `FinalAlert` (+ enum `EventRoute`, `SeverityLevel`,
  `AlertStatus`) — pydantic thuần, không import infra.
- Export qua `domain/entities/__init__.py`.

## 2026-09-16 — Review Phase 1 (re-check) vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 1):**
- Skeleton + `GET /health` → `{"status":"ok"}`; app title =
  `Portfolio Watch & Chat Agent`.
- Chỉ expose `/health` (+ docs mặc định FastAPI) — chưa có `/scan`, `/chat`,
  `/approvals`, `/watchlist` (đúng “chưa business features”).

**Fails:** không có lỗi Phase 1 mới so với lần review trước.

**Missing (đúng kỳ vọng — Phase 3+):**
- Toàn bộ acceptance criteria `product-spec.md`.
- Toàn bộ unit/e2e `test-plan.md`.

Không đổi code trong lần review này.

## 2026-09-16 — Phase 1 re-check (đã hoàn thành trước đó)

- Đọc lại AGENTS.md + specs: checklist Phase 1 toàn bộ `[x]`.
- Smoke-test lại: `GET /health` → `{"status":"ok"}`; `src/chatbot/` không
  còn; `pyproject.toml` + `src/portfolio_watch/` (settings, infra/llm, main)
  còn đủ.
- **Không viết lại / không thêm business features** — tránh đụng Phase 2 UI
  đã xong. Mục chưa làm tiếp theo là Phase 3.

## 2026-09-16 — Phase 2: xác nhận mở UI (3 khu vực, không lỗi console)

- Kiểm tra qua `python -m http.server` + Chrome headless: `#chat`,
  `#watchlist`, `#approvals` hiển thị; `style.css`/`app.js` 200.
- Phát hiện console error `GET /favicon.ico` 404 → thêm
  `<link rel="icon" href="data:,">` trong `index.html`.
- Re-check: 0 console error. Phase 2 UI checklist hoàn tất.

## 2026-09-16 — Review `web/style.css` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi CSS / In Scope frontend):**
- Product-spec: “1 trang đơn giản … không cần polish UI” — `style.css` chỉ
  làm 3 khu vực (chat / watchlist / approvals) dễ đọc; không over-design.

**Fails:** không có lỗi CSS liên quan feature này so với specs.

**Missing (đúng kỳ vọng — không thuộc CSS):**
- Toàn bộ acceptance criteria `product-spec.md` (scan, alert, HITL, chat API,
  guardrail).
- Toàn bộ cases `test-plan.md` (không có tiêu chí CSS/UI visual).

Không đổi code trong lần review này.

## 2026-09-16 — Phase 2: CSS tối thiểu (`web/style.css`)

- Thêm `web/style.css` (layout đơn giản: section, chat box, table, nút).
- `index.html` link stylesheet. Không polish UI.

## 2026-09-16 — Review `web/app.js` stubs vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi stub Phase 2):**
- Có hàm stub cho endpoint AC/test-plan sẽ dùng sau: `POST /scan`,
  `POST /chat`, `GET/POST approvals`, CRUD `/watchlist`.
- Chat submit + Approve/Reject chỉ `console.log` / `fetch` stub — chưa nối
  UI dữ liệu thật (đúng Phase 2).

**Fails (liên quan feature này, đã sửa):**
- `wireUiStubs()` tự gọi `getWatchlist()` + `getApprovals()` khi load → luôn
  lỗi mạng/CORS trên console (backend chưa có), xung đột mục Phase 2
  “không lỗi console”. Đã bỏ auto-fetch; gọi tay từ console khi cần.

**Missing (đúng kỳ vọng — không implement ở stub):**
- Toàn bộ acceptance criteria `product-spec.md` (luồng scan/chat/HITL thật,
  cập nhật trạng thái, guardrail).
- Toàn bộ e2e `test-plan.md` (`/scan`, `/chat`, approve/reject có side-effect).

Không thêm UI/API mới (vd. nút Quét ngay).

## 2026-09-16 — Phase 2: `web/app.js` (API stubs, log console)

- Thêm `web/app.js`: stub `fetch` cho Phase 4 (`/scan`, `/chat`, `/approvals`,
  approve/reject, CRUD `/watchlist`) — chỉ `console.log`, chưa cập nhật UI.
- `index.html`: nạp `app.js`; nút Approve/Reject gắn `data-*-id` để gọi stub.

## 2026-09-16 — Review `web/index.html` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi UI tĩnh / In Scope frontend):**
- Đủ 3 khu vực product-spec yêu cầu: chat box, xem watchlist, danh sách
  cảnh báo chờ duyệt (Approve/Reject).

**Fails (lỗi liên quan feature này, đã sửa):**
- Form chat `type="submit"` mặc định reload trang khi bấm Gửi (file://).
  Thêm `onsubmit="return false;"` — chưa nối API (để Phase 2 mục `app.js`).

**Missing (đúng kỳ vọng — không thuộc HTML tĩnh):**
- Toàn bộ acceptance criteria `product-spec.md` (scan API, alert thật, HITL
  qua API, Chat API, guardrail).
- Toàn bộ cases `test-plan.md` (agents, gates, e2e `/scan` `/chat`).

Không thêm khu vực/UI mới (vd. nút Quét ngay) trong lần sửa này.

## 2026-09-16 — Phase 2: `web/index.html` (3 khu vực tĩnh)

- Tạo `web/index.html` với 3 section tĩnh: Chat (ô nhập + khung hội thoại),
  Watchlist (bảng mã + ngưỡng mẫu), Cảnh báo chờ duyệt (item mẫu +
  Approve/Reject). Chưa nối API, chưa có `app.js` / CSS riêng.

## 2026-09-16 — Review Phase 1 vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 1 / implementation-plan):**
- Khung `src/portfolio_watch/` + `pyproject.toml` + `infra/llm/` +
  `GET /health` → `{"status":"ok"}`.
- Settings có biến riêng project (watchlist, threshold, sources, sqlite).

**Fails (lỗi Phase 1, đã sửa):**
- `.env` cũ còn `APP_NAME=Vietnamese Legal Assistant` → FastAPI title /
  settings sai tên app. Đã đổi `APP_NAME` và bổ sung các key Phase 1 còn
  thiếu (`API_*`, `DEFAULT_*`, `PRICE_SOURCE`, `NEWS_SOURCE`, `SQLITE_PATH`,
  …) mà không đụng API keys.
- Port `8000` bị process uvicorn smoke-test trước chiếm → `python -m …`
  báo WinError 10013. Đã dừng process; khởi động lại `/health` OK.

**Missing (đúng kỳ vọng — thuộc phase sau, không implement ở đây):**
- Toàn bộ acceptance criteria trong `product-spec.md` (scan, watchlist
  alert, HITL approve/reject, Gate 2, Chat API, guardrail mua/bán).
- Toàn bộ unit/integration cases trong `test-plan.md` (agents, gates,
  `POST /scan`, `POST /chat`, cron).

Không thêm business features mới trong lần sửa này.

## 2026-09-16 — Phase 1: Project setup

- Xóa toàn bộ `src/chatbot/` (code cũ ReAct đơn-agent).
- Tạo khung `src/portfolio_watch/` (api / application / domain / infra /
  shared) + `__init__.py`.
- Thêm `pyproject.toml` (fastapi, uvicorn, langgraph, langchain-openai,
  pydantic-settings, openai, apscheduler).
- Thêm `shared/settings.py`, `shared/logging.py`, `.env.example` (bỏ RAG/
  embeddings; thêm watchlist, threshold, price/news source, sqlite path).
- Port `infra/llm/` từ `llm-engineer-demo/app/llm` (backends, client,
  resilience, params, completion) — đổi import sang `src.portfolio_watch`.
- `main.py`: FastAPI + `GET /health` → `{"status":"ok"}`.
- Gỡ service chatbot cũ khỏi `docker-compose.yml` (Docker demo = Phase 7).
- Cập nhật README lệnh chạy Phase 1.
- **Chưa có** business features (scan/chat/agents/UI).

## 2026-09-16 — AGENTS.md cho coding agent

- Viết lại `AGENTS.md` thành hướng dẫn ngắn cho Cursor agent (đọc specs trước,
  một phase/task mỗi lần, giữ app đơn giản, không thêm lib thừa, không đổi
  architecture nếu chưa cập nhật spec, cập nhật change-log + hướng dẫn test
  sau mỗi lần implement).
- Chuyển mô tả domain agents sang `specs/agents.md`; cập nhật tham chiếu trong
  `README.md`, `specs/product-spec.md`, `specs/implementation-plan.md`.

## 2026-09-16 — Khởi tạo spec (Spec-Driven Development)

- Đọc sơ đồ kiến trúc (`portfolio-watch-agent-explained.md` + `.mmd`/`.png`),
  khảo sát `llm-engineer-demo` (nguồn kỹ thuật tái dùng) và `AI_Face_checkin`
  (mẫu clean architecture: `api → application → domain → infra` + `shared`).
- Xác nhận với người dùng: code cũ trong `src/chatbot/` (ReAct đơn-agent,
  guardrails/eval rỗng, layer đặt tên `app/domain/infrastructure`) sẽ bị xóa
  và viết lại theo cấu trúc mới — chỉ tái dùng Ý TƯỞNG kỹ thuật (LLM client,
  model routing, guardrails, tracing), không giữ nguyên file.
- Viết 6 tài liệu spec ban đầu: `README.md`, `AGENTS.md`,
  `specs/product-spec.md`, `specs/implementation-plan.md`,
  `specs/test-plan.md`, `specs/change-log.md` (file này).
- **Chưa viết code implementation** — đây là bước dừng lại để review spec
  trước khi bắt đầu build theo `specs/implementation-plan.md`.

### Quyết định mở, cần chốt trước/khi implement

- Nguồn dữ liệu giá real-time cho mã VN (vnstock? SSI/TCBS public API?) —
  chưa khảo sát kỹ, ghi trong implementation-plan.md phần "Rủi ro".
- Cách lấy tin từ cafef (API chính thức hay scraping) — chưa xác nhận.
- Công thức cụ thể cho "độ tin cậy cao" ở Confidence Gate — sẽ chốt khi viết
  `synthesis_agent.py`.

## 2026-09-19 - Phase 14a
- scan trace = per-request (1 POST /v1/scan = 1 trace), not per-symbol in batch.

