# Implementation Plan — V2 (Small Phases)

**Nền tảng:** MVP Phase 1–10 đã xong — `specs/mvp-status-report.md`.  
**Mục tiêu V2:** `specs/product-spec.md`.  
**Quy tắc:** một phase tại một thời điểm; không code ngoài checklist phase đang mở.

```
Frontend (:5173) → Backend (:8000) → AI (:8001) → Langfuse (host :3000)
```

Tham chiếu code: `../llm-engineer-demo/app/agent_pr/`, `../llm-engineer-demo/app/monitoring/tracing.py`.

---

## Phase 1 — Project setup (V2)

Chuẩn bị refactor — **không** đổi hành vi sản phẩm.

- [x] Xác nhận MVP chạy được: `docker compose up --build` (3 service) + 1 chat +
      1 quét mã trên UI.
- [x] Lưu baseline golden: chạy full eval hiện tại, ghi pass/fail vào
      `specs/eval/v2_baseline.json` (hoặc cập nhật report có sẵn).
- [x] Ghi quyết định V2 vào `specs/change-log.md`: giữ golden 30 case; không nới
      scorer; thứ tự phase 1 → 11 → … → 16.
- [x] Cập nhật `.env.example`: comment block V2 (`LANGFUSE_HOST` self-host,
      `host.docker.internal` trong Docker).
- [x] README: mục «V2 in progress» — trỏ `product-spec` + plan này; ghi rõ path
      legacy (`backend/`, `frontend/`, `scripts/`) sẽ deprecated.
- [x] `AGENTS.md`: xác nhận agent chỉ làm 1 phase / 1 agent folder mỗi lần.

**Xong phase khi:** baseline + docs chốt; MVP vẫn chạy như cũ.

---

## Phase 11 — Cấu trúc `src/` monorepo

Tạo skeleton mới — **song song** code cũ, chưa xóa root `backend/`/`frontend/`.

- [x] Tạo thư mục:
      `src/portfolio_watch/agents/`,
      `src/portfolio_watch/backend/`,
      `src/portfolio_watch/frontend/`,
      `src/portfolio_watch/eval/`,
      `src/portfolio_watch/graph/` (hoặc mở rộng `domain/graph/` → ghi change-log).
- [x] Mỗi thư mục có `__init__.py` + README ngắn (1 đoạn vai trò).
- [x] Bảng migrate (trong change-log hoặc comment README):
      | Cũ | Mới |
      |---|---|
      | `backend/main.py` | `src/portfolio_watch/backend/` |
      | `frontend/` | `src/portfolio_watch/frontend/` |
      | `domain/agents/*` | `src/portfolio_watch/agents/<name>/` |
      | `scripts/run_eval.py` | `src/portfolio_watch/eval/run.py` |
- [x] `pyproject.toml`: package discover/include path mới (nếu cần).
- [x] Test smoke: `pytest tests/ -q` vẫn pass (chưa bắt buộc dùng path mới).

**Xong phase khi:** skeleton tồn tại; mapping migrate được ghi; test cũ không vỡ.

---

## Phase 12 — Refactor từng agent

Pattern mỗi agent (tham chiếu `agent_pr`):

```text
agents/<name>/
  __init__.py
  nodes.py       # logic node, docstring ngắn
  state.py       # TypedDict
  schemas.py     # I/O (tuỳ agent)
  tools.py       # ReAct tools (tuỳ agent)
  graph.py       # subgraph compile (tuỳ agent)
```

**Làm lần lượt** — tick từng dòng, chạy test agent sau mỗi agent:

- [x] **12a — `price_agent`:** port từ `domain/agents/price_agent.py`; không LLM;
      pytest price pass.
- [x] **12b — `news_agent`:** ReAct + `fetch_cafef_news`; pytest news pass.
- [x] **12c — `event_classifier`:** routing normal/abnormal; pytest classifier pass.
- [x] **12d — `eval_agent`:** ReAct + `read_price_history`; pytest eval pass.
- [x] **12e — `synthesis_agent`:** alert + guardrail loop nội bộ; pytest synthesis pass.
- [x] **12f — `supervisor_agent`:** rewrite + routing; pytest supervisor pass.
- [x] **12g — `answer_composer`:** compose + guardrail; pytest answer pass.
- [x] **12h — Prompts:** chốt 1 nơi (`agents/<name>/prompts/` *hoặc*
      `infra/llm/prompt_registry`) — ghi change-log.
- [x] **12i — Shared:** `guardrails`, `entities` — import từ `shared/` hoặc
      `domain/` (chốt, không trùng lẫn).

**Backlog 12c** (thêm dòng khi golden fail, không nới scorer):

- [ ] _(placeholder)_ Task mới khi debug case.

**Xong phase khi:** 7 agent folder có `nodes.py`; test agent tương ứng pass.

---

## Phase 13 — LangGraph orchestration thật

Graph **chạy** luồng — không chỉ vẽ sơ đồ.

- [x] **13a — Graph chat:** `graph/chat.py` — rewrite → supervisor → workers →
      answer → guardrail; subgraph worker (pattern `supervisor_agent/graph.py` demo).
- [x] **13b — Graph scan:** `graph/scan.py` — price+news → classifier →
      (normal END | abnormal → eval → synthesis → gates).
- [x] **13c — Wire API:** `/v1/chat`, `/v1/scan` invoke compiled graph;
      `recursion_limit` hợp lý.
- [x] **13d — `steps[]`:** sinh từ tên node / event graph (không list hardcode
      riêng trong handler).
- [x] **13e — Visualization:** `save_graph_visualization()` + `python -m
      src.portfolio_watch.graph.workflow` (pattern `hierarchical.py`).
- [x] **13f — Deprecate dần:** `application/answer_question.py`,
      `application/scan_symbol.py` gọi graph hoặc thay hẳn — ghi change-log.
- [x] pytest graph compile + 1 invoke stub (mock LLM/tools).

**Xong phase khi:** chat + scan qua graph; UI vẫn nhận `steps[]`; eval 1 case
lookup pass.

---

## Phase 14 — Langfuse trace lồng nhau

Port ý tưởng `llm-engineer-demo/app/monitoring/tracing.py`.

- [x] **14a — Root trace:** `trace_request(name, input)` — 1 trace / `POST /v1/chat`
      (và 1 trace / scan — chốt per-request hay per-symbol trong change-log).
- [x] **14b — Agent span:** `agent_span(turn, agent_name)` — 1 span / graph node;
      tên = `rewrite_question`, `price_agent`, …
- [x] **14c — Step span:** `trace_step(..., step_name)` — con **thụt 1 cấp**
      (tool call, draft, guardrail_retry, …); mỗi span có input + output.
- [x] **14d — Wire nodes:** mọi `nodes.py` gọi `trace_step` ở bước nội bộ.
- [x] **14e — Docker env:** AI service `LANGFUSE_HOST=http://host.docker.internal:3000`,
      `extra_hosts: host-gateway` trong compose.
- [x] **14f — No-op:** `MONITORING_ENABLED=false` → chat/scan OK, không gọi Langfuse.
- [x] **14g — Test:** pytest mock hierarchy parent/child; checklist thủ công
      (test-plan §4): 1 chat UI → Langfuse 1 trace, expand ≥ 3 cấp.

**Xong phase khi:** checklist Langfuse pass (hoặc mock test pass nếu không có host).

---

## Phase 15 — Docker product-only

Product chạy **chỉ** qua compose; xóa path legacy.

- [x] **15a — Compose:** 3 service trỏ entry mới trong `src/portfolio_watch/`:
      - `frontend` → static `src/portfolio_watch/frontend` (:5173)
      - `backend` → uvicorn backend package (:8000)
      - `ai` → uvicorn AI package (:8001)
- [x] **15b — Dockerfile:** build context + copy `src/`; ghi tag/image trong
      change-log.
- [x] **15c — Volume:** `pw_data` — SQLite AI + Backend (giữ path hoặc migrate
      — ghi rõ).
- [x] **15d — Healthcheck:** `/health` AI + Backend trong compose.
- [x] **15e — Eval module:** `src/portfolio_watch/eval/run.py` +
      `eval/regression.py` — thay `scripts/run_eval.py`, `phase5_regression.py`.
- [x] **15f — Xóa:** thư mục `scripts/`; root `backend/`, `frontend/` (sau test pass).
- [x] **15g — README:** chỉ còn hướng dẫn `docker compose up --build` + eval
      qua `docker compose run --rm ai python -m ...`.

**Xong phase khi:** không còn README tham chiếu `scripts/`; compose E2E pass.

---

## Phase 16 — Regression & docs

Đóng V2 — chất lượng + tài liệu.

- [x] **16a — Golden full 30:** qua Docker eval — không tụt `REGRESSION_TOLERANCE`.
- [x] **16b — Injection slice:** pass **100%**.
- [x] **16c — Cập nhật** `specs/agents.md` (path folder mới + graph).
- [x] **16d — Cập nhật** `specs/test-plan.md` (lệnh Docker cuối cùng).
- [x] **16e — Cập nhật** README: Langfuse checklist, URL, troubleshooting Docker.
- [x] **16f —** `specs/mvp-status-report.md` — thêm section «V2 complete».
- [x] **16g —** Demo script ngắn trong README: watchlist → quét → chat → Langfuse trace.

**Xong phase khi:** acceptance criteria `product-spec.md` §5 đều tick.

---

## Thứ tự thực hiện

```
1 → 11 → 12 (12a…12g) → 13 → 14 → 15 → 16
```

| Phase | Phụ thuộc |
|---|---|
| 11 | Phase 1 |
| 12 | Phase 11 skeleton |
| 13 | Phase 12: ít nhất price, news, supervisor, answer |
| 14 | Phase 13 (graph + nodes wired) |
| 15 | Phase 13–14 ổn định |
| 16 | Phase 15 |

**Một lần chỉ mở 1 phase** (Phase 12: tối đa 1 agent / PR).
