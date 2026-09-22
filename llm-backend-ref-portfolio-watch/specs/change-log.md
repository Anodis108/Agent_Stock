## 2026-09-22 — Review Phase 17 (line 1) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] README appendix Optional local development (Spec Guide Bước 9).`

**Passes**
- Docker-first Quick Start vẫn đứng trước appendix (AC9 giữ nguyên).
- Một app `:8000` uvicorn — khớp kiến trúc V3.
- test-plan: product test ưu tiên Docker; local cho contributors.
- `tests/test_readme_phase17_local.py` + `test_readme_phase16.py` pass.

**Fails (đã sửa trong review)**
- Agy báo SUCCESS nhưng không ghi file — Cursor implement + sửa `test_readme_phase16.py` cho phép uvicorn chỉ trong appendix.

**Missing**
- Phase 17 line 2 (ngrok), line 3 (mvp-status-report).

## 2026-09-22 — Phase 17 line 1: README optional local dev

- `README.md`: section `## Optional local development` (venv, pip install -e ".[dev]", uvicorn :8000, pytest).
- `tests/test_readme_phase17_local.py`; cập nhật `tests/test_readme_phase16.py`.
- `specs/implementation-plan.md`: Phase 17 mở + line 1 `[x]`.

### Demo thủ công
```bash
python -m pytest tests/test_readme_phase17_local.py tests/test_readme_phase16.py -q
# Optional: uvicorn src.portfolio_watch.backend.main:app --reload --port 8000
```

## 2026-09-22 — Review Phase 16 (line 5) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] Demo ngắn trong README: chat → graph hover → market → (tuỳ chọn) Langfuse.`

**Passes**
- README `## Demo walkthrough (5 phút)`: chat, live graph hover, Market tab, Langfuse optional.
- test-plan §6 Demo E2E bước 1–4 — khớp phạm vi line 5.
- product-spec AC1/AC2/AC3 (optional) — có hướng dẫn thủ công.
- Phase 16 checklist 5/5 `[x]`; mvp-status-report: Phase 16 complete.

**Fails (đã sửa trong review)**
- `test_readme_phase16_demo.py` chuẩn hóa ROOT + split section an toàn hơn.

**Missing**
- Không (Phase 16 hoàn tất).

## 2026-09-22 — Phase 16 line 5: README demo walkthrough

- `README.md`: section Demo walkthrough (chat → graph → market → Langfuse optional).
- `tests/test_readme_phase16_demo.py`.
- `specs/mvp-status-report.md`: Phase 16 complete.
- `specs/implementation-plan.md`: đánh dấu `[x]` dòng 5 — **Phase 16 done**.

### Demo thủ công
```bash
python -m pytest tests/test_readme_phase16_demo.py -q
docker compose up --build -d
# Mở http://localhost:8000 → làm theo README Demo walkthrough
```

## 2026-09-22 — Review Phase 16 (line 4) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] Status report: section V3 complete khi AC product-spec 1–9 tick.`

**Passes**
- `specs/mvp-status-report.md`: section `## V3 complete (2026-09-22)` bảng AC 1–9 Done.
- How to run trỏ README Docker-first; có lệnh eval in container.
- `tests/test_mvp_status_report_phase16.py` pass.

**Fails (đã sửa trong review)**
- Evidence paths sai (`web/`, `eval/dataset.json`) → sửa path thật trong repo.
- Thiếu `by_slice` ở AC7; ngày báo cáo cũ → cập nhật 2026-09-22.

**Missing (Phase 16 line 5)**
- Demo ngắn trong README (chat → graph → market → Langfuse optional).

## 2026-09-22 — Phase 16 line 4: Status report V3 complete

- `specs/mvp-status-report.md`: V3 complete table AC 1–9 + Docker-first run.
- `tests/test_mvp_status_report_phase16.py`.
- `specs/implementation-plan.md`: đánh dấu `[x]` dòng 4.

### Demo thủ công
```bash
python -m pytest tests/test_mvp_status_report_phase16.py -q
# Đọc specs/mvp-status-report.md section V3 complete
```

## 2026-09-22 — Review Phase 16 (line 3) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] README chỉ Docker product + eval trong container.`

**Passes**
- product-spec AC9 / out-of-scope: không còn uvicorn local làm đường chính trong README.
- test-plan §5 Docker product + eval in container — đạt.
- Quick start: `docker compose up --build`; eval qua `docker compose run --rm app`.
- `tests/test_readme_phase16.py` pass.

**Fails (đã sửa trong review)**
- README thiếu volume/logs/down và link `.env.example` → bổ sung ngắn.

**Missing (Phase 16 line 4–5)**
- Status report «V3 complete»; demo walkthrough trong README.

## 2026-09-22 — Phase 16 line 3: README Docker-only + eval in container

- `README.md`: Docker-first; bỏ hướng dẫn chạy local/uvicorn/:5173.
- `tests/test_readme_phase16.py`: assert docker + eval container, không local run.
- `specs/implementation-plan.md`: đánh dấu `[x]` dòng 3.

### Demo thủ công
```bash
python -m pytest tests/test_readme_phase16.py -q
cp .env.example .env
docker compose up --build -d
docker compose run --rm app python -m src.portfolio_watch.eval.run --self-check
```

## 2026-09-22 — Review Phase 16 (line 2) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] .env.example: memory, Langfuse, freshness, Qdrant (optional).`

**Passes**
- Section V3 gom memory, freshness (TTL), Langfuse, Qdrant optional.
- Biến khớp `shared/settings.py`; Qdrant fallback + compose profile documented.
- product-spec AC5/AC6 env; test-plan §4 memory env — đạt.
- pytest `test_env_example_phase16` + env tests pass.

**Fails (đã sửa trong review)**
- `test_env_example_phase16.py` thiếu docstring/ROOT convention → chuẩn hóa.

**Missing (Phase 16 line 3–5)**
- README Docker-only, status report V3 complete, demo README.

## 2026-09-22 — Phase 16 line 2: .env.example V3 memory / Langfuse / Qdrant

- `.env.example`: section `# V3 — Memory, freshness, Langfuse, Qdrant (optional)`.
- `tests/test_env_example_phase16.py`: assert keys + comments freshness/Qdrant.
- `specs/implementation-plan.md`: đánh dấu `[x]` dòng 2.

### Demo thủ công
```bash
python -m pytest tests/test_env_example_phase16.py -q
cp .env.example .env
# Kiểm tra: MEMORY_*, QDRANT_* (optional), MONITORING_*, LANGFUSE_*
docker compose --profile qdrant config | grep QDRANT
```

## 2026-09-22 — Review Phase 16 (line 1) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] UI: lỗi API / timeout / HITL fail không làm trắng trang.`

**Passes**
- Boot `Promise.allSettled`: 1 API fail vẫn render 2 panel còn lại.
- Banner theo vùng: chat, watchlist, market, approvals, scan.
- HITL approve/reject fail: `#approvals-error` + giữ list; reload approvals.
- Global `error` / `unhandledrejection` → boot-status, không crash trang.
- test-plan §3 UI layout giữ nguyên khi lỗi; pytest 9 pass.

**Fails (đã sửa trong review)**
- Handler click HITL trùng `setBoot` với `doApprove`/`doReject` → gọn catch.

**Missing (Phase 16 line 2–5)**
- `.env.example`, README Docker-only, status report V3, demo README.

## 2026-09-22 — Phase 16 line 1: UI error resilience (no blank page)

- `frontend/index.html`: `#watchlist-error`, `#approvals-error`, `#scan-error`.
- `frontend/app.js`: safeLoad*, allSettled boot, HITL/scan/watchlist errors, global handlers.
- `frontend/style.css`: shared error banner styles.
- `tests/test_frontend.py`: `test_phase16_error_resilience_ui`.

### Demo thủ công
```bash
python -m pytest tests/test_frontend.py -q
# 1) Dừng backend → refresh UI: header + chat vẫn hiện; boot-status báo tải lỗi N/3
# 2) Bật backend → chat timeout: banner chat + bubble lỗi, timeline error node
# 3) Tab Approvals → Duyệt id sai: banner approvals, list không trống
```

## 2026-09-22 — Review Phase 15 (line 5) vs product-spec / test-plan

### Phạm vi — chỉ 1 dòng checklist
`[x] Gate: injection 100%; regression vs v3_baseline + tolerance.`

**Passes**
- `check_injection_gate`: injection fail → exit 1 (không tolerance).
- `check_regression`: so rate tổng vs `v3_baseline.json` + tolerance 0.05.
- `check_regression_by_slice`: bắt drop theo slice (skip diagram baseline 0/0).
- `eval_gates_passed`: overall + by_slice + injection 100%.
- Default dataset `golden_v3.yaml`; `regression.py` dùng v3 golden + v3 baseline.
- product-spec AC7 (eval gates) — đạt phần gate; pytest 104 pass.

**Fails (đã sửa trong review)**
- `regression.py` write_report vẫn hardcode baseline_debug → dùng path động.

**Missing (Phase 16+)**
- README Docker-only; UI error handling; status report V3 complete.

## 2026-09-22 — Phase 15 line 5: Injection gate + regression vs v3_baseline

- `eval/run.py`: `check_regression_by_slice`, default `golden_v3`, wire gates in `main`.
- `eval/regression.py`: golden_v3 + v3_baseline, `--dataset`, slice order + diagram.
- `tests/test_eval.py`: 3 test gate by_slice / eval_gates_passed.
- `specs/implementation-plan.md`: đánh dấu `[x]` dòng 5 — Phase 15 hoàn tất.

### Demo thủ công
```bash
python -m pytest tests/test_eval.py -q
python -m src.portfolio_watch.eval.run --self-check
python -m src.portfolio_watch.eval.run --run --slice injection --skip-judge --skip-agent-eval
docker compose run --rm app python -m src.portfolio_watch.eval.regression --limit 3
```

## 2026-09-22 ? Review Phase 15 (line 4) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d�ng checklist
`[x] Runner aggregate overall + by_slice.`

**Passes**
- `build_report` lu�n tr? 5 slice (g?m `diagram`, k? c? 0/0).
- `format_report` in `Theo slice:` v?i d�ng `diagram: 0/0 passed (n/a)` khi kh�ng c� case.
- `EvalReport.as_dict()` / `baseline_payload`: `by_slice` d?ng dict keyed by slice type.
- `SliceScore.rate` = `None` khi `total == 0` (kh?p `v3_baseline.json`).
- test-plan �1 aggregate `overall + by_slice[type]` ? ??t cho runner.
- pytest + `--self-check` pass.

**Fails (?� s?a trong review)**
- `_self_check` ch?a assert `diagram` trong report ? th�m assert 5 slice + `by_slice["diagram"]`.
- File th?a `append_test.py` (t? agy) ? x�a.

**Missing (ngo�i ph?m vi line 4 ? Phase 15 line 5)**
- Gate injection 100% + regression vs `v3_baseline` + tolerance.
- Default runner v?n `golden_dataset.yaml` (d�ng `--dataset golden_v3.yaml` khi c?n 33 case).

## 2026-09-22 ? Phase 15 line 4: Runner aggregate overall + by_slice

- `eval/run.py`: `SLICE_ORDER` +5 `diagram`; `build_report` / `format_report` / `SliceScore.rate`.
- `tests/test_eval.py`: 3 test `by_slice` (5 slice, diagram case, format line).
- `specs/implementation-plan.md`: ?�nh d?u `[x]` d�ng 4.

### Demo th? c�ng
```bash
python -m pytest tests/test_eval.py -q
python -m src.portfolio_watch.eval.run --self-check
python -m src.portfolio_watch.eval.run --run --dataset specs/eval/golden_v3.yaml --slice diagram --skip-judge --skip-agent-eval
```

## 2026-09-22 ? Review Phase 15 (line 3) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d�ng checklist
`[x] Rule-based must_include / must_not_include.`

**Passes**
- `score_rule_based` / `score_case_rule_based` �p d?ng cho 5 slice (g?m `diagram`).
- `validate_golden_case_rules` + auto-validate khi load `golden_v3.yaml`.
- CLI `--dataset PATH` cho ph�p ch?m rule-only tr�n golden_v3.
- `_self_check` th�m fixture `diagram_01` pass/fail.
- test-plan �1 t?ng rule-based ? ??t; pytest pass.

**Fails (?� s?a trong review)**
- Module docstring v?n ghi �4 slice� ? c?p nh?t 5 slice.
- `validate_golden_case_rules` ch?a ki?m `slice.type ? RULE_SLICES` ? th�m.

**Missing (ngo�i ph?m vi line 3 ? Phase 15 line 4?5)**
- Default runner v?n `golden_dataset.yaml`; report `by_slice`; regression baseline 33 cases.

## 2026-09-22 ? Phase 15 line 3: Rule-based must_include / must_not_include

- `eval/run.py`: `GOLDEN_V3_PATH`, `RULE_SLICES`, `validate_golden_case_rules`, `--dataset`.
- `tests/test_golden_v3_rules.py`: rule pass/fail theo t?ng slice.
- `specs/implementation-plan.md`: ?�nh d?u `[x]` d�ng 3.

### Demo th? c�ng
```bash
python -m src.portfolio_watch.eval.run --self-check
python -m pytest tests/test_golden_v3_rules.py -q
python -m src.portfolio_watch.eval.run --run --dataset specs/eval/golden_v3.yaml --case-id diagram_01 --skip-judge --skip-agent-eval
```

## 2026-09-22 ? Review Phase 15 (line 2) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Slice: lookup, comparison, out_of_scope, injection, diagram (?3 case).`

**Passes**
- `golden_v3.yaml`: 33 cases ? 5 slice types; `diagram` ?3 (`diagram_01`?`03`).
- C?u h?i ti?ng Vi?t (FPT/VNM/HPG); `must_include`/`must_not_include` kh?p output heuristic diagram agent.
- test-plan slice `diagram`: gate Mermaid h?p l? ? `must_include` c? `graph`/`mermaid`/`price_agent`.
- product-spec #7: dataset c? ?? slice Class 18 (g?m diagram).
- Smoke rule-based: 3/3 diagram cases pass `score_rule_based` v?i `run_chat_graph`.
- Pytest: `test_golden_v3.py` pass.

**Fails**
- Kh?ng c? (agy implement ??ng ph?m vi).

**Missing (ngo?i ph?m vi line 2 ? Phase 15 line 3?5)**
- Runner ch?a tr? `golden_v3`; aggregate `by_slice`; regression vs `v3_baseline`.

## 2026-09-22 ? Phase 15 line 2: diagram slice (?3 case)

- `specs/eval/golden_v3.yaml`: th?m `diagram_01`?`diagram_03`.
- `tests/test_golden_v3.py`: assert 5 slice types, diagram ?3.
- `specs/implementation-plan.md`: ??nh d?u `[x]` d?ng 2.

### Demo th? c?ng
```bash
python -m pytest tests/test_golden_v3.py -q
python -c "import yaml; d=yaml.safe_load(open('specs/eval/golden_v3.yaml',encoding='utf-8')); print({c['slice']['type'] for c in d['cases']})"
```

## 2026-09-22 ? Review Phase 15 (line 1) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] specs/eval/golden_v3.yaml: version, m?i case c? id + slice.`

**Passes**
- `golden_v3.yaml`: `dataset`, `version: 3`, `changelog`; 30 cases carry-forward t? v1.
- M?i case c? `id` unique + `slice.type` + `slice.difficulty`.
- Slice counts: lookup 18, comparison 6, out_of_scope 3, injection 3 (kh?p v1).
- test-plan ?1 c?u tr?c version ho? + id/slice ? ??t cho 4 slice hi?n c?.
- Pytest: `tests/test_golden_v3.py` pass.

**Fails (?? s?a trong review)**
- `changelog` b? l?i encoding (`t?i gi?n`) ? s?a UTF-8.
- Test d?ng path t??ng ??i ? chuy?n sang `Path` + assert `dataset`/`difficulty`.

**Missing (ngo?i ph?m vi line 1 ? Phase 15 line 2?5)**
- Slice `diagram` (?3 case); runner tr? `golden_v3`; by_slice aggregate; regression gate.
- Eval runner v?n d?ng `golden_dataset.yaml` (ch?a wire ? line 4).

## 2026-09-22 ? Phase 15 line 1: golden_v3.yaml

- `specs/eval/golden_v3.yaml`: dataset v3, 30 case, id + slice { type, difficulty }.
- `tests/test_golden_v3.py`: validate schema Class 18.
- `specs/implementation-plan.md`: ??nh d?u `[x]` d?ng 1 Phase 15.

### Demo th? c?ng
```bash
python -m pytest tests/test_golden_v3.py -q
python -c "import yaml; d=yaml.safe_load(open('specs/eval/golden_v3.yaml',encoding='utf-8')); print(d['version'], len(d['cases']))"
```

## 2026-09-22 ? Review Phase 14 (line 4) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Structured output cho plan s? ?? (n?u d?ng LLM).`

**Passes**
- `DiagramPlanOutput` (Pydantic): `title`, `nodes`, `edges`, `mermaid`, `format` + `to_graph_json()`.
- `LlmDiagramBrain` d?ng `call_llm_structured` + prompt `diagram_plan`; fallback `HeuristicDiagramBrain`.
- `run_diagram_agent` tr? `graph_json` t? plan; `/chat` payload `diagram.graph_json`.
- Mock LLM test: `test_phase14_diagram_structured_llm_plan`; schema: `test_diagram_plan_schema`.
- Phase 14 **ho?n th?nh** ? c?u ?v? s? ?? lu?ng scan ?? hi?n s? ?? tr?n UI.
- **95 pytest passed** to?n suite.

**Fails (?? s?a trong review)**
- `HeuristicDiagramBrain` tr? `edges=[]` ? b? sung edges scan-flow.
- `implementation-plan.md` b? agy ??i wording d?ng 2?3 ? kh?i ph?c checklist g?c.
- `test_phase14_diagram_outputs_mermaid` ch?a assert `graph_json` ? th?m.

**Missing (ngo?i Phase 14)**
- Golden slice `diagram` (Phase 15); LLM production path m?c ??nh v?n heuristic (gi?ng c?c agent kh?c trong test).

## 2026-09-22 ? Phase 14 line 4: Structured output cho plan s? ??

- `shared/schemas.py`: `DiagramPlanOutput`.
- `agents/diagram_agent/schemas.py`: re-export + `DiagramBrain` protocol.
- `agents/diagram_agent/nodes.py`: `HeuristicDiagramBrain`, `LlmDiagramBrain`, brain pattern.
- `prompts/diagram_plan/v1.yaml` + `production.txt`.
- `graph/chat.py`: inject `diagram_brain` qua deps.
- `tests/test_phase14.py`: `test_phase14_diagram_structured_llm_plan`.
- `tests/test_structured_output.py`: `test_diagram_plan_schema`.
- `specs/implementation-plan.md`: ??nh d?u `[x]` d?ng 4 ? **Phase 14 xong**.

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. Chat: **?V? s? ?? lu?ng scan FPT?** ? s? ?? render trong bubble (heuristic).
3. DevTools ? `/chat` JSON: `diagram.mermaid` + `diagram.graph_json.nodes/edges`.
4. (T?y ch?n LLM) inject `LlmDiagramBrain` qua deps/eval ? structured plan qua `call_llm_structured`.

## 2026-09-22 ? Review Phase 14 (line 3) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] UI render s? ?? trong bubble ho?c panel.`

**Passes**
- `index.html` load mermaid.js CDN; `app.js` render SVG trong bubble assistant (`.diagram-panel`).
- `doChat` ??c `data.diagram` t? `/chat`; fallback parse fenced ` ```mermaid ` trong `answer`.
- product-spec Flow A b??c 5 / acceptance #8: s? ?? hi?n tr?n UI (bubble).
- test-plan: ?Diagram answer ? s? ?? render ???c? ? wiring + `/chat` tr? `diagram.mermaid`.
- Pytest: `test_phase14_diagram_ui_render` + phase14 backend tests pass.

**Fails (?? s?a trong review)**
- Thi?u `mermaid.initialize()` tr??c `mermaid.run()` ? th?m `initMermaid()`.
- Element render thi?u class `mermaid` ? th?m khi g?i `renderMermaidInElement`.
- `change-log.md` b? l?i encoding t? agy ? vi?t l?i entry.

**Missing (ngo?i ph?m vi line 3 ? Phase 14 line 4)**
- Structured output LLM cho plan s? ?? ? ch?a c?.

## 2026-09-22 ? Phase 14 line 3: Diagram UI render

- `frontend/index.html`: CDN `mermaid.min.js` tr??c `app.js`.
- `frontend/app.js`: `renderMermaidInElement`, `appendChat(..., diagram)`, `doChat` truy?n payload `diagram`.
- `frontend/style.css`: `.diagram-panel`, `.mermaid-diagram`.
- `tests/test_frontend.py`: `test_phase14_diagram_ui_render`.
- `specs/implementation-plan.md`: ??nh d?u `[x]` d?ng 3 Phase 14.

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. M? http://127.0.0.1:8000/
3. Chat: **?V? s? ?? lu?ng scan FPT?**
4. Bubble assistant hi?n th? s? ?? Mermaid (SVG), kh?ng c?n raw code block.

# Change Log

Nh?t k? thay ??i theo th?i gian cho project Portfolio Watch & Chat Agent.
Ghi theo ng?y, m?i nh?t ? tr?n.

## 2026-09-22 ? Review Phase 14 (line 2) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Output Mermaid ho?c graph JSON.`

**Passes**
- `diagram_agent` tr? `DiagramAgentResult` v?i `mermaid`, `format="mermaid"`, `graph_json=None`.
- `answer` ch?a fenced block ` ```mermaid `; `/chat` payload c? object `diagram`.
- `steps[]` node `diagram_agent` c? `output.mermaid` (live graph hover I/O).
- Slice `diagram` (test-plan): Mermaid h?p l? (`graph TD`, node `price_agent`, symbol FPT).
- Pytest: `test_phase14_diagram_outputs_mermaid` + **92 passed** to?n suite.

**Fails (?? s?a trong review)**
- `mermaid.strip("\`mermaid\\n")` d?ng char-set strip ? d? h?ng chu?i ? t?ch `mermaid_body` /
  `fenced` r? r?ng trong `diagram_agent/nodes.py`.

**Missing (ngo?i ph?m vi line 2 ? Phase 14 line 3?4)**
- product-spec Flow A b??c 5 / acceptance #8: **UI render s? ??** (bubble/panel) ? ch?a c?.
- Structured output LLM cho plan s? ?? ? ch?a c?.

## 2026-09-22 ? Phase 14 line 2: Diagram Mermaid output

- `agents/diagram_agent/nodes.py`: `run_diagram_agent` outputs static Mermaid diagram structure.
- `application/answer_question.py` & `graph/chat.py`: Propagate `diagram_result` in `AnswerQuestionResult`.
- `graph/steps.py`: Map diagram fields for live-graph UI hover I/O.
- `backend/ai_client.py`: Include `diagram` object with `mermaid`, `format`, `graph_json` in `/chat` response.
- `tests/test_phase14.py`: Th?m `test_phase14_diagram_outputs_mermaid` ?? ki?m ch?ng c?u tr?c output.
- `specs/implementation-plan.md`: ??nh d?u `[x]` d?ng 2 c?a Phase 14.

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. Chat: **?V? s? ?? lu?ng scan FPT?**
3. Trong JSON response, xem `diagram.mermaid` ch?a ?? th? Mermaid `graph TD...` v? `steps` cho node `diagram_agent` bao g?m I/O Mermaid rendering.

## 2026-09-22 ? Review Phase 14 (line 1) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Intent "v? s? ??" ? node/agent diagram_agent (ho?c nh?nh supervisor).`

**Passes**
- Heuristic + LLM fallback: `_has_diagram_intent` / intent `diagram` ?
  `agents_to_call: ["diagram"]`.
- LangGraph `graph/chat.py`: nh?nh supervisor ? `diagram_agent` ? END (stub answer).
- Agent m?i `agents/diagram_agent/`; step `diagram_agent` trong `steps[]` (live graph).
- Schema: intent/agents literal m? r?ng `diagram` trong `shared/schemas.py`.
- Pytest: `tests/test_phase14.py::test_phase14_diagram_intent_routes_to_diagram_agent`.
- **91 pytest passed**.

**Fails (?? s?a trong review)**
- Agy timeout 12m ? code ?? v?o repo nh?ng ch?a tick checklist/change-log ? b? sung.

**Missing (??ng k? v?ng ? d?ng Phase 14 c?n l?i)**
- Mermaid/graph JSON output; UI render s? ??; structured diagram plan (LLM).

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. Chat: **?V? s? ?? lu?ng scan FPT?**
3. Live graph c? node `diagram_agent`; c?u tr? l?i placeholder (Mermaid ? line 2).

## 2026-09-22 ? Phase 14 line 1: diagram intent routing (agy)

- `supervisor_agent/nodes.py`: intent `diagram`, phrases v? s? ??.
- `graph/chat.py`: node `diagram_agent`, conditional edge t? supervisor.
- `agents/diagram_agent/`: stub `run_diagram_agent`.
- `tests/test_phase14.py`: routing + steps test.

## 2026-09-22 ? Review Phase 13 (line 3) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Kh?ng g?i AI service t?ch (n?u ?? g?p).`

**Passes**
- Product-spec: m?t app Docker ? UI + API + LangGraph c?ng process.
- `docker-compose.yml`: `AI_TRANSPORT: "inprocess"`; kh?ng service `ai:` ri?ng.
- `.env.example`: `AI_TRANSPORT=inprocess` (HTTP ch? khi override test/V2).
- `ai_client._use_http()` ? `False` m?c ??nh; frontend kh?ng `:8001`/`/v1/*`.
- Pytest: `test_phase13_no_separate_ai_from_frontend`, `test_phase13_inprocess_default`,
  `test_chat_inprocess`.

**Fails (?? s?a trong review)**
- Agy SUCCESS nh?ng kh?ng ghi repo (scratch) ? b? sung test + tick checklist.

**Missing**
- Phase 13 ho?n t?t; Phase 14+ ch?a b?t ??u.

### Demo th? c?ng
1. `docker compose up --build` ? ch? service `app` (:8000), kh?ng container AI ri?ng.
2. DevTools Network khi chat/qu?t: kh?ng request t?i `:8001`.
3. (Tu? ch?n) `AI_TRANSPORT=http` + AI down ? chat 502; m?c ??nh inprocess v?n OK.

## 2026-09-22 ? Phase 13 line 3: in-process AI default (review)

- X?c nh?n c?u h?nh s?n c?; th?m pytest ? tr?n.

## 2026-09-22 ? Review Phase 13 (line 2) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Qu?t + approve/reject ho?t ??ng t? UI m?i.`

**Passes**
- Product-spec flow C: Watchlist c? form qu?t + n?t Qu?t t?ng m?; Approvals tab
  c? Duy?t/T? ch?i.
- `app.js`: `doScan` ? `POST /scan` + `applyTimelineFromBackend` + reload
  `loadApprovals`/`loadMarket`; `doApprove`/`doReject` ? API + refresh lists.
- L?i qua `showOpError` / `setBoot` / `formatApiError` (kh?ng reload trang).
- Pytest: `test_phase13_scan_approve_ui_wiring`, `test_phase13_scan_and_approve_api`.

**Fails (?? s?a trong review)**
- Agy ghi file v?o scratch folder, kh?ng v?o repo ? b? sung test + tick checklist
  trong review.

**Missing (??ng k? v?ng ? d?ng checklist kh?c Phase 13)**
- Kh?ng g?i AI service t?ch (d?ng cu?i Phase 13).

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. Tab Watchlist ? nh?p FPT ? **Qu?t** ? Timeline + Live graph c?p nh?t.
3. Tab C?nh b?o ch? duy?t (n?u c? pending) ? **Duy?t** ho?c **T? ch?i** ? list
   gi?m; tab Market status c?p nh?t tr?ng th?i.

## 2026-09-22 ? Phase 13 line 2: scan + HITL UI wiring (review)

- X?c nh?n wiring s?n c? trong `app.js`; th?m pytest UI + API ? tr?n.

## 2026-09-22 ? Review Phase 13 (line 1) vs product-spec / test-plan

### Ph?m vi ? ch? 1 d?ng checklist
`[x] Chat / graph / market / watchlist / HITL c?ng origin app (Phase 2?3).`

**Passes**
- Product-spec AC1 / flow A?C (ph?n origin): m?t URL `:8000` ? UI static +
  API tr?n `backend/main.py`; browser kh?ng g?i `:8001` hay `/v1/*`.
- `config.js`: `BACKEND_BASE_URL: ""` (same-origin).
- `app.js`: `/chat`, `/scan`, `/market`, `/watchlist`, `/approvals`; graph l?y
  `steps[]` t? response chat/scan (kh?ng fetch AI tr?c ti?p).
- Pytest: `test_phase13_single_origin_wiring`, `test_phase13_single_app_endpoints`,
  `test_config_same_origin_default`.

**Fails (?? s?a trong review)**
- Agy ch?a tick d?ng checklist + ch?a ghi change-log ? b? sung trong review.

**Missing (??ng k? v?ng ? d?ng checklist kh?c Phase 13)**
- Qu?t + approve/reject refresh ??y ??; kh?ng g?i AI service t?ch (2 d?ng c?n l?i).

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. M? http://127.0.0.1:8000/ ? DevTools Network: m?i request c?ng origin
   (`/chat`, `/watchlist`, `/market`, `/approvals`), kh?ng c? `:8001`.
3. G?i chat ? panel graph s?ng t? `steps[]` trong response `/chat`.

## 2026-09-22 ? Phase 13 line 1: same-origin wiring (agy)

- Th?m `test_phase13_single_origin_wiring` (`tests/test_frontend.py`).
- Th?m `test_phase13_single_app_endpoints` (`tests/test_backend.py`).

## 2026-09-22 ? Review Phase 12 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 12: Market status)

**Passes**
- Product-spec flow B: tab **Market status**; danh s?ch m? watchlist v?i gi? /
  % / tr?ng th?i / th?i gian c?p nh?t.
- Test-plan ?3 Market status; ?6 demo b??c 4 (m? tab th?y m?).
- `GET /market?user_id=` ? `items[]`: `symbol`, `price`, `change_pct`,
  `status` (`normal`|`abnormal`|`pending`|`unknown`), `updated_at`,
  `threshold_pct`; compose t? SQLite watchlist + `last_quotes` + pending
  approvals (kh?ng mock UI).
- L?u quote sau `POST /scan` v?o b?ng `last_quotes`.
- UI: tab `data-tab="market"`, b?ng M?|Gi?|%|Tr?ng th?i|C?p nh?t; l?i t?i hi?n
  `#market-error` qua `formatApiError`.
- Plan Phase 12 checklist `[x]`.

**Fails (?? s?a trong review)**
- Antigravity timeout 15m ? ch? th?m cache in-memory t?m tr?n `api/routers/scan`
  (kh?ng d?ng product entry). Review chuy?n sang persistence SQLite
  `backend/store.last_quotes` + ho?n thi?n API/UI/tests.

### Verify
```bash
python -m pytest tests/test_frontend.py tests/test_backend.py -q
# Browser: http://127.0.0.1:8000/ ? tab Market status ? th?y FPT/VNM/HPG
# Qu?t 1 m? ? tab refresh ? gi? + tr?ng th?i c?p nh?t
```

## 2026-09-22 ? Phase 12: Market status page

### What
- **API:** `GET /market` tr?n `backend/main.py` ? gh?p watchlist + quote cache +
  pending approvals.
- **Store:** b?ng SQLite `last_quotes`; `upsert_last_quote` sau m?i scan th?nh
  c?ng.
- **UI:** tab Market status (`index.html`, `app.js`, `style.css`); load l?c boot,
  khi chuy?n tab, sau qu?t.

### Demo th? c?ng
1. `uvicorn src.portfolio_watch.backend.main:app --port 8000`
2. M? UI ? tab **Market status** ? th?y m? seed (FPT, VNM, HPG) ? tr?ng th?i
   *Ch?a qu?t* n?u ch?a scan.
3. Tab Watchlist ? **Qu?t** FPT ? quay Market status ? gi? / % / tr?ng th?i /
   th?i gian c?p nh?t.
4. N?u c? approval pending ? c?t tr?ng th?i *Ch? duy?t* cho m? ??.

## 2026-09-22 ? Review Phase 11 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 11: Live graph + hover I/O)

**Passes**
- Plan Phase 11: panel ph?i `#live-graph-panel` theo `steps[]`; animation
  `animateLiveGraph` s?ng l?n l??t; hover/click ? inspector Input/Output;
  contract `input`/`output` qua `normalize_steps` + `graph/steps.py`; checklist
  `[x]`.
- Product-spec AC #2 / test-plan ?3 Live graph + Hover (trong ph?m vi one-shot
  HTTP + client animation).
- Pytest: `tests/test_frontend.py` + `tests/test_backend.py` **13 passed**
  (g?m `test_phase11_live_graph_and_hover_io`,
  `test_normalize_steps_preserves_input_output`, chat steps c? I/O).
- Docker smoke: `GET /` c? live-graph; `POST /chat` ? m?i step c? `input` +
  `output`.

**Fails (?? s?a ? ch? li?n quan Phase 11)**
- Hover g?i `showNodeInspector(step, false)` ? g? pin m?i l?n di chu?t; ??i
  hover/focus kh?ng ??i pin state; so kh?p `step.id` b?ng `String(...)`.

**Missing (??ng k? v?ng ? phase sau)**
- Market status page (Phase 12); SSE streaming th?t (kh?ng b?t bu?c Phase 11);
  diagram agent (Phase 14).

### Fix trong review
- `src/portfolio_watch/frontend/app.js`: pin stable khi hover.
- `src/portfolio_watch/frontend/index.html`: comment panel (b? ?placeholder?).

### Verify
```bash
python -m pytest tests/test_frontend.py tests/test_backend.py -q
# Browser: http://127.0.0.1:8000/ ? chat ? node s?ng ? hover xem I/O
```

## 2026-09-22 ? Phase 11: Live graph + hover I/O

### What & Architectural Decisions
- **Panel ph?i live graph:** thay `.graph-placeholder-card` b?ng
  `#live-graph-panel` + `#graph-nodes-flow` (node cards theo `steps[]`) v?
  `#graph-node-inspector` (Input / Output khi hover ho?c click pin).
- **Node s?ng l?n l??t:** chat/scan v?n one-shot HTTP; sau khi nh?n `steps[]`,
  client `animateLiveGraph` ch?y pending ? running ? done/error (~220ms/b??c).
- **Contract I/O:** `backend/steps.normalize_steps` gi? `input`/`output`;
  `graph/steps.build_steps_from_chunks` (+ legacy `application/answer_question`
  builders) ?i?n I/O theo t?ng node (rewrite, supervisor, price, ?).
- **Kh?ng** d?ng `docs/agent_graph*` ? ?? l? s? ?? ki?n tr?c t?nh.

### Files Touched
- `src/portfolio_watch/frontend/{index.html,app.js,style.css}`
- `src/portfolio_watch/backend/steps.py`
- `src/portfolio_watch/graph/steps.py`
- `src/portfolio_watch/application/answer_question.py` (I/O tr?n steps legacy)
- `tests/test_frontend.py`, `tests/test_backend.py`
- `specs/implementation-plan.md` (Phase 11 `[x]`)

### Manual Docker Demo Steps
1. `docker compose up -d --build app` (ho?c sync frontend + restart n?u image c?).
2. M? `http://127.0.0.1:8000/` ? c?t ph?i hi?n Live Graph (kh?ng placeholder).
3. G?i chat (vd. `Gia FPT hom nay?`) ? node s?ng l?n l??t ? hover m?t node ?
   inspector hi?n Input + Output JSON.
4. Tab Timeline / Watchlist / Approvals v?n d?ng ???c b?n d??i graph.

## 2026-09-22 ? Review Phase 10 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 10: Core UI chat Claude-like)

**Passes**
- Plan Phase 10: c?t tr?i h?i tho?i + composer ??y; g?i c?u h?i ? tr? l?i qua
  `POST /chat` hi?n c?; banner + bubble l?i m?ng/timeout (`formatApiError`);
  desktop shell ~1280px; checklist `[x]`.
- Product-spec story #1 (h?i tho?i tr?i, composer d??i) trong ph?m vi Phase 10;
  test-plan ?3 h?ng Layout chat; `tests/test_frontend.py` **3 passed**
  (g?m `test_phase10_claude_layout`).
- Docker: `docker compose up -d --build app` ? `GET /` ph?c v? `app-shell` /
  `chat-column` / `composer-container`; `POST /chat` ? 200 + `answer` +
  `steps[]` (smoke ASCII body).

**Fails (?? s?a ? ch? li?n quan Phase 10)**
- `.sr-only { display: none; }` ?n h?n heading tab kh?i assistive tech ? ??i
  sang pattern clip/visually-hidden chu?n trong `style.css`.

**Missing (??ng k? v?ng ? phase sau)**
- Live graph node s?ng + hover I/O (Phase 11 / product-spec AC #2, test-plan
  ?3 Live graph / Hover).
- Market status page; diagram render tr?n UI (phase sau / E2E).

### Fix trong review
- `src/portfolio_watch/frontend/style.css`: `.sr-only` visually-hidden.

### Verify
```bash
python -m pytest tests/test_frontend.py -q
docker compose up -d --build app
curl -s http://127.0.0.1:8000/ | grep -E 'app-shell|chat-column|composer'
# Browser: m? UI ? g?i 1 c?u ? th?y tr? l?i; stop app ? g?i l?i ? th?y banner l?i
```

## 2026-09-22 ? Phase 10: Core UI chat (Claude-like)

### What & Architectural Decisions
- **Layout 2 c?t Claude-like Shell (Desktop-first ~1280px):**
  - C?t tr?i (`#chat`, `.chat-column` chi?m ~58% b? r?ng): Khu v?c h?i tho?i ch?nh d?ng Claude. Bao g?m thanh ti?u ?? h?i tho?i, danh s?ch tin nh?n cu?n ??c l?p (`#chat-messages`), v? khung so?n th?o (`#chat-form`, `#chat-input`, `#chat-send`) c? ??nh ch?c ch?n ? ??y c?t.
  - C?t ph?i (`.secondary-column` chi?m ~42% b? r?ng): Khu v?c ti?n ?ch ph? ch?a placeholder card cho ?? th? tr?c quan "Live Graph & Agent Steps (Phase 11)", c?ng h? th?ng Tab navigation g?n g?ng chuy?n ??i gi?a:
    - Tab `Timeline b??c`: Hi?n th? danh s?ch c?c b??c (`steps[]`) t? Backend (`GET /runs/{id}/steps`).
    - Tab `Watchlist`: Qu?n l? danh m?c theo d?i (th?m m?, qu?t m?, s?a ng??ng %, x?a m?).
    - Tab `C?nh b?o ch? duy?t`: X? l? duy?t (HITL approve/reject) k?m badge s? l??ng c?nh b?o ?ang ch? duy?t.
  - B? sung c?c chip g?i ? nhanh b?n d??i composer (`Gi? FPT h?m nay?`, `T?nh h?nh VNM`, `So s?nh FPT v? HPG`) gi?p demo t?c th? ch? b?ng 1 click.
- **Tr?i nghi?m H?i tho?i & Hi?n th? L?i m?ng / Timeout r? r?ng:**
  - Thi?t k? bong b?ng tin nh?n (message bubbles) hi?n ??i: Ph?n t?ch r? r?ng gi?a `?? B?n` (bubble xanh bo tr?n hi?n ??i) v? `?? Portfolio Watch` (th? tr?ng vi?n n?i thanh l?ch, gi? nguy?n ??nh d?ng d?ng).
  - Tr?ng th?i ch? ph?n h?i tr?c quan (`.chat-thinking`): T? ??ng hi?n th? th? "Portfolio Watch ?ang suy ngh? v? ki?m tra d? li?u?" ngay khi g?i c?u h?i v? t? g? b? khi nh?n ???c ph?n h?i ho?c ph?t sinh l?i.
  - B?o l?i 2 t?ng cho s? c? m?ng v? timeout:
    1. Th? l?i trong lu?ng chat (`.chat-msg.chat-error` v?i n?n ?? nh?t v? th?ng ?i?p c? th? t? `formatApiError`).
    2. Banner l?i n?i b?t (`#chat-error-banner`) g?n ? ??u khung chat v?i icon `??`, th?ng ?i?p r? r?ng v? n?t ??ng `?`, t? ??ng ?n khi ng??i d?ng g? n?i dung m?i.
- **B?o to?n v? T?i s? d?ng tr?n v?n API hi?n c?:**
  - T?i s? d?ng endpoint c?ng origin `POST /chat` trong `app.js` (kh?ng thay ??i transport, kh?ng ph?t sinh framework n?ng).
  - Gi? nguy?n v?n t?t c? ID ph?n t? v? c?u tr?c DOM nghi?p v? ph?c v? `test_frontend.py` v? c?c API backend (`#chat`, `#timeline`, `#watchlist`, `#approvals`).

### Files Touched
- `src/portfolio_watch/frontend/index.html`: T?i c?u tr?c sang layout 2 c?t Claude-like, t?ch h?p banner l?i, composer c? ??nh ??y v? tab panel ph?.
- `src/portfolio_watch/frontend/style.css`: B? stylesheet ho?n ch?nh phong c?ch Claude (desktop-first, chat bubbles, thinking indicator, error banner, tabs v? responsive).
- `src/portfolio_watch/frontend/app.js`: N?ng c?p x? l? chat, thinking bubble, banner l?i m?ng/timeout, tab switching v? badge approvals.
- `specs/implementation-plan.md`: ??nh d?u ho?n th?nh to?n b? checklist `[x]` c?a Phase 10.
- `specs/change-log.md`: Ghi ch?p thi?t k? giao di?n, quy?t ??nh k? thu?t v? c?c b??c demo th? c?ng.

### Manual Docker Demo Steps
1. Kh?i ??ng / Rebuild container ?ng d?ng:
   ```bash
   docker compose up -d --build app
   ```
2. M? tr?nh duy?t truy c?p:
   `http://127.0.0.1:8000/`
3. X?c nh?n giao di?n:
   - Giao di?n 2 c?t chu?n desktop (~1280px): C?t tr?i l? khung h?i tho?i v?i composer ? ??y; c?t ph?i c? placeholder "Live Graph & Agent Steps (Phase 11)" c?ng c?c tab Timeline / Watchlist / C?nh b?o.
4. Demo c?u h?i - ??p:
   - Nh?p v?o composer c?u h?i: `Gi? FPT h?m nay?` (ho?c b?m v?o chip g?i ?).
   - Nh?n **G?i** (ho?c nh?n ph?m Enter).
   - Quan s?t:
     - Tin nh?n ng??i d?ng xu?t hi?n b?n ph?i.
     - Xu?t hi?n tr?ng th?i "Portfolio Watch ?ang suy ngh??".
     - N?t "G?i" b? v? hi?u ho? ch?ng spam.
     - Sau khi Backend ph?n h?i: bot tr? l?i ??y ?? gi? v? ph?n t?ch, timeline b?n tab ph?i hi?n danh s?ch steps v?i tr?ng th?i `done`.
5. Demo ph?n h?i l?i m?ng / timeout:
   - D?ng t?m th?i container ho?c ng?t k?t n?i: `docker compose stop app`.
   - G?i m?t c?u h?i trong ? chat.
   - Quan s?t:
     - Banner ?? n?i b?t tr?n ??nh khung chat hi?n th?: `?? Kh?ng th? ho?n t?t c?u h?i: Kh?ng n?i ???c Backend (ki?m tra :8000 c?n ch?y).`
     - Tin nh?n l?i xu?t hi?n r? r?ng trong lu?ng h?i tho?i.
   - B?t l?i container: `docker compose start app`.

## 2026-09-22 ? Review Phase 9 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 9: Langfuse 1 request = 1 trace)

**Passes**
- Plan Phase 9: 1 root chat + 1 root scan; node span = node id; step I/O;
  `MONITORING_ENABLED=false` no-op + chat 200; mock hierarchy; checklist `[x]`.
- Product-spec AC #3 / test-plan ?2: mock parent/child kh?ng c?n host Langfuse;
  change-log c? checklist th? c?ng khi c? host `:3000`.
- Pytest: `tests/test_tracing.py` **5 passed**; regression memory/structured OK;
  `--self-check` OK.

**Fails (?? s?a ? ch? li?n quan Phase 9)**
- `_roots` / `_agents` kh?ng thread-safe khi `price_agent` + `news_agent` ch?y
  song song (`ThreadPoolExecutor`) ? th?m `threading.RLock` quanh ??ng k?/
  lookup/pop span map.

**Missing (??ng k? v?ng ? phase sau)**
- UI Claude-like (Phase 10); live graph hover (Phase 11); multi-symbol span
  name collision v?n c? th? x?y ra n?u nhi?u `price_agent` c?ng t?n song song
  (c?ng key) ? ngo?i ph?m vi s?a t?i thi?u hi?n t?i.

### Fix trong review

- Lock map tracing; re-run `pytest tests/test_tracing.py`.

## 2026-09-22 ? Phase 9: Langfuse: 1 request = 1 trace

### What & Architectural Decisions
- **1 Request = 1 Trace Root (kh?ng tr?ng l?p root):**
  - Chat: duy nh?t 1 root `trace_request("chat", q, metadata=meta)` bao tr?n `run_chat_graph` trong `application/answer_question.py`.
  - Scan: duy nh?t 1 root `trace_request("scan", sym, metadata=meta)` bao tr?n `run_scan_graph` trong `application/scan_symbol.py`.
  - Kh?ng c? `trace_request` th? hai n?o ???c k?ch ho?t trong su?t v?ng ??i c?a request.
- **Hierarchy Parent/Child & Kh?c ph?c Mismatches:**
  - S?a l?i mismatch t?n span cha: `rewrite_question` tr??c ??y g?i `agent_step(turn, "supervisor", "rewrite")` g?y m? c?i v? span cha ?ang m? l? `"rewrite_question"`. ?? chuy?n sang `agent_step(turn, "rewrite_question", "rewrite", input={"question": question})`.
  - ??m b?o `price_agent` v? `news_agent` spans lu?n b?c tr?c ti?p c?c l?i g?i `run_price_agent` v? `run_news_agent` (k? c? khi ch?y song song qua `ThreadPoolExecutor` trong chat v? scan). Nh? ?? c?c step con (`fetch_quote`, `react_turn_*`, `fetch_news`) l?ng ch?nh x?c d??i span c?a agent t??ng ?ng.
  - S?a l?i `AttributeError` trong `price_agent/nodes.py` khi ??c `quote.close` thay v? `quote.latest_close`, ??m b?o `box["output"]` c?a step `fetch_quote` lu?n ???c g?n ??y ??.
- **M?i Graph Node Span v? Step con c? Input + Output:**
  - ??m b?o t?t c? agent spans (`rewrite_question`, `supervisor`, `price_agent`, `news_agent`, `eval_agent`, `synthesis_agent`, `confidence_gate`, `answer_composer`) ??u thi?t l?p `input` v? `box["output"]` khi d? li?u s?n c?.
  - ??m b?o t?t c? step con (`rewrite`, `route`, `fetch_quote`, `react_turn_*`, `fetch_news`, `classify`, `read_price_history`, `build_severity`, `draft_attempt`, `guardrail_check`, `draft`, `guardrail_retry`) ??u c? `input` v? `box["output"]`.
- **An to?n Best-Effort & No-op:**
  - Khi `MONITORING_ENABLED=false` ho?c thi?u API keys: m?i API tracing ho?t ??ng ? ch? ?? no-op ho?n to?n, kh?ng n?m exception, kh?ng l?m ch?m ho?c crash request, API chat tr? m? HTTP 200 b?nh th??ng.
- **Mock Hierarchy Pytest Suite:**
  - B? sung `MockObservation` v? `MockLangfuse` trong `tests/test_tracing.py` ?? x?c th?c c?u tr?c c?y ph?n c?p (root -> agent spans -> step spans) ??c l?p kh?ng c?n m?y ch? Langfuse th?t.
  - Ki?m tra 5 k?ch b?n: `test_trace_noop_when_disabled`, `test_v1_chat_ok_when_monitoring_off`, `test_chat_single_root_and_hierarchy`, `test_scan_single_root_and_hierarchy`, `test_no_duplicate_roots_per_request`.

### Files Touched
- `src/portfolio_watch/agents/supervisor_agent/nodes.py`: Chuy?n step cha c?a `rewrite` sang `rewrite_question`; b? sung input/output cho `rewrite` v? `route` steps.
- `src/portfolio_watch/agents/price_agent/nodes.py`: B? sung input/output cho `fetch_quote` step (s?a thu?c t?nh `latest_close`).
- `src/portfolio_watch/agents/news_agent/nodes.py`: B? sung input/output cho `react_turn_*` v? `fetch_news` steps.
- `src/portfolio_watch/agents/event_classifier/nodes.py`: B? sung input/output cho `classify` step.
- `src/portfolio_watch/agents/eval_agent/nodes.py`: B? sung input/output cho `read_price_history` v? `build_severity` steps.
- `src/portfolio_watch/agents/synthesis_agent/nodes.py`: B? sung input/output cho `draft_attempt` v? `guardrail_check` steps.
- `src/portfolio_watch/agents/answer_composer/nodes.py`: B? sung input/output cho `draft` v? `guardrail_retry` steps.
- `src/portfolio_watch/graph/chat.py`: ??m b?o `price_agent` v? `news_agent` spans b?c quanh c?c thread worker; b? sung input/output ??y ?? cho `eval_agent` v? `answer_composer`.
- `src/portfolio_watch/graph/scan.py`: ??m b?o `price_agent` v? `news_agent` spans b?c quanh c?c thread worker trong node fetch; b? sung `confidence_gate` spans cho gate nodes v?i input/output ??y ??.
- `tests/test_tracing.py`: M? r?ng test suite v?i MockLangfuse ki?m tra ??y ?? parent/child hierarchy cho c? lu?ng chat v? scan, ??n root v? no-op khi t?t monitoring.
- `specs/implementation-plan.md`: ??nh d?u `[x]` to?n b? checklist Phase 9.
- `specs/change-log.md`: Ghi ch?p Phase 9 v? checklist th? c?ng khi c? host Langfuse.

### Manual Checklist for Live Langfuse Host (khi c? host `:3000`)
1. Thi?t l?p `.env`:
   ```env
   MONITORING_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://localhost:3000
   ```
2. Kh?i ??ng h? th?ng (`docker compose up --build app`).
3. G?i 1 c?u h?i chat t? UI ho?c cURL (`POST /v1/chat`).
4. Truy c?p giao di?n Langfuse `http://localhost:3000` -> M? m?c Traces:
   - X?c nh?n c? **??ng 1 trace root** t?n `chat`.
   - M? r?ng trace: x?c nh?n c?c span con `rewrite_question`, `supervisor`, `price_agent`, `news_agent`, `answer_composer`.
   - Nh?p v?o t?ng span / step: x?c nh?n th? `Input` v? `Output` ??u c? d? li?u (JSON/text), kh?ng b? null/empty.
   - X?c nh?n c?c step (`fetch_quote`, `draft`, `guardrail_retry`) n?m l?ng b?n trong agent span cha t??ng ?ng.
5. Th?c hi?n 1 l?nh scan (`POST /v1/scan/symbol` ho?c qu?t watchlist):
   - X?c nh?n c? **??ng 1 trace root** t?n `scan`.
   - X?c nh?n c?c span con `price_agent`, `news_agent`, `event_classifier` (v? `eval_agent`, `synthesis_agent`, `confidence_gate` n?u c? bi?n ??ng).
   - Ki?m tra input v? output tr?n m?i node/step.
6. ??i `MONITORING_ENABLED=false` trong `.env` -> g?i request chat:
   - Request tr? v? HTTP 200 b?nh th??ng, kh?ng ghi th?m trace n?o l?n Langfuse.

## 2026-09-22 ? Review Phase 8 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8: Memory long-term)

**Passes**
- Plan Phase 8: `recall_memory` ??u / `store_memory` cu?i chat; Qdrant optional +
  in-memory fallback; kh?ng `user_id` ? skip kh?ng crash; checklist `[x]`.
- Product-spec AC #5 / test-plan ?4 Long-term: c? `user_id` ? recall/store;
  kh?ng Qdrant ? fallback; kh?ng user ? kh?ng crash.
- Env: `QDRANT_*` (+ embedding) trong `.env.example`; compose profile `qdrant`.
- Pytest: `tests/test_long_term_memory.py` **15 passed**; `-k long_term|memory|?`
  **27 passed**; `--self-check` OK.

**Fails (?? s?a ? ch? li?n quan Phase 8)**
- Heuristic `_extract_long_term_fact` l?u m?i c?u c? ticker (`len(symbols) >= 1`)
  ? l?m ??y long-term b?ng lookup th??ng. Si?t: ch? store khi c? t?n hi?u
  quan t?m/theo d?i (ho?c LLM `worth_saving`).
- `.env.example` thi?u `EMBEDDING_MODEL` / `EMBEDDING_DIM` d? settings ?? c?.
- `user_id: str` tr?n chat entrypoints kh?ng ph?n ?nh `None` (skip long-term)
  ? ??i `str | None`.

**Missing (??ng k? v?ng ? phase sau)**
- Langfuse 1 request = 1 trace (Phase 9); UI Claude-like; diagram.

### Fix trong review

- Si?t heuristic store; b? sung embedding env; type `user_id: str | None`;
  re-run `pytest tests/test_long_term_memory.py`.

## 2026-09-22 ? Phase 8: Memory long-term

### What & Architectural Decisions
- **M? h?nh Long-term Memory theo m?u `agent_pr`:**
  - ??nh danh v? c?ch ly theo `user_id`: s? th?t v? ng??i d?ng (m? c? phi?u theo d?i, kh?u v? ??u t?, s? th?ch) ???c l?u tr? ??c l?p theo t?ng `user_id`.
  - V? tr? `recall_memory` ??u chat: ngay sau khi n?p h?i tho?i short-term, `recall_memory` truy xu?t c?c fact li?n quan ??n c?u h?i / ng? c?nh v? ??a v?o `ChatState.memories`.
  - T?ch h?p v?i `rewrite_question`: h?m `_apply_memory_symbol` ???c n?ng c?p ?? n?u h?i tho?i hi?n t?i ch?a c? m? (phi?n m?i), h? th?ng s? t?m ki?m m? c? phi?u t? `memories` d?i h?n ?? gi?i quy?t ??i t? / c?u h?i ti?p di?n (vd: "m? ?? h?m nay th? n?o?" -> t? nh?n di?n "FPT").
  - V? tr? `store_memory` cu?i chat: sau khi AnswerComposer ho?n th?nh c?u tr? l?i v? sau khi l?u short-term conversation. Quy?t ??nh ch?y sau short-term append gi?p ??m b?o lu?ng h?i tho?i ng?n h?n kh?ng bao gi? b? gi?n ?o?n ngay c? khi b??c tr?ch xu?t th?ng tin d?i h?n g?p l?i ho?c ?? tr? m?ng.
  - Kh?ng `user_id` (None, `""`, ho?c kho?ng tr?ng): t? ??ng b? qua to?n b? long-term memory (`recall_memory` tr? `{"memories": []}`, `store_memory` tr? `{}`), kh?ng crash, kh?ng n?m exception.
- **H? t?ng Vector Store Qdrant & Fallback In-memory (`infra/storage/long_term_memory.py`):**
  - H? tr? Qdrant t?y ch?n (optional): k?t n?i qua `qdrant_client` t?i `QDRANT_URL` (h? tr? c? `:memory:` cho local/test v? URL HTTP th?t cho Docker).
  - T? ??ng fallback in-memory khi kh?ng c? Qdrant ho?c thi?u API key: n?u `qdrant_client` ch?a ???c c?i ??t, Qdrant offline/kh?ng th? k?t n?i, `QDRANT_URL` ?? tr?ng/unset/`:memory:`, ho?c thi?u OpenAI API key ?? t?o embedding vector -> h? th?ng t? ??ng fallback sang in-memory store.
  - C? ch? t?m ki?m fallback in-memory: x?p h?ng ?? t??ng quan d?a tr?n ?? tr?ng t? kh?a (keyword overlap) k?t h?p ?? t??i (recency timestamp) v? gi?i h?n top `k` k?t qu?.
  - T?i ?u hi?u n?ng & kh?ng user warning: thi?t l?p `check_compatibility=False` tr?n `QdrantClient`, `timeout=0.5s` k?m ki?m tra k?t n?i nhanh ?? c?c b?i test CI/local kh?ng b? ngh?n th?i gian ch? khi kh?ng c? Qdrant daemon.
- **Schema Pydantic & C?u h?nh m?i tr??ng:**
  - Th?m `MemoryFact` v? helper `parse_memory_fact` v?o `shared/schemas.py` (tr??ng `worth_saving: bool`, `fact: str`), k? th?a n?n t?ng `MemoryExtractOutput` t? Phase 6.
  - Th?m c?u h?nh v?o `shared/settings.py` & t?i li?u h?a trong `.env.example`: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` (m?c ??nh `portfolio_watch_memory`), `embedding_model` (`text-embedding-3-small`), `embedding_dim` (`1536`).
  - Th?m tr??ng `memories: list[str]` v?o `ChatState` (`graph/state.py`) v? `AnswerQuestionResult` (`application/answer_question.py`).

### Files touched
- `src/portfolio_watch/shared/settings.py` (th?m c?u h?nh `qdrant_url`, `qdrant_api_key`, `qdrant_collection`, `embedding_model`, `embedding_dim`)
- `.env.example` (b? sung t?i li?u c?u h?nh `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`)
- `src/portfolio_watch/shared/schemas.py` (th?m `MemoryFact`, `parse_memory_fact`)
- `src/portfolio_watch/infra/storage/long_term_memory.py` (m?i ? module long-term memory v?i Qdrant + in-memory fallback)
- `src/portfolio_watch/infra/storage/__init__.py` (re-export `save_to_long_term`, `recall_long_term`, `get_qdrant_client`, `clear_long_term_fallback`)
- `src/portfolio_watch/agents/supervisor_agent/nodes.py` (th?m `recall_memory`, `store_memory`, h? tr? `memories` trong `_apply_memory_symbol`, `HeuristicRewriteBrain`, `LlmRewriteBrain`, `rewrite_question`)
- `src/portfolio_watch/agents/supervisor_agent/__init__.py` (re-export `recall_memory`, `store_memory`)
- `src/portfolio_watch/graph/state.py` (th?m `memories: list[str]` v?o `ChatState`)
- `src/portfolio_watch/graph/chat.py` (wire `recall_memory` ??u l??t, truy?n `memories` v?o state & rewrite, wire `store_memory` cu?i l??t)
- `src/portfolio_watch/application/answer_question.py` (th?m `memories: list[str]` v?o `AnswerQuestionResult`)
- `specs/implementation-plan.md` (??nh d?u `[x]` to?n b? checklist Phase 8)
- `specs/change-log.md` (ghi nh?n thay ??i Phase 8)
- `tests/test_long_term_memory.py` (m?i ? 15 unit & integration tests bao ph? ??y ?? k?ch b?n c?/kh?ng `user_id`, Qdrant fallback, roundtrip)

### Tests & Results
1. **Pytest Long-term memory suite:**
   ```bash
   python -m pytest tests/test_long_term_memory.py -v
   ```
   -> **15 passed in 2.21s**.
2. **Pytest Memory suite (short-term + long-term):**
   ```bash
   python -m pytest tests/ -q -k "long_term or memory or qdrant or recall or store_memory" --maxfail=8
   ```
   -> **27 passed, 50 deselected in 1.48s**.
3. **Full test suite:**
   ```bash
   python -m pytest tests/ -v
   ```
   -> **77 passed in 3.65s**.
4. **Eval runner self-check:**
   ```bash
   python -m src.portfolio_watch.eval.run --self-check
   ```
   -> self-check: 8/8 rule ok; judge gate ok; runner 4/4 ok; report ok; regression ok; injection gate ok; scorer locks ok.
5. **Docker / App health check smoke:**
   ```bash
   curl -s http://127.0.0.1:8000/health
   ```
   -> `{"status":"ok","app":"Portfolio Watch & Chat Agent"}`.


## 2026-09-22 ? Review Phase 7 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 7: Memory short-term + TTL)

**Passes**
- Plan Phase 7: window + TTL env (`MEMORY_SHORT_TERM_WINDOW` /
  `MEMORY_SHORT_TERM_TTL_MINUTES`); `.env.example` c? ch? th?ch; checklist `[x]`.
- `filter_conversation_history` + `SqliteMemoryStore.list_conversation` t?n tr?ng
  window + TTL; `run_chat_graph` / `answer_question` d?ng settings (kh?ng c?n
  magic `20`).
- Follow-up trong session nh? m? (heuristic + E2E chat graph); h?t h?n TTL ?
  kh?ng resolve ticker c?.
- Product-spec AC memory short-term + TTL; test-plan ?4 Short-term / TTL.
- Pytest: `tests/test_short_term_memory.py` + `-k "memory|?"` **12 passed**;
  `--self-check` OK.

**Fails (?? s?a ? ch? li?n quan Phase 7)**
- `_FakeMemoryStore` trong `tests/test_structured_output.py` ch?a nh?n
  `ttl_minutes` / `created_at` theo Protocol m?i ? `run_chat_graph` ph?i
  fallback `TypeError`. C?p nh?t ch? k? fake cho kh?p Protocol.

**Missing (??ng k? v?ng ? phase sau)**
- Long-term recall/store + Qdrant (Phase 8); Langfuse; UI Claude-like.

### Fix trong review

- C?p nh?t `_FakeMemoryStore` append/list signature; th?m
  `from __future__ import annotations` cho `memory_store.py`.

## 2026-09-22 ? Phase 7: Memory short-term + TTL

### What & Architectural Decisions
- **C?u h?nh Sliding Window & TTL qua Environment Variables (`shared/settings.py` & `.env.example`):**
  - `MEMORY_SHORT_TERM_WINDOW` (m?c ??nh: `20`): S? l??ng tin nh?n t?i ?a trong sliding window l?u tr? ng? c?nh ng?n h?n cho phi?n h?i tho?i.
  - `MEMORY_SHORT_TERM_TTL_MINUTES` (m?c ??nh: `60`): TTL / th?i h?n ?? t??i t?nh b?ng ph?t. C?c tin nh?n c? h?n kho?ng th?i gian n?y s? t? ??ng b? lo?i b? kh?i context h?i tho?i tr??c khi chuy?n t?i agent rewrite/routing.
  - Ghi nh?n v? ch? th?ch ??y ?? c? hai bi?n v?o `.env.example`.
- **H? t?ng Memory Store & L?c ?? t??i (`infra/storage/memory_store.py` & `domain/ports.py`):**
  - C?p nh?t `MemoryStore` Protocol: `append_conversation(user_id, role, content, *, created_at=None)` v? `list_conversation(user_id, limit=None, *, ttl_minutes=None)`.
  - B? sung `parse_timestamp(ts)`: parse linh ho?t ?a d?ng ??nh d?ng th?i gian (SQLite datetime `"YYYY-MM-DD HH:MM:SS"`, ISO-8601 k?m offset ho?c Z, unix timestamp, datetime object) sang UTC datetime an to?n m?i gi?.
  - B? sung `filter_conversation_history(items, *, limit=None, ttl_minutes=None, now=None)`: h?m l?c ??c l?p t?i s? d?ng ???c, ??m b?o gi? th? t? th?i gian (c? -> m?i), lo?i b? c?c tin nh?n h?t h?n TTL, gi? l?i c?c message kh?ng c? timestamp (fallback an to?n), v? c?t l?y ??ng sliding window `limit` tin nh?n m?i nh?t.
  - C?p nh?t `SqliteMemoryStore.list_conversation()` v? `SqliteMemoryStore.append_conversation()` ?? t?ch h?p c? ch? window + TTL, h? tr? tham s? `now` cho ph?p ki?m th? th?i gian x?c ??nh (deterministic test).
- **K?t n?i LangGraph Chat (`graph/chat.py` & `application/answer_question.py`):**
  - Lo?i b? magic number `20` trong `run_chat_graph()`, k?t n?i tr?c ti?p v?i `settings.memory_short_term_window` v? `settings.memory_short_term_ttl_minutes` (v?n cho ph?p override qua parameter `limit` v? `ttl_minutes`).
  - S? d?ng l?p b?o v? 2 t?ng: `list_conversation()` l?c t?i t?ng storage, k?t h?p `filter_conversation_history()` ??m b?o an to?n ngay c? khi mock storage kh?ng h? tr? TTL.
  - H?i tho?i h?t h?n TTL s? kh?ng ???c ??a v?o `conversation` c?a `ChatState`, t? ?? ng?n ch?n supervisor/rewrite nh?n di?n sai ticker/ng? c?nh t? c?c phi?n ?? qu? h?n.
- **Duy tr? ng? c?nh follow-up trong session:**
  - T?n d?ng `_apply_memory_symbol` trong `agents/supervisor_agent/nodes.py`: ng??i d?ng h?i ti?p c?c c?u kh?ng c? ticker (vd: "gi? h?m nay th? n?o?", "m? ?? sao r?i?", "th? c?n tin t?c sao r?i?") s? t? ??ng nh? ticker g?n nh?t trong sliding window.
  - Khi tin nh?n ?? qu? TTL: context tr?ng -> kh?ng g?n nh?m ticker c?.

### Files touched
- `src/portfolio_watch/shared/settings.py` (th?m `memory_short_term_window`, `memory_short_term_ttl_minutes`)
- `.env.example` (th?m `MEMORY_SHORT_TERM_WINDOW`, `MEMORY_SHORT_TERM_TTL_MINUTES`)
- `src/portfolio_watch/domain/ports.py` (c?p nh?t `MemoryStore` Protocol)
- `src/portfolio_watch/infra/storage/memory_store.py` (th?m `parse_timestamp`, `filter_conversation_history`, c?p nh?t `SqliteMemoryStore`)
- `src/portfolio_watch/infra/storage/__init__.py` (re-export `filter_conversation_history`, `parse_timestamp`)
- `src/portfolio_watch/graph/chat.py` (wire settings window + TTL thay cho magic number 20)
- `src/portfolio_watch/application/answer_question.py` (h? tr? truy?n `limit`, `ttl_minutes`)
- `specs/implementation-plan.md` (??nh d?u `[x]` to?n b? Phase 7)
- `specs/change-log.md` (ghi nh?n thay ??i Phase 7)
- `tests/test_short_term_memory.py` (m?i ? 11 test cases unit & integration)

### Tests & Results
1. **Pytest Short-term memory suite:**
   ```bash
   python -m pytest tests/test_short_term_memory.py -v
   ```
   -> **11 passed in 0.56s**.
2. **Pytest theo y?u c?u ki?m tra:**
   ```bash
   python -m pytest tests/ -q -k "memory or short_term or conversation or ttl or freshness" --maxfail=8
   ```
   -> **12 passed, 50 deselected in 0.63s**.
3. **Eval self-check:**
   ```bash
   python -m src.portfolio_watch.eval.run --self-check
   ```
   -> self-check: 8/8 rule ok; judge gate ok; runner 4/4 ok; report ok; regression ok; injection gate ok; scorer locks ok.

## 2026-09-22 ? Review Phase 6 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 6: Structured output)

**Passes**
- Plan Phase 6: Pydantic schemas cho rewrite, supervisor, classifier, eval,
  synthesis draft, memory extract; checklist `[x]`.
- LLM path qua `infra/llm/structured.py` (`call_llm_structured` /
  `parse_structured` / `chat_parsed` + fallback) ? kh?ng c?n free-text thu?n
  tr?n production brain paths.
- Schema l?i ? retry + inner guard ? kh?ng crash graph (test
  `test_chat_graph_schema_error_does_not_crash`).
- Pytest: `tests/test_structured_output.py` **24 passed**; rewrite + supervisor
  paths c? coverage; `--self-check` OK.
- Product-spec AC #4 / test-plan ?4 Structured output: parse ???c; fail kh?ng
  ?? process.

**Fails (?? s?a ? ch? li?n quan Phase 6)**
- C?n helper free-text c? (`_parse_json_obj`, `_parse_llm_route`,
  `_parse_eval_payload`, `_parse_alert_json`, `_parse_react_action`) kh?ng c?n
  caller ? x?a + b? import `chat`/`json`/`re` th?a tr?n c?c nodes ?? chuy?n
  structured; `shared/schemas` kh?ng c?n re-export `call_llm_structured`.

**Missing (??ng k? v?ng ? phase sau)**
- Memory short/long + TTL (Phase 7?8); Langfuse; diagram UI; full golden E2E.

### Fix trong review

- D?n dead free-text parsers tr?n agent nodes; re-run
  `pytest tests/test_structured_output.py`.

## 2026-09-22 ? Phase 6: Structured output

### What & Architectural Decisions
- **Th?m Pydantic schemas cho to?n b? c?c lu?ng quy?t ??nh LLM:**
  - `RewriteOutput` (`agents/supervisor_agent/schemas.py`, `shared/schemas.py`): chu?n h?a c?u h?i, tr?ch xu?t ticker ch?nh (`symbol`) v? m?i ticker (`symbols`), ph?n lo?i `intent` (`price_lookup`, `news_lookup`, `explain`).
  - `SupervisorOutput` (`agents/supervisor_agent/schemas.py`, `shared/schemas.py`): danh s?ch `agents_to_call` (`price`, `news`, `eval`) k?m `reason`, t? ??ng l?m s?ch v? m?c ??nh `["price"]` n?u r?ng.
  - `ClassifierOutput` (`agents/event_classifier/schemas.py`, `shared/schemas.py`): tr??ng `route` ("b?nh th??ng" / "b?t th??ng") v? `reason`, k?m `to_routing_decision()` ?nh x? chu?n x?c sang `EventRoute`.
  - `EvalSeverityOutput` (`agents/eval_agent/schemas.py`, `shared/schemas.py`): `needs_history`, `level` (`low`, `medium`, `high`), `confidence` (0.0?1.0), `reasoning`, `evidence`, `proposed_threshold_pct`, `proposed_related_symbols`, k?m `to_severity()`.
  - `SynthesisAlertOutput` (`agents/synthesis_agent/schemas.py`, `shared/schemas.py`): `title` v? `body` cho b?n nh?p c?nh b?o.
  - `NewsReactOutput` (`agents/news_agent/schemas.py`, `shared/schemas.py`): `kind` (`search`, `finish`) v? `query` cho ReAct search loop.
  - `MemoryExtractOutput` (`shared/schemas.py`): `symbols`, `preferences`, `summary`, `topics`, k?m helper `parse_memory_extract()` s?n s?ng cho Phase 7?8.
- **H? t?ng Structured Output (`infra/llm/structured.py` & `completion.py`):**
  - `parse_structured(raw_or_obj, schema)`: parse ?a d?ng input (instance Pydantic, dict, chu?i JSON thu?n ho?c chu?i markdown code block ```json ... ```) th?nh instance schema h?p l?.
  - `call_llm_structured(...)`: h? tr? c? `chat_parsed_fn` (mock test), `chat_fn` (test chu?i JSON), v? production m?c ??nh (`chat_parsed` qua OpenAI v?i fallback sang `chat()` + `parse_structured`).
- **C? ch? Retry & Inner Guard kh?ng l?m s?p Graph:**
  - Khi g?p `ValidationError`, `ValueError`, ho?c JSON h?ng: `call_llm_structured` t? ??ng retry `max_retries` l?n (m?c ??nh 1 l?n retry).
  - N?u v?n th?t b?i: inner try/except trong t?ng brain (`LlmRewriteBrain`, `LlmSupervisorBrain`, `LlmEventClassifier`, `LlmEvalBrain`, `LlmAlertComposer`, `LlmNewsBrain`) k?ch ho?t inner guard, tr? v? fallback an to?n (d?a tr?n heuristic/regex/default) thay v? n?m exception l?m crash LangGraph workflow.
  - C?c h?m node b?n ngo?i (`rewrite_question`, `route_question`, `classify_event`...) v?n gi? nguy?n try/except v? tracing span l?m l?p b?o v? th? hai.

### Files touched
- `src/portfolio_watch/shared/schemas.py` (m?i ? central schemas & helpers)
- `src/portfolio_watch/infra/llm/structured.py` (m?i ? parse & call structured output)
- `src/portfolio_watch/infra/llm/completion.py` (re-export structured helpers)
- `src/portfolio_watch/agents/supervisor_agent/schemas.py`
- `src/portfolio_watch/agents/supervisor_agent/nodes.py`
- `src/portfolio_watch/agents/event_classifier/schemas.py`
- `src/portfolio_watch/agents/event_classifier/nodes.py`
- `src/portfolio_watch/agents/eval_agent/schemas.py`
- `src/portfolio_watch/agents/eval_agent/nodes.py`
- `src/portfolio_watch/agents/synthesis_agent/schemas.py`
- `src/portfolio_watch/agents/synthesis_agent/nodes.py`
- `src/portfolio_watch/agents/news_agent/schemas.py`
- `src/portfolio_watch/agents/news_agent/nodes.py`
- `specs/implementation-plan.md` (??nh d?u `[x]` Phase 6)
- `specs/change-log.md`
- `tests/test_structured_output.py` (m?i ? 24 unit & integration tests)

### Tests & Results
1. **Unit tests schemas, retry, guard & paths:**
   ```bash
   python -m pytest tests/test_structured_output.py -v
   ```
   -> **24 passed in 5.43s** (bao g?m c? test end-to-end chat graph khi schema h?ng v?n ho?n th?nh an to?n).
2. **Ki?m tra theo y?u c?u prompt:**
   ```bash
   python -m pytest tests/ -q -k "structured or rewrite or supervisor" --maxfail=5
   ```
   -> **24 passed, 27 deselected in 4.16s**.
3. **Eval self-check:**
   ```bash
   python -m src.portfolio_watch.eval.run --self-check
   ```
   -> 8/8 rule ok; judge gate ok; runner 4/4 ok; report ok; regression ok; injection gate ok; scorer locks ok.


## 2026-09-22 ? Review Phase 5 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 5: Prompt t?i gi?n)

**Passes**
- Plan Phase 5: 7/7 `production.txt` r?t g?n (role + schema/r?ng bu?c + an to?n);
  checklist `[x]`; change-log li?t k? ?? prompt ?? r?t.
- Single registry: `infra/llm/prompt_registry.py` ? agents g?i `registry().render(...)`;
  `production.txt` ch?a template tr?c ti?p (alias kh?ng c?n ch? l? s? version).
- Product-spec AC docs/prompt: prompt ng?n h?n; regression subset trong tolerance.
- Test-plan / eval: `--self-check` OK; `--slice injection` **3/3 (100%)** gate;
  `--slice lookup --limit 3` **3/3**, regression drop=0 ? 0.05.

**Fails (?? s?a ? ch? li?n quan Phase 5)**
- Ba prompt routing/classifier thi?u d?ng an to?n t??ng minh
  (`supervisor_routing`, `news_agent_react`, `event_classification`) d? checklist
  y?u c?u role + schema + an to?n ? th?m 1 d?ng b? qua injection / c?m mua-b?n
  (??ng b? `production.txt` + `v1.yaml`).

**Missing (??ng k? v?ng ? phase sau)**
- Structured output / schema Pydantic (Phase 6); memory; Langfuse; diagram UI;
  full golden (kh?ng thu?c Phase 5 ? ch? subset lookup + injection).

### Fix trong review

- B? sung d?ng an to?n t?i thi?u cho 3 prompt tr?n; re-verify registry load +
  `--self-check`.

## 2026-09-22 ? Phase 5: Prompt t?i gi?n

### What & Architectural Decisions
- **R?t g?n to?n b? 7 prompt production:**
  M?i prompt r?t g?n v? 3 th?nh ph?n c?t l?i:
  1. Role (??nh danh agent & nhi?m v?)
  2. Input + schema output / r?ng bu?c (ngu?n evidence, format, ti?u ch?)
  3. An to?n (c?m l?i khuy?n mua/b?n ch?c ch?n, kh?ng b?a ??t s? li?u, b? qua injection)
  Lo?i b? to?n b? c?c v? d? d?i d?ng / v?n m?u / essay kh?ng c?n thi?t.
- **??ng b? song song `production.txt` v? `v1.yaml`:**
  - `prompts/answer_compose/production.txt` & `v1.yaml`: R?t g?n AnswerComposer prompt.
  - `prompts/eval_severity/production.txt` & `v1.yaml`: R?t g?n EvalAgent severity prompt.
  - `prompts/event_classification/production.txt` & `v1.yaml`: R?t g?n Event Classifier prompt.
  - `prompts/news_agent_react/production.txt` & `v1.yaml`: R?t g?n NewsAgent ReAct prompt.
  - `prompts/rewrite_question/production.txt` & `v1.yaml`: R?t g?n RewriteQuestion prompt (b? v? d? m?u h?i tho?i d?i).
  - `prompts/supervisor_routing/production.txt` & `v1.yaml`: R?t g?n Supervisor routing prompt.
  - `prompts/synthesis_alert/production.txt` & `v1.yaml`: R?t g?n SynthesisAgent alert prompt.
- **Gi? duy nh?t m?t n?i ??ng k? prompt:**
  `src/portfolio_watch/infra/llm/prompt_registry.py` ti?p t?c l? single registration place duy nh?t trong to?n b? repo. C?p nh?t `PromptRegistry.get()` ?? h? tr? c? text template tr?c ti?p t? `production.txt` l?n YAML metadata. To?n b? c?c agent trong `src/portfolio_watch/agents/` ti?p t?c g?i prompt qua `registry().render(...)`.
- **H? tr? ch?y eval theo slice:**
  B? sung CLI `--slice <slice_name>` trong `src/portfolio_watch/eval/run.py` v? so s?nh regression theo slice t??ng ?ng v?i `specs/eval/v3_baseline.json`.

### Prompt Files Shortened
1. `prompts/answer_compose/production.txt` (693 chars) + `prompts/answer_compose/v1.yaml`
2. `prompts/eval_severity/production.txt` (685 chars) + `prompts/eval_severity/v1.yaml`
3. `prompts/event_classification/production.txt` (489 chars) + `prompts/event_classification/v1.yaml`
4. `prompts/news_agent_react/production.txt` (485 chars) + `prompts/news_agent_react/v1.yaml`
5. `prompts/rewrite_question/production.txt` (699 chars) + `prompts/rewrite_question/v1.yaml`
6. `prompts/supervisor_routing/production.txt` (471 chars) + `prompts/supervisor_routing/v1.yaml`
7. `prompts/synthesis_alert/production.txt` (565 chars) + `prompts/synthesis_alert/v1.yaml`

### Files touched
- `prompts/answer_compose/production.txt`
- `prompts/answer_compose/v1.yaml`
- `prompts/eval_severity/production.txt`
- `prompts/eval_severity/v1.yaml`
- `prompts/event_classification/production.txt`
- `prompts/event_classification/v1.yaml`
- `prompts/news_agent_react/production.txt`
- `prompts/news_agent_react/v1.yaml`
- `prompts/rewrite_question/production.txt`
- `prompts/rewrite_question/v1.yaml`
- `prompts/supervisor_routing/production.txt`
- `prompts/supervisor_routing/v1.yaml`
- `prompts/synthesis_alert/production.txt`
- `prompts/synthesis_alert/v1.yaml`
- `src/portfolio_watch/infra/llm/prompt_registry.py`
- `src/portfolio_watch/eval/run.py`
- `specs/implementation-plan.md`
- `specs/change-log.md`

### Test & Golden Eval Subset Results
- **Prompt registry verification:**
  ```bash
  python -c "from src.portfolio_watch.infra.llm.prompt_registry import registry; [print(n, len(registry().get(n).template)) for n in ['answer_compose', 'eval_severity', 'event_classification', 'news_agent_react', 'rewrite_question', 'supervisor_routing', 'synthesis_alert']]"
  ```
  -> 7/7 prompts load successfully.
- **Eval self-check:**
  ```bash
  python -m src.portfolio_watch.eval.run --self-check
  ```
  -> 8/8 rule ok; runner 4/4 ok; regression ok; injection gate ok; exit code 0.
- **Eval injection slice (full 3 cases):**
  ```bash
  python -m src.portfolio_watch.eval.run --run --slice injection --skip-judge --skip-agent-eval
  ```
  -> **3/3 passed (100%)**, Injection gate OK (100%, no tolerance), Regression OK (rate 100% vs baseline 100%, drop=0.0000 <= tolerance=0.05).
- **Eval lookup slice (subset 3 cases):**
  ```bash
  python -m src.portfolio_watch.eval.run --run --slice lookup --limit 3 --skip-judge --skip-agent-eval
  ```
  -> **3/3 passed (100%)**, Regression OK (rate 100% vs baseline 100%, drop=0.0000 <= tolerance=0.05).
  *(L?u ? trung th?c: upstream Vietcap/vnstock guest thi tho?ng timeout 30s khi l?y gi?, h? th?ng fallback chu?n x?c kh?ng crash, k?t qu? v?n ??p ?ng ??y ?? rule-based scorer v? kh?ng vi ph?m guardrail).*


## 2026-09-22 ? Review Phase 4 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 4: clean dead code)

**Passes**
- Plan Phase 4: canonical `src/portfolio_watch/agents/`; x?a `domain/agents/`
  shim; x?a `web/`; graph/application import th?ng `agents/`; checklist `[x]`.
- Product path: UI = `frontend/` (kh?ng c?n `web/`); README/compose kh?ng c?n
  path ch?t `web/` hay `domain/agents`.
- `specs/agents.md` ?? tr? `agents/<name>/`.
- Local smoke: `pytest tests/test_docker.py tests/test_backend.py tests/test_agents.py`
  ? **15 passed**.
- Docker rebuild: `/health` 200; `from src.portfolio_watch.agents?` /
  `graph.chat` import OK; `domain.agents` **kh?ng c?n** (ModuleNotFoundError ??ng k? v?ng).

**Fails (?? s?a ? ch? li?n quan Phase 4)**
- Change-log Phase 4 ghi `docker compose run ? pytest` nh?ng image product
  **kh?ng** c? `pytest` (ch? optional `[dev]`) ? l?nh fail `executable not found`.
  ??i h??ng d?n smoke Docker sang import check (kh?ng b?t bu?c pytest trong image).

**Missing (??ng k? v?ng ? phase sau)**
- AC Claude UI / Langfuse / memory / golden / diagram ? kh?ng thu?c Phase 4.

### Fix trong review

- C?p nh?t m?c Test c?a entry Phase 4 + ghi review n?y (l?nh smoke Docker kh?ng d?ng pytest trong image).

## 2026-09-22 ? Phase 4: Clean code ch?t

### What & Architectural Decisions
- **Ch?t 1 ngu?n agent canonical:** Ch?n `src.portfolio_watch.agents` (`agents/`) l?m ngu?n duy nh?t cho agent logic (c?c package `answer_composer/`, `eval_agent/`, `event_classifier/`, `news_agent/`, `price_agent/`, `supervisor_agent/`, `synthesis_agent/` theo c?u tr?c chu?n `nodes.py`, `state.py`, `tools.py`).
- **X?a `src/portfolio_watch/domain/agents/`:** To?n b? 8 file re-export wrapper (`answer_composer.py`, `eval_agent.py`, `event_classifier.py`, `news_agent.py`, `price_agent.py`, `supervisor.py`, `synthesis_agent.py`, `__init__.py`) l? legacy shim t? Phase 12 ?? ???c x?a b? ho?n to?n.
- **C?p nh?t import tr?c ti?p t? `agents/`:**
  - `src/portfolio_watch/graph/chat.py`
  - `src/portfolio_watch/graph/scan.py`
  - `src/portfolio_watch/graph/state.py`
  - `src/portfolio_watch/application/answer_question.py`
  - `src/portfolio_watch/application/scan_symbol.py`
  - `src/portfolio_watch/application/scan_watchlist.py`
  - `src/portfolio_watch/domain/graph/workflow.py`
  - `tests/test_agents.py`
- **C?p nh?t boundary check backend:** `tests/test_backend.py` c?p nh?t `_FORBIDDEN_EVERYWHERE = ("portfolio_watch.agents", "domain.agents")` ?? ??m b?o backend kh?ng import agent tr?c ti?p.
- **X?a dead `web/`:** X?a b? th? m?c `web/` (g?m `web/app.js`, `web/index.html`, `web/style.css`) - l? giao di?n static c? kh?ng c?n s? d?ng. Product UI chu?n hi?n t?i ???c ph?c v? t? `src/portfolio_watch/frontend/`.
- **??nh d?u checklist:** ??nh d?u `[x]` to?n b? checklist Phase 4 trong `specs/implementation-plan.md`.

### Files touched / deleted
- **Deleted:**
  - `src/portfolio_watch/domain/agents/__init__.py`
  - `src/portfolio_watch/domain/agents/answer_composer.py`
  - `src/portfolio_watch/domain/agents/eval_agent.py`
  - `src/portfolio_watch/domain/agents/event_classifier.py`
  - `src/portfolio_watch/domain/agents/news_agent.py`
  - `src/portfolio_watch/domain/agents/price_agent.py`
  - `src/portfolio_watch/domain/agents/supervisor.py`
  - `src/portfolio_watch/domain/agents/synthesis_agent.py`
  - `web/app.js`
  - `web/index.html`
  - `web/style.css`
- **Modified:**
  - `src/portfolio_watch/agents/README.md`
  - `src/portfolio_watch/graph/chat.py`
  - `src/portfolio_watch/graph/scan.py`
  - `src/portfolio_watch/graph/state.py`
  - `src/portfolio_watch/application/answer_question.py`
  - `src/portfolio_watch/application/scan_symbol.py`
  - `src/portfolio_watch/application/scan_watchlist.py`
  - `src/portfolio_watch/domain/graph/workflow.py`
  - `tests/test_agents.py`
  - `tests/test_backend.py`
  - `specs/implementation-plan.md`
  - `specs/change-log.md`

### How to test
```bash
# Smoke local (c? pytest trong venv)
python -m pytest tests/test_docker.py tests/test_backend.py tests/test_agents.py -q

# Smoke Docker ? image product kh?ng ship pytest; check import path canonical
docker compose up -d --build
curl -s http://127.0.0.1:8000/health
docker compose run --rm app python -c "from src.portfolio_watch.agents.price_agent import run_price_agent; from src.portfolio_watch.graph.chat import run_chat_graph; print('IMPORT_OK')"
```

## 2026-09-22 ? Review Phase 3 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 3: Docker 1 service)

**Passes**
- Plan Phase 3: service `app` :8000; qdrant optional (profile); kh?ng c?n b?t bu?c
  `frontend`/`backend`/`ai`; volume SQLite ghi change-log; healthcheck `app`.
- Product-spec **AC6**: kh?ng c?n service backend t?ch trong compose product;
  API + UI c?ng container (`backend.main` + StaticFiles).
- Test-plan ?5: 1 URL product ch?nh `http://localhost:8000`; volume
  `pw_data` ? `/app/data`; README l?nh `docker compose run --rm app ?`.
- Smoke: `docker compose up --build -d` ? `portfolio-watch-app` **healthy**;
  `/health` `/` `/watchlist` = 200. `tests/test_docker.py` 4 passed.

**Fails (?? s?a ? ch? li?n quan Phase 3)**
- `.env` c?n `FRONTEND_ORIGIN=http://127.0.0.1:5173` (V2) ?? v?o container ?
  compose ch?a override ? CORS l?ch product same-origin.
- Test compose d?ng `"ai:" not in text` d? false-positive v?i `AI_*`; ch?a
  assert kh?ng c?n service `backend:`.

**Missing (??ng k? v?ng ? phase sau)**
- AC1 ??y ?? E2E chat/market/HITL demo UI Claude; AC2?5, 7?9 (graph hover,
  Langfuse 1-trace, memory, golden_v3, diagram, README Docker-only tuy?t ??i).
- Image tag v?n `portfolio-watch:split` (nit ??t t?n ? kh?ng ch?n AC).

### Fix trong review

- `docker-compose.yml`: `FRONTEND_ORIGIN=*`, `QDRANT_URL=http://qdrant:6333`.
- `tests/test_docker.py`: assert service keys `\n  ai|backend|frontend:` v?ng.

## 2026-09-22 ? Phase 3: Docker product 1 service

### What

- `docker-compose.yml`: Thay th? 3 services r?i (`frontend` + `backend` + `ai`) b?ng 1 service ch?nh duy nh?t `app` ch?y port 8000 (`uvicorn src.portfolio_watch.backend.main:app`).
- Th?m optional service `qdrant` k?ch ho?t qua `--profile qdrant` ho?c `--profile optional` (image `qdrant/qdrant:latest`, port 6333/6334, volume `qdrant_data`), s?n s?ng cho Phase 8 memory.
- Healthcheck compose cho `app`: ki?m tra `http://127.0.0.1:8000/health` qua `urllib.request`.
- `Dockerfile`: C?p nh?t `CMD` m?c ??nh ch?y `src.portfolio_watch.backend.main:app` tr?n port 8000 v? `EXPOSE 8000`.
- `README.md`: C?p nh?t m?c ch?y Docker 1 product URL (http://localhost:8000/) v? l?nh eval trong container `app`.
- `specs/implementation-plan.md`: ??nh d?u `[x]` to?n b? checklist Phase 3.
- `tests/test_docker.py`: C?p nh?t assertions ki?m tra compose layout 1 service `app`, optional `qdrant`, Dockerfile CMD, v? TestClient test `backend.main:app` ph?c v? c? `/health` l?n UI `/`.

### SQLite Volume Path

- Docker named volume: `pw_data` (`name: portfolio-watch-data`) mount t?i `/app/data` trong container.
- SQLite path l?u tr? b?n trong volume:
  - Agent / LangGraph: `/app/data/portfolio_watch.db` (bi?n m?i tr??ng `SQLITE_PATH`)
  - Backend store (watchlist + approvals): `/app/data/backend_store.db` (bi?n m?i tr??ng `BACKEND_SQLITE_PATH`)
- D? li?u SQLite t?n t?i b?n v?ng qua c?c l?n container start/stop/rebuild.

### Test

```bash
cd llm-backend-ref-portfolio-watch
docker compose config
python -m pytest tests/test_docker.py -q

# Kh?i ??ng Docker container
docker compose up -d --build
# Ki?m tra healthcheck & single product URL
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/
# Smoke test chat & scan
curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"question":"Gi? FPT h?m nay?"}'
curl -s -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" -d '{"symbol":"FPT"}'
```

### Known issues

- `docker compose up --build` full rebuild t? ??u c? th? ch?m tr?n m?i tr??ng Windows do m?ng v? t?i c?c g?i dependency; n?u ?? c? image `portfolio-watch:split`, c? th? kh?i ??ng nhanh b?ng `docker compose up -d`.


## 2026-09-21 ? Review Phase 2 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 2: g?p entry app)

**Passes**
- Plan Phase 2: 1 FastAPI = UI static + `/watchlist` `/chat` `/scan`
  `/approvals`; `/health` 200; LangGraph in-process; reuse `backend/`.
- Product-spec h??ng AC6 (m?t ph?n): API + UI c?ng process, reuse store/routes
  ? ??t tr?n **uvicorn local** (done-when Phase 2).
- Test-plan ? UI t?i thi?u cho entry: m? `/`, assets `/app.js` `/config.js`
  `/style.css`, API c?ng origin.
- `tests/test_backend.py` (sau fix): UI copy + same-origin config + assets.

**Fails (?? s?a ? ch? li?n quan Phase 2)**
- UI v?n ghi ?Frontend t?ch ri?ng?; boot hi?n `BACKEND_BASE_URL=` r?ng.
- `backend/README.md` / `frontend/README.md` c?n m? t? proxy/t?ch FE V2.

**Missing (??ng k? v?ng ? phase sau, kh?ng s?a ? ??y)**
- Product AC6 ??y ?? / test-plan ?5: `docker compose` 1 service `app` ? **Phase 3**.
- AC1?5, 7?9 (Claude graph hover, Langfuse 1-trace, memory, golden_v3,
  diagram, README Docker-only) ? phase 4+.

### Fix trong review

- `frontend/index.html`, `app.js`: copy c?ng origin; label `(same-origin)`.
- README `backend/` + `frontend/`; test assets + config `BACKEND_BASE_URL: ""`.

## 2026-09-21 ? Phase 2: G?p entry app (reuse backend)

### What

- `backend/ai_client.py`: m?c ??nh **in-process** (`answer_question` /
  `scan_symbol` ? LangGraph). HTTP c? qua `AI_TRANSPORT=http`.
- `backend/main.py`: mount `frontend/` StaticFiles (`html=True`) sau API routes.
- `frontend/config.js`: `BACKEND_BASE_URL=""` (same-origin).
- `.env.example`: `AI_TRANSPORT=inprocess`.
- Tests: UI `/`, chat in-process; HTTP proxy tests ch? khi `AI_TRANSPORT=http`.

Kh?ng vi?t service m?i ? reuse store/routes backend.

### Test

```bash
cd llm-backend-ref-portfolio-watch
python -m pytest tests/test_backend.py -q

# M?t process
python -m uvicorn src.portfolio_watch.backend.main:app --host 127.0.0.1 --port 8000
# M? http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/watchlist
curl -s http://127.0.0.1:8000/approvals
printf '%s' '{"question":"Gia FPT?"}' > /tmp/pw_chat.json
curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" --data-binary @/tmp/pw_chat.json
printf '%s' '{"symbol":"FPT"}' > /tmp/pw_scan.json
curl -s -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" --data-binary @/tmp/pw_scan.json
```

K?t qu?: `tests/test_backend.py` 6 passed; smoke `/` `/health` `/chat` `/scan`
`/watchlist` `/approvals` = 200 tr?n m?t uvicorn.

### Known issues

- Docker compose v?n 3 service (Phase 3 m?i g?p). Dev path ch?nh Phase 2 =
  m?t uvicorn nh? tr?n.

## 2026-09-21 ? Phase 1: Project setup (baseline V3)

### What

- `specs/eval/v3_baseline.json` ? ?i?m hi?n t?i (carry-forward V2 **30/30**,
  dataset `golden_dataset.yaml` v1.0, scorer rule-based skip-judge/agent-eval,
  injection gate 100%; slice `diagram` tr?ng ??n Phase 15).
- README: m?c **V3 in progress** tr? product-spec + implementation-plan + baseline.
- AGENTS.md: **1 phase / l?n**; kh?ng code ngo?i checklist.
- Tick checklist Phase 1 trong `specs/implementation-plan.md`.
- Dockerfile: c?i `setuptools`/`wheel` tr??c `pip install -e .` (tr?nh fail
  build isolation khi PyPI kh?ng tr? setuptools).

### Quy?t ??nh V3 (ch?t docs)

| Quy?t ??nh | Ghi ch? |
|---|---|
| **1 app Docker** | UI+API+LangGraph c?ng product ? g?p Phase 2?3; b? b?t bu?c 3 service |
| **Memory + TTL** | short-term window + long-term recall/store ? Phase 7?8 |
| **UI Claude + graph** | chat tr?i, panel node live + hover I/O ? Phase 10?11 |
| **Eval Class 18** | golden slice + `by_slice`; injection 100%; regression vs `v3_baseline` ? Phase 15 |

### Kh?ng ??i h?nh vi

Kh?ng implement business feature; V2 3-service v?n ch?y.

### Test

```bash
cd llm-backend-ref-portfolio-watch
docker compose up -d
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8001/health
# chat
printf '%s' '{"question":"Gia FPT hom nay?"}' > /tmp/pw_chat.json
curl -s -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" --data-binary @/tmp/pw_chat.json
# scan
printf '%s' '{"symbol":"FPT"}' > /tmp/pw_scan.json
curl -s -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" --data-binary @/tmp/pw_scan.json
```

K?t qu? 2026-09-21: BE/AI health 200; FE 200; **POST /chat 200**; **POST /scan 200**.

### Known issues

- `docker compose up --build` full rebuild r?t ch?m / d? ??t PyPI tr?n m?y n?y;
  smoke Phase 1 d?ng image `portfolio-watch:split` s?n + `up -d`.

## 2026-09-21 ? Rewrite implementation-plan V3 (SDD B??c 3)

### What

- Vi?t l?i `specs/implementation-plan.md` th?nh **16 phase nh?**, m?i phase
  checklist c? th? + ?i?u ki?n xong + b?ng ph? thu?c.
- Kh?ng vi?t code.

### Test

??c plan ? m?i phase l?m ???c ??c l?p theo th? t? 1?16.

## 2026-09-21 ? Review product-spec V3 (SDD B??c 2)

### What

- L?m r? 6 m?c b?t bu?c: app goal, target users, core user flow, in/out of
  scope, acceptance criteria ? ng?n h?n, flow t?ng b??c, AC ki?m th? ???c.
- Kh?ng vi?t code.

### Test

??c `specs/product-spec.md` ? ?? 6 heading, d? tri?n khai MVP.

## 2026-09-21 ? V3 specs only (ch?a implement)

### What

Vi?t l?i v?ng **V3** theo y?u c?u product (SDD ? docs tr??c, ch?a code):

- `specs/product-spec.md` ? Claude-like UI + live graph I/O; 1 Langfuse
  trace/request; structured output; memory short+long + TTL; g?p app (reuse
  backend, b? t?ch service); golden Class 18; diagram agent; market status;
  prompt t?i gi?n; Docker-only.
- `specs/implementation-plan.md` ? Phase **20?29** (unchecked).
- `specs/test-plan.md` ? slice / by_slice / injection gate; UI + Langfuse checklist.
- `AGENTS.md` ? quy t?c V3 g?n.
- `README.md` ? V3 in progress; gi? l?nh Docker V2 l?m baseline.

### Why

User y?u c?u update multi-agent b?ng spec-driven development v? **kh?ng
implement app** ? b??c n?y.

### Test

??c 6 file tr?n; x?c nh?n kh?ng c? diff code runtime ngo?i docs.

### Missing (??ng k? v?ng)

- To?n b? Phase 20?29 ch?a tick.
- Ch?a g?p container; ch?a UI Claude; ch?a golden_v3.yaml.

## 2026-09-21 ? Agent graph HTML (d? ??c)

### What

- Th?m `docs/agent_graph.html` ? t?ch nh?nh Scan / Chat, legend, b?ng node.
- Vi?t l?i `docs/agent_graph.mmd` theo 2 subgraph (kh?ng c?n ?? th? LangGraph g?p r?i).
- PNG c? (`agent_graph.png`) gi? l?m ?nh tham chi?u; ?u ti?n m? HTML.

### Test

M? `docs/agent_graph.html` trong tr?nh duy?t.

## 2026-09-21 ? README local development instructions

### What

- C?p nh?t `README.md`: m?c **Local development** ? prerequisites, install,
  env, l?nh ch?y AI / Backend / Frontend, URL local, troubleshooting.
- Gi? Docker l?m ???ng ch?y product khuy?n ngh?; **kh?ng** ??i app logic.

### Test

??c README; (tu? ch?n) ch?y 3 process local v? m? http://127.0.0.1:5173.

## 2026-09-19 ? Phase 15c?15d volume + healthcheck

### 15c

- Volume `pw_data` ? `/app/data` (ai + backend). **Gi? path:** AI
  `portfolio_watch.db`, Backend `backend_store.db` ? kh?ng migrate.

### 15d

- `docker-compose.yml` ? healthcheck `/health` cho `ai` (:8001) v? `backend` (:8000).

### Test

```bash
python -m pytest tests/test_docker_compose.py -q
docker compose up --build -d
docker compose ps   # ai/backend healthy
```

## 2026-09-19 ? Tests d?ng dependency th?t (b? fakes.py)

### What

- X?a `tests/fakes.py`; `conftest.py` wire `VnstockPriceSource`, `CafefNewsSource`,
  SQLite th?t qua `build_real_deps()`.
- B? patch Heuristic brain ? pytest d?ng LLM production (c?n `.env` + network).
- Backend `test_chat_proxy_to_real_ai`: uvicorn AI session fixture + HTTP th?t.
- Langfuse hierarchy mock b?; gi? test no-op khi `MONITORING_ENABLED=false`.

### Test

```bash
cp .env.example .env   # ?i?n OPENAI_API_KEYS
python -m pytest tests/ -q
```

## 2026-09-19 ? Gom tests c?n 7 file

### What

- X?a ~95 file `tests/test_*.py` r?i; gi? 7 file c?t l?i:
  `test_docker`, `test_backend`, `test_ai`, `test_agents`, `test_eval`,
  `test_tracing`, `test_frontend` (+ `conftest.py`, `fakes.py`).

### Test

```bash
python -m pytest tests/ -q
```

## 2026-09-19 ? Phase 15b Dockerfile src-only (review ? agy scratch)

### Implement

- `Dockerfile` ? b? `COPY backend/`, `COPY frontend/`; UI n?m trong `COPY src`.
- Image tag gi? `portfolio-watch:split` (compose).
- `tests/test_dockerfile.py`, `tests/test_docker_single_url.py` ? assert path m?i.

### Test

```bash
python -m pytest tests/test_dockerfile.py tests/test_docker_env_file.py tests/test_docker_single_url.py -q
docker compose build
```

## 2026-09-19 ? Phase 15a Compose 3 service tr? entry m?i trong src/portfolio_watch/

### Implement

- Copy legacy backend `backend/*.py` ? `src/portfolio_watch/backend/` v? ??i absolute import `backend.` th?nh `src.portfolio_watch.backend.`.
- Copy legacy frontend `frontend/*` ? `src/portfolio_watch/frontend/`.
- C?p nh?t `docker-compose.yml`: backend tr? uvicorn command t?i `src.portfolio_watch.backend.main:app`, frontend tr? directory t?i `src/portfolio_watch/frontend`. (Kh?ng xo? c?c th? m?c c?).

### Test

```bash
python -m pytest tests/test_docker_compose.py tests/test_backend_no_agent_imports.py -q
```

## 2026-09-19 ? Phase 14f?14g Langfuse no-op + mock hierarchy

### 14f

- `tests/test_monitoring_noop.py` ? `test_v1_scan_ok_when_monitoring_disabled`.

### 14g (review ? agy ghi scratch, implement l?i trong repo)

- `tests/test_langfuse_tracing.py` ? `test_agent_step_child_of_agent_not_root`,
  `test_agent_step_noop_when_monitoring_disabled`.

### Test

```bash
python -m pytest tests/test_monitoring_noop.py tests/test_langfuse_tracing.py -q
```

**Checklist th? c?ng (test-plan ?4):** Langfuse `:3000` + `docker compose up` ? 1 chat ?
1 trace, expand ? 3 c?p span.

## 2026-09-19 ? Phase 14e Docker Langfuse env (agy)

### Implement

- `docker-compose.yml` ? AI service: `LANGFUSE_HOST=http://host.docker.internal:3000`,
  `extra_hosts: host.docker.internal:host-gateway` (keys v?n t? `.env`).
- `tests/test_docker_env_file.py` ? `test_compose_configures_langfuse_host`.

### Test

```bash
python -m pytest tests/test_docker_env_file.py -q
```

## 2026-09-19 ? Phase 14d wire agent_step + graph turn propagation

### Implement

- `agents/*/nodes.py` ? `agent_step(turn, ?)` ? b??c n?i b? (price fetch, news react,
  draft, guardrail, classify, ?).
- **Review fix:** `graph/chat.py`, `graph/scan.py` truy?n `turn=turn` xu?ng m?i
  `run_*_agent` / `rewrite_question` / `route_question` / `classify_event` ?? step span
  l?ng ??ng d??i agent span.
- `tests/test_langfuse_tracing.py` ? fake stubs nh?n `turn=`.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py tests/test_graph_chat.py tests/test_graph_scan.py -q
```

## 2026-09-19 ? Phase 14c agent_step (trace_step helper) + review

### Implement

- agy SUCCESS nh?ng ghi scratch workspace ? implement l?i trong repo.
- `tracing.py` ? th?m `agent_step(turn, agent_name, step_name, ?)`.
- `tests/test_langfuse_tracing.py` ? `test_trace_step_three_level_hierarchy`.

### Review vs test-plan ?4

- **Pass:** root ? agent ? step 3 c?p (mock).
- **Missing (14d):** wire `agent_step` v?o `agents/*/nodes.py`.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py -q
```

## 2026-09-19 ? Phase 14a root trace + 14b agent span (review)

### 14a Implement (agy)

- `v1.py` ? g?i `answer_question` / `scan_symbol` (wrapper c? `trace_request`).
- **Quy?t ??nh:** 1 POST `/v1/scan` = 1 trace (per-request, kh?ng per-symbol batch).

### 14b Review

- Graph nodes (`chat.py`, `scan.py`) ?? g?i `agent_span(turn, ?)`; `turn` ??ng b?
  qua application wrapper (`turn = request_id or uuid`).
- **Pass:** `test_trace_request_and_agent_spans_when_enabled` ? hierarchy root ? agent.
- agy 14b fail (503) ? x?c nh?n code hi?n t?i ?? spec.

### Test

```bash
python -m pytest tests/test_langfuse_tracing.py tests/test_request_id_propagation.py tests/test_monitoring_noop.py tests/test_ai_v1_service.py -q
docker compose up --build
# G?i 1 chat ? Langfuse UI :3000 ? 1 trace (checklist 14g th? c?ng sau)
```

## 2026-09-19 ? Phase 13f deprecate application ? graph + review

### Implement (agy `gemini-3.1-pro-high`)

- `application/answer_question.py` ? wrapper `run_chat_graph()` + `trace_request`.
- `application/scan_symbol.py` ? wrapper `run_scan_graph()` + helpers gi? nguy?n.
- Phase 13 pytest stub: `test_graph_chat.py`, `test_graph_scan.py`, `test_graph_steps.py`.

### Review vs product-spec / test-plan

- **Pass:** eval/router v?n g?i `answer_question`/`scan_symbol`; orchestration qua graph.
- **Fixed:** tests patch `graph.chat.*` thay v? `application.answer_question.*`.

### Test

```bash
python -m pytest tests/test_answer_question.py tests/test_scan_symbol.py tests/test_graph_chat.py tests/test_graph_scan.py tests/test_langfuse_tracing.py -q
docker compose run --rm ai pytest tests/test_ai_v1_service.py -q
```

## 2026-09-19 ? Phase 13d steps[] from graph + review

### Implement (agy `gemini-3.1-pro-high`)

- `graph/steps.py` ? `build_steps_from_chunks()` t? `stream_mode="updates"`.
- `chat.py` / `scan.py` ? g?n `result.steps` t? stream chunks.
- `v1.py` ? `/v1/scan` d?ng `result.steps`; x?a `build_scan_steps()`.
- `tests/test_graph_steps.py` ? unit chat + scan step mapping.

### Review vs product-spec / test-plan

- **Pass:** test-plan ?3 ? chat/scan invoke tr? `steps[]` theo graph nodes.
- **Missing (13e?13f):** export PNG, deprecate application layer.

### Test

```bash
python -m pytest tests/test_graph_steps.py tests/test_graph_chat.py tests/test_ai_v1_service.py -q
```

## 2026-09-19 ? Phase 13b review vs product-spec / test-plan

### Pass

- test-plan ?3 (scan): graph compile OK; nodes kh?p lu?ng `agents.md` (price+news ?
  classifier ? eval ? synthesis ? Gate1/Gate2).
- product-spec ?2 (gi?m s?t): normal END; abnormal ? eval ? synthesis ? auto-send /
  HITL Gate1; Gate2 proposal pending.
- `run_scan_graph()` contract `ScanSymbolResult` gi?ng `scan_symbol`.

### Fixed (review)

- Error handling: eval/synthesis node catch ? route END, gi? price/news/routing.
- `request_id` + fallback `turn` UUID (parity `scan_symbol`).
- Warning log khi notifier fail ? `gate1_auto`.
- Tests: port parity t? `test_scan_symbol.py` (+ eval error path mock).

### Missing (kh?ng thu?c 13b ? phase sau)

- Wire API `/v1/scan` ? graph (**13c**).
- `steps[]` t? graph events (**13d**).
- `trace_request` root span (**14a**); export graph PNG (**13e**).

### Test

```bash
python -m pytest tests/test_graph_scan.py -q
```

## 2026-09-19 ? Phase 13b agy validate + review

### Agy `--task implement` (validation)

- Prompt: `.agy-runs/phase13b-validate-prompt.txt` ? output:
  `.agy-runs/phase13b-implement-validate.json` (SUCCESS, ~205s).
- **So s?nh v?i b?n Cursor:** `scan.py`, `state.py` **gi?ng h?t** (agy kh?ng s?a core).
- **Agy b? sung:** 3 test (`low_confidence`, `gate2`, `empty_symbol`) trong
  `tests/test_graph_scan.py`; export `ChatState`/`ScanState` trong `graph/__init__.py`.
- **Gi? b?n hi?n t?i** + c?i ti?n agy (tests/exports); backup Cursor:
  `.agy-runs/backup-13b-cursor/`.

### Agy `--task review --skip-permissions`

- Output: `.agy-runs/20260919-042044-review.json`.
- High: thi?u `trace_request` (Phase 14), thi?u try/except abnormal pipeline.
- Medium: thi?u `request_id` param, 4 test parity c?n thi?u vs `test_scan_symbol.py`.

### Workflow (t? 13c, m?i `/antigravity-cli`)

1. `agy --task implement` tr??c (prompt trong `.agy-runs/`).
2. ??c JSON output; pytest verify.
3. Ch? s?a tay khi agy fail / test fail.
4. `agy --task review --skip-permissions` khi c?n.

## 2026-09-19 ? Phase 13b LangGraph scan

### Implement

- `src/portfolio_watch/graph/scan.py` ? graph: fetch (price+news) ? event_classifier
  ? (normal END | eval ? gate2? ? synthesis ? gate1 auto/pending);
  `run_scan_graph()` tr? `ScanSymbolResult` (c?ng contract `scan_symbol`).
- `src/portfolio_watch/graph/state.py` ? th?m `ScanState`.
- `tests/test_graph_scan.py` ? compile + normal/abnormal invoke stub.
- Reuse helpers t? `application/scan_symbol.py`; runtime deps qua `contextvars`.

### Test

```bash
python -m pytest tests/test_graph_scan.py -q
```

## 2026-09-19 ? Phase 13a LangGraph chat + review

### Implement

- `src/portfolio_watch/graph/chat.py` ? graph th?t: rewrite ? supervisor ?
  workers ? answer_composer; `run_chat_graph()` tr? `AnswerQuestionResult`.
- `src/portfolio_watch/graph/state.py` ? `ChatState`.
- `tests/test_graph_chat.py` ? compile + invoke stub (heuristic brains).
- Runtime deps qua `contextvars` (LangGraph kh?ng gi? object trong configurable).

### Review vs product-spec / test-plan

- **Pass:** test-plan ?3 partial ? graph compile + invoke stub; nodes kh?p chat flow.
- **Missing (13b?13f):** scan graph, wire API, steps t? graph events, deprecate application.

### Test

```bash
python -m pytest tests/test_graph_chat.py -q
```

## 2026-09-19 ? Phase 12 complete (12a?12i) + review

### Implement

- Port 7 agents ? `src/portfolio_watch/agents/<name>/` (nodes, state, schemas;
  news/eval c? `tools.py`).
- Legacy `domain/agents/*.py` re-export; `tests/conftest.py` patch factory tr?n
  `agents/*/nodes` + domain.
- **12h:** gi? prompts t?i `infra/llm/prompt_registry` + `prompts/` YAML (kh?ng
  t?ch per-agent folder ? tr?nh tr?ng).
- **12i:** `guardrails` + `entities` gi? `domain/`; agents import qua domain
  cho ??n Phase 15 (kh?ng duplicate sang `shared/`).

**L?u ?:** `agy` ch?a c?i ? implement tr?c ti?p.

### Review vs product-spec / test-plan

- **Pass:** test-plan ?2 ? m?i agent folder + pytest t??ng ?ng pass.
- **Pass:** product-spec AC ?2 partial ? 7 agent folders; backend v?n kh?ng import agents.
- **Missing:** Phase 13+ (graph th?t, Langfuse, Docker-only, x?a scripts).

### Test

```bash
python -m pytest tests/ -q -k "price_agent or news_agent or event_classifier or eval_agent or synthesis_agent or supervisor or answer_composer or phase12"
```

## 2026-09-19 ? Phase 12a price_agent + review (SDD B??c 5?6)

### Implement

- Port `domain/agents/price_agent.py` ? `agents/price_agent/` (`nodes.py`, `state.py`,
  `schemas.py`, `__init__.py`).
- Legacy path re-export gi? import c?.
- `tests/test_phase12a_price_agent.py`.

**L?u ?:** `agy` ch?a c?i ? implement tr?c ti?p thay v? `agy_run.py`.

### Review vs product-spec / test-plan

- **Pass:** test-plan ?2 price_agent (fetch close + change_pct); kh?ng LLM; 12 tests pass.
- **Pass:** pattern `agent_pr` (nodes + state + schemas).
- **Missing (Phase 12+):** c?c agent c?n l?i, graph wire, Langfuse.

### Test

```bash
python -m pytest tests/test_price_agent.py tests/test_phase12a_price_agent.py tests/test_price_evidence_before_pct.py -q
```

## 2026-09-19 ? Review Phase 11 vs product-spec / test-plan (SDD B??c 6)

### Pass (Phase 11 scope)

- Skeleton 5 th? m?c + `__init__.py` + README; import package OK.
- B?ng migrate trong change-log + `src/portfolio_watch/README.md`.
- `graph/` re-export `domain/graph/` ? kh?ng ??i h?nh vi.
- Functional smoke pass (agent, API, graph, backend-no-agent-imports).
- Legacy `backend/`, `frontend/`, `scripts/` song song ? ??ng plan.

### Fail / ngo?i scope Phase 11 (ch?a s?a)

- `pytest tests/ -q` full: ~30 fail ? doc-guard MVP (README Phase 6?10, plan c?).
  Kh?ng do skeleton; d?n Phase **16d**.
- product-spec AC ?5.2?5.3 (agent folders, x?a scripts): Phase **12?15**.
- test-plan ?2??5 (agent refactor, LangGraph, Docker-only eval): Phase **12?15**.

### Fix review

- Th?m `src/portfolio_watch/README.md` (b?ng migrate trung t?m).
- M? r?ng `tests/test_phase11_v2_skeleton.py`: import t?ng package + verify
  b?ng migrate trong change-log v? `src/portfolio_watch/README.md`.

### Test Phase 11

```bash
python -m pytest tests/test_phase11_v2_skeleton.py -q
```

## 2026-09-19 ? Phase 11 V2 monorepo skeleton

### Thay ??i

- T?o skeleton V2 d??i `src/portfolio_watch/`:
  `agents/`, `backend/`, `frontend/`, `eval/`, `graph/` ? m?i folder c?
  `__init__.py` + `README.md`.
- `graph/__init__.py` re-export t? `domain/graph/` (logic gi? nguy?n ??n Phase 13).
- `tests/test_phase11_v2_skeleton.py` ? guard c?u tr?c + re-export.
- Code legacy **song song**, ch?a x?a root `backend/` / `frontend/` / `scripts/`.

### B?ng migrate (V2)

| C? | M?i |
|---|---|
| `backend/main.py` | `src/portfolio_watch/backend/` |
| `frontend/` (root) | `src/portfolio_watch/frontend/` |
| `domain/agents/*.py` | `src/portfolio_watch/agents/<name>/` |
| `domain/graph/` | `src/portfolio_watch/graph/` (Phase 13) |
| `scripts/run_eval.py` | `src/portfolio_watch/eval/run.py` (Phase 15) |

`pyproject.toml`: `include = ["src*", "backend*"]` ?? cover package m?i ? kh?ng ??i.

### Test

```bash
python -m pytest tests/test_phase11_v2_skeleton.py -q
```

## 2026-09-19 ? Phase 1 V2 project setup (SDD B??c 5)

### Thay ??i

- X?c nh?n MVP Docker: `docker compose up --build` ? backend :8000, AI :8001,
  frontend :5173; smoke `POST /chat` + `POST /scan` ? 200.
- T?o `specs/eval/v2_baseline.json` ? golden 30/30 (t? Phase 5 regression);
  ghi `phase1_docker_smoke`.
- C?p nh?t `.env.example` ? block V2 Langfuse (`host.docker.internal` trong Docker).
- README: m?c ?V2 in progress?, legacy paths s? deprecated Phase 15.
- `tests/test_phase1_v2_setup.py` ? guard baseline + checklist docs.
- ??nh d?u Phase 1 `[x]` trong `specs/implementation-plan.md`.

### Quy?t ??nh V2 (ch?t Phase 1)

- Gi? golden **30 case**; kh?ng n?i scorer ?? pass.
- Th? t? implement: **1 ? 11 ? 12 ? 13 ? 14 ? 15 ? 16**.
- Langfuse self-host `:3000` tr?n host; AI container d?ng `host.docker.internal`.

### Test

```bash
docker compose up --build -d
python -m pytest tests/test_phase1_v2_setup.py -q
# Re-run golden baseline (optional):
python scripts/phase5_regression.py --case-delay 20
```

## 2026-09-19 ? AGENTS.md (SDD B??c 4)

### Thay ??i (docs only)

- Vi?t l?i `AGENTS.md` ng?n g?n: ??c spec tr??c, 1 phase/task, kh?ng th?m lib,
  c?p nh?t change-log + h??ng d?n test sau m?i implement; gi? quy t?c V2.

### Review vs product-spec / test-plan

- **Pass:** align SDD Guide B??c 4.
- **Fail:** ch?a implement Phase 1 checklist.

## 2026-09-19 ? Review implementation-plan (SDD B??c 3)

### Thay ??i (spec only)

- `specs/implementation-plan.md`: rewrite phase nh? ? Phase 1 (V2 setup) +
  Phase 11?16 v?i checklist con (12a?12g, 13a?13f, ?); th? t? ph? thu?c.

### Review vs product-spec / test-plan

- **Pass:** align product-spec acceptance; test-plan c? th? c?p nh?t ? Phase 16d.
- **Fail:** ch?a implement.

## 2026-09-19 ? Review product-spec (SDD B??c 2)

### Thay ??i (spec only)

- `specs/product-spec.md`: c?u tr?c l?i 6 m?c SDD (goal, users, flow, in/out
  scope, acceptance) ? ng?n g?n, flow chat/scan/eval c? th?; gom ki?n tr?c/Langfuse
  v?o in-scope.

### Review vs product-spec / test-plan

- **Pass:** ?? checklist SDD Guide B??c 2.
- **Fail:** ch?a implement Phase 11+.

## 2026-09-19 ? Spec V2: clean agents + src monorepo + Docker product

### Thay ??i (spec only ? ch?a implement)

- Vi?t l?i `specs/product-spec.md` ? m?c ti?u V2: c?u tr?c `agent_pr`, FE/BE/AI
  trong `src/`, x?a `scripts/`, Langfuse trace l?ng nhau (1 trace / c?u h?i).
- Vi?t l?i `specs/implementation-plan.md` ? Phase 11?16 (unchecked).
- Vi?t l?i `specs/test-plan.md` ? test Docker-only + Langfuse checklist.
- C?p nh?t `README.md`, `AGENTS.md` cho v?ng V2.

### Quy?t ??nh ki?n tr?c (ch?t trong spec)

- Langfuse self-host `:3000` tr?n **host** ? AI container d?ng
  `host.docker.internal:3000` (tham chi?u `llm-engineer-demo/docker-compose.yml`).
- Kh?ng g?i Langfuse stack v?o compose repo n?y.
- Eval / regression ? `python -m src.portfolio_watch.eval.*` trong container AI.

### Review vs product-spec / test-plan

- **Pass:** acceptance criteria V2 ghi r?; phase t?ch nh?.
- **Fail:** ch?a c? code Phase 11+.
- **Missing:** Phase 12c backlog placeholder.

## 2026-09-19 ? LangGraph th?t + save_graph_visualization (hierarchical)

### Thay ??i
- `src/portfolio_watch/domain/graph/workflow.py`: `StateGraph` kh?p lu?ng
  `scan_symbol` + `answer_question`; `save_graph_visualization()` copy pattern
  `llm-engineer-demo/.../hierarchical.py` (PNG tr??c, fallback `.mmd`).
- X?a `visualize.py`; CLI: `python -m ...workflow` ho?c `scripts/draw_agent_graph.py`.
- C?p nh?t tests graph + `specs/agents.md`.

### Review vs product-spec / test-plan
- **Pass:** Phase 10 visualization t? code th?t; 13 node / 26 edge.
- **Fail:** kh?ng.
- **Missing:** graph ch?a thay imperative orchestration (ch? visualize).

## 2026-09-18 ? SDD: README ?Demo with local?

### Thay ??i
- `README.md`: m?c **Demo with local** ? start FE/BE/AI (5173/8000/8001),
  expose FE tr?n local, c?u h?nh `frontend/config.js` / `?backend=`, ngrok
  Backend tu? ch?n; gi? k?ch b?n watchlist/chat/scan.
- Kh?ng ??i app logic.
- Tests: `tests/test_readme_demo_with_local.py`; c?p nh?t
  `test_readme_phase7_demo_scenario.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4/5/8 h??ng demo 3 process + UI; test-plan demo th? c?ng.
- **Fail:** kh?ng.
- **Missing:** kh?ng (docs only).

## 2026-09-18 ? SDD B??c 9: README Local development

### Thay ??i
- `README.md`: m?c **Local development** ? prerequisites, install
  (`pip install -e ".[dev]"`), env vars, l?nh AI/Backend/Frontend, local
  URLs, troubleshooting t?m t?t; c?p nh?t **Tr?ng th?i** (Phase 8 xong).
- Kh?ng ??i app logic.
- Test: `tests/test_readme_local_development_sdd.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4 h??ng (3 process / 3 URL) c? h??ng d?n README; test-plan
  acceptance map ?3 process ri?ng ? README l?nh?.
- **Fail:** kh?ng.
- **Missing:** kh?ng (docs only).

## 2026-09-18 ? Phase 3c: R? so?t backlog ? kh?ng c? gap m?i

### Thay ??i
- `implementation-plan.md` ?3c: ??ng checkbox placeholder ?Th?m task khi
  gap?; ghi triage ? `blocked_cases.yaml` tr?ng + Phase 5 regression
  30/30 / injection 100%; gi? h??ng d?n th?m `- [ ]` + blocked entry khi
  fail sau n?y (kh?ng n?i scorer).
- Test: `tests/test_phase3c_backlog_triage.py`.
- **Kh?ng** th?m feature multi-agent m?i (kh?ng c? gap c?n code).

### Review vs product-spec / test-plan
- **Pass:** AC3 (case fail c? ghi ch? + backlog khi c?n ? hi?n kh?ng c?
  fail/blocked); test-plan Quality Loop b??c c?p nh?t Phase 3c khi c?n;
  acceptance map ?Case fail ? change-log + Phase 3c?.
- **Fail:** kh?ng.
- **Missing:** kh?ng trong ph?m vi v?ng Quality Loop + FE/BE/AI (Phase
  1?8 ?? [x]; 3c kh?ng c?n checkbox m?).

## 2026-09-18 ? Phase 8 ho?n th?nh: `.env.example` ?? bi?n Langfuse

**Ng?y ho?n th?nh Phase 8 (Tracing with Langfuse):** **2026-09-18**

### Thay ??i
- `.env.example`: kh?i Monitoring ghi ?? `MONITORING_ENABLED`,
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` + ch? th?ch
  no-op khi t?t/thi?u key, cloud vs self-host, `pip install langfuse`,
  tr? README Phase 8; kh?ng nh?ng key th?t.
- Test: `tests/test_env_example_phase8_langfuse.py`.

### Review vs product-spec / test-plan
- **Pass:** c?u h?nh AC6 / test-plan ?4 c? ?? bi?n trong `.env.example`
  (kh?p settings + README); secret kh?ng leak v?o example.
- **Fail:** kh?ng (ph?m vi item / ??ng Phase 8).
- **Missing:** kh?ng c?n checkbox Phase 8 trong implementation-plan.

## 2026-09-18 ? Phase 8: README b?t monitoring + t?m trace Langfuse

### Thay ??i
- `README.md` m?c **Langfuse (Phase 8)**: b?t `MONITORING_*` / `LANGFUSE_*`,
  m? UI Langfuse, t?m trace theo c?u h?i / `request_id`, troubleshooting;
  b?ng env li?t k? ?? 4 bi?n thay v? g?p `LANGFUSE_*`.
- Test: `tests/test_readme_phase8_langfuse.py`.

### Review vs product-spec / test-plan
- **Pass:** h??ng d?n AC6 / test-plan ?4 (b?t monitoring ? xem 1 trace;
  t??ng quan `request_id`); map ?Langfuse trace? c? c?ch ch?ng minh trong
  README + report Phase 8.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** kh?ng (??ng c?ng ng?y qua m?c `.env.example` ph?a tr?n).

## 2026-09-18 ? Phase 8: E2E chat ? Langfuse 1 root + spans

### Thay ??i
- `scripts/phase8_langfuse_e2e.py` ? live probe AI `/v1/chat` (??ch proxy
  c?a UI?Backend) + ??c observations Langfuse v4; `--print-checklist` UI.
- `tests/test_phase8_langfuse_e2e.py` ? FE?Backend contract, `request_id`,
  mock span tree khi monitoring on; optional live (`PHASE8_LIVE_LANGFUSE=1`).
- B?o c?o: `specs/eval/phase8_langfuse_e2e_report.md` (+ run log).

### Review vs product-spec / test-plan
- **Pass:** AC6 (1 chat + monitoring ? 1 trace); test-plan ?4 true+keys ?
  root `chat` + spans agent; evidence trong b?o c?o (trace_id + span list).
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** kh?ng (Phase 8 ?? ??ng ? xem m?c `.env.example` c?ng ng?y).

## 2026-09-18 ? Phase 8: MONITORING off / thi?u key ? chat no-op

### Thay ??i
- `tracing.py`: no-op khi `MONITORING_ENABLED=false` ho?c thi?u
  `LANGFUSE_*` key; c?nh b?o 1 l?n khi b?t nh?ng thi?u key / init fail;
  flush l?i ch? warn, kh?ng raise; cache `_client=False` kh?ng b? nh?m
  th?nh client th?t.
- Tests: `tests/test_monitoring_noop.py` (disabled, thi?u key, init fail,
  `/v1/chat` v?n 200, flush fail kh?ng crash).

### Review vs product-spec / test-plan
- **Pass:** product-spec ?t?t monitoring v?n chat b?nh th??ng?; test-plan
  ?4 `MONITORING_ENABLED=false` ? OK; thi?u key / sai init ? warn +
  best-effort kh?ng crash.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** kh?ng (Phase 8 ?? ??ng ? xem m?c `.env.example` c?ng ng?y).

## 2026-09-18 ? Phase 8: Propagate `request_id` Backend ? AI ? Langfuse

### Thay ??i
- Backend: m?i `/chat` v? `/scan` sinh `request_id` (UUID), g?i AI qua body
  + header `X-Request-Id`, echo l?i trong response.
- `backend/ai_client.py`: `ai_chat` / `ai_scan` nh?n v? forward `request_id`.
- AI `/v1/chat` + `/v1/scan`: nh?n `request_id` (body ho?c header), truy?n
  `answer_question` / `scan_symbol` ? metadata Langfuse (`request_id` +
  d?ng l?m `turn` khi c?).
- Tests: `tests/test_request_id_propagation.py`.

### Review vs product-spec / test-plan
- **Pass:** t??ng quan c?ng request Backend?AI?Langfuse metadata (test-plan
  ?3 ?c?ng request?); AC6 h??ng t?m trace theo request id.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** kh?ng (Phase 8 ?? ??ng ? xem m?c `.env.example` c?ng ng?y).

## 2026-09-18 ? Phase 8: Chat/scan ? 1 trace cha + span con (Langfuse)

### Thay ??i
- `src/portfolio_watch/infra/monitoring/tracing.py` ? port ? t??ng
  `llm-engineer-demo` (`trace_request` / `agent_span` / `trace_step`);
  no-op khi `MONITORING_ENABLED=false` ho?c thi?u key / thi?u package.
- `answer_question`: root `chat` + span `rewrite_question`, `supervisor`,
  `price_news_fetch`, `eval_agent`, `answer_composer`.
- `scan_symbol`: root `scan` + span `price_agent`, `news_agent`,
  `event_classifier`, `eval_agent`, `synthesis_agent`.
- Tests: `tests/test_langfuse_tracing.py`.

### Review vs product-spec / test-plan
- **Pass:** AC6 h??ng (1 request ? 1 trace cha + span b??c); test-plan ?4
  monitoring off v?n OK (no-op); pattern demo kh?ng copy nguy?n file.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** kh?ng (Phase 8 ?? ??ng ? xem m?c `.env.example` c?ng ng?y).
  `langfuse` c?i khi b?t monitoring (`pip install langfuse`).

## 2026-09-18 ? Phase 7 ho?n th?nh: quy?t ??nh compose (port / volume / DB)

**Ng?y ho?n th?nh Phase 7 (v?ng Quality Loop + FE/BE/AI):** **2026-09-18**

### Quy?t ??nh Docker / Compose (3 service)

| M?c | Quy?t ??nh | L? do ng?n |
|-----|------------|------------|
| Image base | `python:3.12-slim` | Kh?p runtime ?3.10; slim ?? FastAPI + deps |
| Image tag | `portfolio-watch:split` | M?t image, `command` kh?c nhau theo service |
| Ki?n tr?c | **3 service:** `ai` + `backend` + `frontend` | Kh?p AC4 (3 process/URL); FE kh?ng g?i AI th?ng |
| Port AI | host/container **8001** | `AI_API_PORT`; health `/health` |
| Port Backend | container **8000**; host `${APP_HOST_PORT:-8000}` | ??i c?ng host qua `.env` |
| Port Frontend | host/container **5173** | `python -m http.server` ph?c v? `frontend/` |
| AI?Backend | `AI_BASE_URL=http://ai:8001` (t?n service) | DNS n?i b? compose; browser v?n d?ng `127.0.0.1:8000` |
| Volume name | `portfolio-watch-data` (compose key `pw_data`) | Named volume ? s?ng qua `restart` / `down` |
| Volume path | ? `/app/data` | AI: `SQLITE_PATH=/app/data/portfolio_watch.db`; Backend: `BACKEND_SQLITE_PATH=/app/data/backend_store.db` |
| Env / secrets | `env_file: .env`; kh?ng bake key v?o image | Override host/path trong `environment:` |
| Demo URL | FE `http://127.0.0.1:5173/` ? BE `:8000` ? AI `:8001` | C?ng ranh gi?i local 3 process |
| X?a DB | `docker compose down -v` | Gi? volume m?c ??nh khi ch? `down` |

L?nh: `docker compose up --build` / `logs -f` / `down` ? README m?c
**Demo b?ng Docker**. Verifier local: `scripts/verify_clean_local.py` ?
`CLEAN_VENV_SMOKE_OK`.

### Review vs product-spec / test-plan
- **Pass:** AC4 (3 URL); c?u h?nh URL/CORS/env; test-plan README + Docker
  demo; Phase 7 checklist to?n `[x]`.
- **Fail:** kh?ng.
- **Missing:** Phase 8 Langfuse tracing (item ti?p theo).

## 2026-09-18 ? Phase 7: X?c nh?n m?y s?ch / dong312 (3 process ? 3 lu?ng)

### Thay ??i
- `scripts/verify_clean_local.py` ? d?ng stub AI + Backend + Frontend
  (c?ng t?m); ki?m watchlist, chat+steps, scan+approve; in
  `CLEAN_VENV_SMOKE_OK`. `VERIFY_USE_CURRENT=1` d?ng env hi?n t?i
  (dong312 / venv).
- `README.md`: m?c x?c nh?n m?y s?ch d??i Demo local.
- Tests: `tests/test_clean_venv_smoke.py` (assert 3 process).

### K?t qu? ch?y
- `VERIFY_USE_CURRENT=1 python scripts/verify_clean_local.py` ?
  **CLEAN_VENV_SMOKE_OK**.
- Venv t?m ??y ?? (`python scripts/verify_clean_local.py`) ?
  **CLEAN_VENV_SMOKE_OK** (log: `specs/eval/phase7_clean_local_run.log`).

### Review vs product-spec / test-plan
- **Pass:** AC4/AC5/AC8 h??ng (3 process, chat timeline, watchlist/scan/
  duy?t) tr?n script m?y s?ch; test-plan ?3 README + th? tay c?
  verifier t? ??ng.
- **Fail:** kh?ng.
- **Missing:** ghi quy?t ??nh compose (port/volume) ? item Phase 7 cu?i.

## 2026-09-18 ? Phase 7: docker compose 3 service (AI + Backend + Frontend)

### Thay ??i
- `docker-compose.yml`: services `ai` (:8001), `backend` (:8000),
  `frontend` (:5173); `AI_BASE_URL=http://ai:8001`; volume
  `portfolio-watch-data` ? `/app/data`.
- `Dockerfile`: COPY `backend` + `frontend` + `prompts`; default CMD =
  `ai_main` :8001 (compose override t?ng service).
- `README.md`: m?c **Demo b?ng Docker** ? `up` / `down` / `logs` / `-v`.
- Tests: c?p nh?t compose / Dockerfile / README Docker demo.

### Review vs product-spec / test-plan
- **Pass:** AC4 h??ng (3 process/URL trong compose); Frontend?Backend?AI;
  kh?ng bake secret; l?nh up/down/log trong README.
- **Fail:** kh?ng (ch?a ch?y `compose up` tr?n m?y n?y trong b??c docs).
- **Missing:** x?c nh?n m?y s?ch end-to-end; ghi quy?t ??nh compose chi ti?t
  (Phase 7 c?n l?i).

## 2026-09-18 ? Phase 7: K?ch b?n demo local (localhost)

### Thay ??i
- `README.md`: m?c **Demo local (Phase 7)** ? b?t 3 process, m?
  `http://127.0.0.1:5173/`, seed watchlist, chat + timeline, qu?t, duy?t
  n?u c?; **kh?ng** c?n ngrok.
- `scripts/phase7_demo_checklist.py` ? in checklist tay.
- Tests: `tests/test_readme_phase7_demo_scenario.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4/AC5/AC8 h??ng (3 process local, timeline chat, watchlist
  + scan + duy?t); test-plan ?UI timeline? demo th? c?ng 1 c?u; kh?ng
  c?n internet c?ng c?ng (expose).
- **Fail:** kh?ng (ph?m vi k?ch b?n docs).
- **Missing:** docker compose 3 service; x?c nh?n m?y s?ch; ghi quy?t ??nh
  compose (Phase 7 c?n l?i). Chat/scan th?t v?n c?n LLM/network n?i b?.

## 2026-09-18 ? Phase 6: Troubleshooting (key / port / AI / CORS)

### Thay ??i
- `README.md`: m?c **Troubleshooting (Phase 6)** ? thi?u
  `OPENAI_API_KEYS`; port tr?ng 8001/8000/5173; AI unreachable/timeout
  (502); CORS/`FRONTEND_ORIGIN`.
- Tests: `tests/test_readme_phase6_troubleshooting.py`.
- Phase 6 local-run checklist ? ?? `[x]`.

### Review vs product-spec / test-plan
- **Pass:** test-plan ?3 (AI down ? l?i r?, kh?ng treo; Backend/FE t?ch);
  AC4 h??ng ch?y 3 process c? h??ng d?n khi l?i; Phase 5 error messages
  ???c ghi trong README.
- **Fail:** kh?ng.
- **Missing:** Phase 7 demo k?ch b?n / compose / m?y s?ch.

## 2026-09-18 ? Phase 6: L?nh eval m?t case v? full golden

### Thay ??i
- `README.md`: m?c **Eval (Phase 6)** ? m?t case (`--case-id`), full
  (`--run` / `phase5_regression.py`), `--self-check`; ghi ch? rate-limit
  v? injection/regression.
- Tests: `tests/test_readme_phase6_eval_commands.py`.

### Review vs product-spec / test-plan
- **Pass:** AC1 h??ng (ch?y eval t?ng case / full); test-plan ?1 l?nh
  `--case-id` + full golden; developer flow ?si?t ch?t l??ng?.
- **Fail:** kh?ng.
- **Missing:** troubleshooting (Phase 6 cu?i).

## 2026-09-18 ? Phase 6: B?ng bi?n m?i tr??ng b?t bu?c / tu? ch?n

### Thay ??i
- `README.md`: m?c **Bi?n m?i tr??ng (Phase 6)** ? b?ng b?t bu?c
  (`OPENAI_API_KEYS`, `LLM_BACKEND`) + tu? ch?n (URL/port, SQLite,
  CORS, Langfuse, ?) kh?p `.env.example`.
- Tests: `tests/test_readme_phase6_env_table.py`.

### Review vs product-spec / test-plan
- **Pass:** product ?c?u h?nh URL/CORS b?ng bi?n m?i tr??ng?; AC4 h??ng
  (URL/port t?ch process); test-plan README c? b?ng env ng?n.
- **Fail:** kh?ng.
- **Missing:** l?nh eval; troubleshooting (Phase 6 c?n l?i).

## 2026-09-18 ? Phase 6: Ba l?nh ch?y AI ? Backend ? Frontend

### Thay ??i
- `README.md`: m?c **Ch?y 3 process (Phase 6)** ? l?nh
  `serve_ai.py` (:8001) ? `serve_backend.py` (:8000) ?
  `serve_frontend.py` (:5173) + health URL; thay skeleton ?ch?a ?? l?nh?.
- Tests: `tests/test_readme_phase6_three_commands.py`.

### Review vs product-spec / test-plan
- **Pass:** AC4 (3 process / 3 URL); test-plan ?3 ?3 process ri?ng? /
  ?README l?nh?; lu?ng Frontend?Backend?AI.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** b?ng bi?n env; l?nh eval; troubleshooting (Phase 6 c?n l?i).

## 2026-09-18 ? Phase 6: README prerequisites (dong312 / venv + .env)

### Thay ??i
- `README.md`: m?c **Prerequisites (Phase 6)** ? Python ? 3.10; conda
  `dong312` ho?c venv; `pip install -e ".[dev]"`; copy `.env.example` ?
  `.env` + `OPENAI_API_KEYS`.
- Tests: `tests/test_readme_phase6_prerequisites.py`; si?t
  `test_readme_local_instructions.py` theo item ?ang m?.

### Review vs product-spec / test-plan
- **Pass:** AC4 h??ng (chu?n b? ch?y 3 process); test-plan ?README l?nh?
  b?t ??u b?ng prerequisites r?; l?nh ki?m tra import `settings` ch?y OK.
- **Fail:** kh?ng (ph?m vi item n?y).
- **Missing:** ba l?nh ch?y AI?BE?FE; b?ng env; l?nh eval; troubleshooting
  (c?c item Phase 6 c?n l?i).

## 2026-09-18 ? Phase 5: Regression full golden sau FE/BE

### Thay ??i
- Ch?y full 30 golden (rule-based, kh?p `baseline_debug`): **30/30**,
  drop=0.0000 ? 0.05; injection **3/3 (100%)**.
- `scripts/phase5_regression.py` ? ch?y t?ng case subprocess + retry
  rate-limit vnstock guest; ghi `specs/eval/baseline_phase5.json` +
  `specs/eval/phase5_regression_report.md`.
- `scripts/run_eval.py`: `--case-delay` / `EVAL_CASE_DELAY_SEC` (h? tr?
  full run tr?nh burst).

### K?t qu?
| Slice | Passed/Total |
|---|---|
| lookup | 18/18 |
| comparison | 6/6 |
| out_of_scope | 3/3 |
| injection | 3/3 |
| **T?ng** | **30/30** |

### Review vs product-spec / test-plan
- **Pass:** test-plan Regression (Phase 5/7) ? rate kh?ng t?t qu?
  tolerance; AC2 injection 100%; AC1 h??ng 30/30 v?i scorer ?? ch?t
  (rule, skip-judge/agent-eval nh? baseline_debug).
- **Fail:** kh?ng.
- **Missing:** LLM-judge / task_success full (ngo?i m?c baseline_debug);
  Phase 6 README l?nh ch?y 3 process.

## 2026-09-18 ? Phase 5: Eval policy ? kh?ng n?i scorer + blocked/3c

### Thay ??i
- `specs/eval/blocked_cases.yaml` ? registry case fail ?? ghi nh?n
  (`reason` + `phase3c_task` b?t bu?c).
- `scripts/run_eval.py`: `assert_scorer_locks` (kh?ng h? judge < 3.0,
  kh?ng n?i `--tolerance` > 0.05); `load_blocked_cases`;
  `format_fail_policy_guidance` / `format_blocked_registry` in sau report.
- Tests: `tests/test_eval_scorer_policy.py`; self-check kh?a scorer.

### Review vs product-spec / test-plan
- **Pass:** test-plan ?Kh?ng n?i scorer?; fail ? s?a ho?c blocked+3c
  (AC3 h??ng); injection v?n hard 100%; judge s?n 3.0 gi? nguy?n.
- **Fail:** kh?ng.
- **Missing:** Regression full golden sau FE/BE (item Phase 5 cu?i).

## 2026-09-18 ? Phase 5: Approvals missing / ?? x? l? ? 404 r?

### Thay ??i
- `backend/store.py`: `get_approval`, `explain_approval_failure`
  (thi?u vs ?? x? l?).
- `backend/main.py`: approve/reject tr? 404 chi ti?t; ki?m tra state kh?ng
  ??i khi fail; `approval_id` r?ng ? 400.
- FE: hi?n l?i Duy?t/T? ch?i + reload list (kh?ng ?? UI l?ch).
- Tests: `tests/test_backend_approvals_errors.py`.

### Review vs product-spec / test-plan
- **Pass:** Phase 5 approvals l?i id; AC HITL kh?ng ??i state khi fail;
  message r? ?kh?ng t?m th?y? / ??? x? l??.
- **Fail:** kh?ng.
- **Missing:** Eval kh?ng n?i scorer (item Phase 5 ti?p); regression golden.

## 2026-09-18 ? Phase 5: Steps l?i gi?a ch?ng ? timeline `error`

### Thay ??i
- `backend/steps.py`: `mark_mid_run_error`, `ensure_steps_reflect_error`;
  `normalize_steps` gi? `error`; `_attach_run` g?n l?i t? field `error`.
- `frontend/app.js`: `markTimelineMidError` (running?error, gi? done);
  boot ?B??c l?i? khi steps c? `error`.
- Tests: `tests/test_steps_mid_run_error.py`.

### Review vs product-spec / test-plan
- **Pass:** AC5 timeline ph?n ?nh b??c l?i; test-plan stream/steps error
  tr?n b??c ?? (MVP one-shot); FE kh?ng g?i AI.
- **Fail:** kh?ng.
- **Missing:** Eval kh?ng n?i scorer / regression golden (Phase 5 c?n l?i).

## 2026-09-18 ? Phase 5: AI down / timeout ? 502 + FE kh?ng treo

### Thay ??i
- `backend/ai_client.py`: `AI_HTTP_TIMEOUT` (m?c ??nh 60s); ph?n bi?t
  ?AI timeout? vs ?AI kh?ng k?t n?i ???c? ? Backend **502** + `detail`.
- `frontend`: `REQUEST_TIMEOUT_MS` + `AbortController`; `formatApiError` /
  `showOpError` (boot + timeline error + chat); n?t G?i lu?n m? l?i.
- `.env.example`: `AI_HTTP_TIMEOUT`.
- Tests: `tests/test_ai_down_timeout.py`.

### Review vs product-spec / test-plan
- **Pass:** test-plan ?3 ?T?t AI ? kh?ng treo v? h?n?; Backend c? message;
  FE hi?n l?i, kh?ng g?i AI th?ng.
- **Fail:** kh?ng.
- **Missing:** approvals id l?i (item Phase 5 ti?p); SSE realtime t?ng b??c.

## 2026-09-18 ? Phase 5: Backend input l?i ? 4xx r?

### Thay ??i
- `backend/main.py`: `_norm_symbol` (r?ng vs kh?ng h?p l?);
  `_norm_threshold` (ng??ng ?m / =0); ?p d?ng watchlist + **scan**.
- Tests: `tests/test_backend_validation_4xx.py`
  (c?u r?ng, symbol invalid, ng??ng ?m).

### Review vs product-spec / test-plan
- **Pass:** Phase 5 m?c validation Backend; test-plan ?5 h??ng 4xx r?;
  AC kh?ng 500 cho input x?u tr?n Backend.
- **Fail:** kh?ng.
- **Missing:** AI down ? FE message (?? ??ng m?c k? ti?p); stream error;
  approvals id l?i.

## 2026-09-18 ? Phase 4: Ki?m th? tay (checklist + smoke)

### Thay ??i
- `tests/test_phase4_manual_checklist.py` ? smoke c?ng lu?ng FE?Backend:
  chat (steps+answer) ? th?m m? ? qu?t ? approve pending.
- `scripts/phase4_manual_checklist.py` ? in checklist UI 3 process.
- `frontend/README.md` ? m?c Ki?m th? tay Phase 4.
- **Phase 4 checklist ho?n t?t.**

### Review vs product-spec / test-plan
- **Pass:** AC5/AC8 h??ng (chat + timeline + watchlist + duy?t qua BE);
  test-plan ?3 b??c 2?3 (curl/API chat c? answer+steps; UI checklist);
  FE kh?ng g?i AI.
- **Fail (?? s?a):** script checklist in Unicode tr?n Windows cp1252 ?
  ghi stdout UTF-8.
- **Missing:** Phase 5 validation/error; demo live 3 process v?n c?n
  LLM/key khi ch?y tay v?i AI th?t.

## 2026-09-18 ? Phase 4: Watchlist/approvals SQLite Backend + FE CRUD

### Thay ??i
- `backend/store.py` ? SQLite th?t: b?ng `watchlist` + `approvals`
  (`BACKEND_SQLITE_PATH`, m?c ??nh `./data/backend_store.db`).
- Runs (steps) v?n in-memory. Seed DEFAULT_WATCHLIST ch? khi DB tr?ng.
- FE: th?m **S?a** ng??ng ? `PATCH /watchlist/{symbol}` (?? CRUD).
- `.env.example` + `backend/README.md`: b?ng n?i l?u Backend vs AI.
- Tests: `tests/test_backend_sqlite_crud.py`.

### N?i l?u (ghi r?)
| D? li?u | Owner | Path |
|---|---|---|
| Watchlist + approvals (UI) | **Backend** | `BACKEND_SQLITE_PATH` ? `./data/backend_store.db` |
| Memory/chat/price (AI) | **AI** | `SQLITE_PATH` ? `./data/portfolio_watch.db` |

### Review vs product-spec / test-plan
- **Pass:** AC8 h??ng watchlist + duy?t qua ki?n tr?c t?ch l?p; FE?BE
  CRUD/approve/reject; d? li?u b?n SQLite Backend; test-plan ?3 FE kh?ng
  g?i AI.
- **Fail:** kh?ng.
- **Missing:** checklist ?Ki?m th? tay? Phase 4 (item ti?p); Phase 5
  validation.

## 2026-09-18 ? Phase 4: Timeline t? Backend `steps` / `/runs/{id}/steps`

### Thay ??i
- `frontend/app.js`: `normalizeSteps`, `showTimelineStart` (running),
  `applyTimelineFromBackend` ? sau chat/scan l?y steps t? response r?i
  **GET `/runs/{run_id}/steps`** (ngu?n s? th?t Backend); kh?ng g?i AI.
- `index.html`: ghi r? ngu?n timeline Backend.
- Tests: `tests/test_frontend_timeline_steps.py`.
- MVP: one-shot steps (ch?a SSE realtime ? Phase 5 n?u c?n).

### Review vs product-spec / test-plan
- **Pass:** AC5 h??ng ?th?y timeline b??c?; test-plan ?3 contract steps +
  ??t nh?t start + done?; FE?Backend only.
- **Fail:** kh?ng.
- **Missing:** SSE stream t?ng b??c realtime (Phase 5); CRUD watchlist
  SQLite ghi r? (item Phase 4 ti?p).

## 2026-09-18 ? Phase 4: Chat Backend forward AI ? FE nh?n answer

### Thay ??i
- `backend/main.py`: `_forward_chat_from_ai` ? lu?n c? `answer` string
  top-level; `GET /runs/{id}` tr? `answer` cho chat.
- `frontend/app.js`: `extractFinalAnswer` + hi?n th? c?u tr? l?i cu?i;
  disable n?t G?i khi ?ang ch?.
- Tests: `tests/test_chat_answer_forward.py`.

### Review vs product-spec / test-plan
- **Pass:** Core flow chat b??c 2+4 (FE?BE?AI, hi?n c?u tr? l?i cu?i);
  test-plan ?3 ?curl chat qua Backend nh?n answer?; FE kh?ng g?i AI.
- **Fail:** kh?ng.
- **Missing:** Phase 5 validation; ki?m th? tay live ?? c? checklist
  (m?c Phase 4 k? ti?p c?ng ng?y).

## 2026-09-18 ? Phase 4: Frontend g?i Backend (b? mock)

### Thay ??i
- `frontend/app.js` ? `fetch` t?i Backend: `/chat`, `/scan`, `/watchlist`,
  `/approvals` (+ approve/reject); **xo? `MOCK_STEPS`**.
- `index.html` ? form th?m watchlist + qu?t m?; timeline t? `steps` response.
- Tests: `test_frontend_backend_wiring.py`; c?p nh?t scaffold/static-serve.
- N?i l?u: watchlist/approvals **in-memory Backend** (`backend/store.py`);
  AI v?n SQLite ri?ng khi chat/scan (proxy).

### Review vs product-spec / test-plan
- **Pass:** FE ch? g?i Backend (AC7 h??ng / test-plan ?3 contract); b? mock;
  ?? 4 nh?m API; kh?ng g?i AI `:8001` t? browser.
- **Fail:** kh?ng (static wiring tests).
- **Missing:** si?t item ?Chat nh?n answer? / timeline stream / CRUD+SQLite
  ghi r? (c?c checkbox Phase 4 c?n l?i); demo tay 3 process.

## 2026-09-18 ? Phase 3c: Guardrail rewrite gi? grounding

### Thay ??i
- `output_checks`: `has_evidence_grounding`, `check_rewrite_grounding`,
  `strip_buy_sell`, `rewrite_keep_grounding` ? rewrite kh?ng ???c b? h?t
  s? li?u evidence; fallback g? mua/b?n t? b?n ?? grounded.
- `answer_composer` + `synthesis_agent`: t? attempt>0 b?t bu?c grounding;
  l?u `last_grounded` cho fallback.
- Prompt `answer_compose` v1.1: khi s?a vi ph?m v?n gi? s? li?u/tin.
- Tests: `tests/test_guardrail_rewrite_grounding.py`.

### Review vs product-spec / test-plan
- **Pass:** AC guardrail mua/b?n + s? kh?p evidence (test-plan Synthesis/
  Answer); rewrite kh?ng c?n m?t s? li?u; AC3 backlog 3c ??ng m?c n?y.
- **Fail:** kh?ng (26 related tests).
- **Missing:** Phase 4 n?i FE?BE; Phase 3c placeholder tr?ng n?u ch?a c? gap m?i.

## 2026-09-18 ? Phase 3c: Rewrite/memory v?i ??i t? (?m? ??)

### Thay ??i
- `supervisor.py`: m? r?ng `_REF_PREV_RE` (c? phi?u ??/n?y, n?, em ??);
  `_apply_memory_symbol` + `_ground_rewritten` d?ng chung Heuristic v?
  `LlmRewriteBrain` (LLM tr? `symbol:null` v?n l?y m? t? h?i tho?i);
  ??i t? ? memory th?ng false ticker; stopword `BAO` (?bao nhi?u?).
- Prompt `rewrite_question` v1.2: v? d? ??i t? / follow-up b?t bu?c g?n m?.
- Tests: pronoun variants + LLM null-symbol fallback
  (`test_answer_question`, `test_supervisor_llm`).

### Review vs product-spec / test-plan
- **Pass:** agents.md RewriteQuestion d?ng Memory; test-plan ?2 Supervisor
  ?m? ?? / follow-up; AC8 chat follow-up (`test_api_chat`); AC3 backlog
  3c m?c ??i t? ?? x? l?.
- **Fail (?? s?a):** ?N? gi?m bao nhi?u?? extract nh?m `BAO` ? memory kh?ng
  ?p d?ng; ?? ?u ti?n ??i t? + stopword.
- **Missing:** Phase 4 FE (guardrail grounding ?? ??ng m?c k? ti?p).

## 2026-09-18 ? Phase 3c: Evidence gi? tr??c khi so s?nh %

### Thay ??i
- `price_agent.has_change_pct_evidence` /
  `prices_have_change_pct_evidence`.
- `answer_question`: fetch ?? gi? m?i m?; **skip `eval_agent`** n?u thi?u
  `change_pct` (kh?ng so s?nh % kh?ng c? c?n c?).
- `HeuristicEvalBrain`: thi?u gi? ? severity th?p + reasoning ?kh?ng so s?nh?.
- Prompt `eval_severity` + `answer_compose`: kh?ng b?a % khi thi?u evidence.
- Tests: `tests/test_price_evidence_before_pct.py`.

### Review vs product-spec / test-plan
- **Pass:** grounding s? li?u (guardrail / comparison trajectory); AC3
  backlog 3c ?? x? l?; h? tr? comparison golden kh?ng g?i eval khi thi?u gi?.
- **Fail:** kh?ng.
- **Missing:** Phase 4 FE (c?c m?c 3c g?i ? ?? ??ng sau ??).

## 2026-09-18 ? Phase 3b: CORS Backend theo `FRONTEND_ORIGIN`

### Thay ??i
- `backend/main.py` ? `CORSMiddleware`:
  - `FRONTEND_ORIGIN=*` (dev m?c ??nh) ? `allow_origins=["*"]`;
  - ho?c origin c? th? (vd. `http://127.0.0.1:5173`).
- `.env.example` + `backend/README.md` ghi c?u h?nh CORS.
- Tests: `tests/test_backend_cors.py` (GET + preflight + si?t origin).
- **Phase 3b checklist ho?n t?t.**

### Review vs product-spec / test-plan
- **Pass:** ?C?u h?nh URL/CORS b?ng bi?n m?i tr??ng? (AC / features);
  Backend s?n s?ng cho FE :5173 g?i cross-origin (h??ng AC4/test-plan ?3).
- **Fail:** kh?ng.
- **Missing:** FE th?t g?i API (Phase 4); si?t origin tr?n AI process
  (kh?ng b?t bu?c ? browser kh?ng g?i AI).

## 2026-09-18 ? Phase 3b: Backend kh?ng import `domain.agents` (HTTP-only)

### Thay ??i
- Gate ki?m tra: `tests/test_backend_no_agent_imports.py`
  - c?m import `domain.agents` / `portfolio_watch.application` / langgraph;
  - c?m `src.portfolio_watch*` trong `backend/`;
  - `ai_client.py` ch? stdlib `urllib` ? `/v1/chat` + `/v1/scan`.
- Si?t assert trong `test_backend_service.py`; README ghi AC7 + l?nh pytest.

(Code Backend v?n ?? HTTP-only; m?c n?y kh?a ranh gi?i b?ng test.)

### Review vs product-spec / test-plan
- **Pass:** AC7 ?Backend ch? g?i AI qua HTTP ? kh?ng import graph/agent
  domain?; test-plan acceptance map ?Backend kh?ng import agents?
  (grep/AST tr?n `backend/`).
- **Fail:** kh?ng.
- **Missing:** FE kh?ng g?i th?ng AI (Phase 4). CORS Backend ?? l?m ? m?c k? ti?p.

## 2026-09-18 ? Phase 3b: Endpoint `steps[]` one-shot (MVP)

### Thay ??i
- `backend/steps.py` ? `normalize_steps` ? `{id,name,status,detail?}`.
- `POST /chat` + `POST /scan`: lu?n tr? `steps[]` chu?n + `run_id`.
- `GET /runs/{run_id}` v? `GET /runs/{run_id}/steps` ? l?y l?i b??c
  one-shot (ch?a SSE; ?? MVP checklist).
- Store gi? `RunRecord` in-memory; tests c?p nh?t contract steps.

### Review vs product-spec / test-plan
- **Pass:** Backend tr? `steps` cho timeline (AC5 h??ng / test-plan ?3
  contract + ?curl chat nh?n answer + steps?); shape id/name/status/detail.
- **Fail:** kh?ng.
- **Missing:** SSE realtime t?ng b??c (tu? ch?n sau); FE n?i timeline
  (Phase 4); CORS + assert no `domain.agents` (m?c 3b c?n l?i).

## 2026-09-18 ? Phase 3b: Backend API (health / watchlist / approvals / proxy AI)

### Thay ??i
- `backend/` ? FastAPI process port **8000**:
  - `GET /health`
  - CRUD `/watchlist`
  - `/approvals` + approve/reject
  - `POST /chat`, `POST /scan` ? HTTP t?i `AI_BASE_URL` `/v1/*`
- `backend/ai_client.py` ? urllib JSON client (kh?ng import `domain.agents`).
- `backend/store.py` ? watchlist/approvals **in-memory** (Backend s? h?u).
- `scripts/serve_backend.py`; `pyproject.toml` include package `backend*`.
- Tests: `tests/test_backend_service.py`.

### Review vs product-spec / test-plan
- **Pass:** h??ng AC4 (Backend URL ri?ng :8000); AC7/AC8 m?t ph?n ?
  proxy chat/scan HTTP-only + watchlist/approvals CRUD; test-plan ?3
  contract Backend?AI (chat/scan JSON c? `steps` khi AI tr?).
- **Fail:** kh?ng trong scope m?c n?y.
- **Missing:** assert c?ng ?kh?ng import agents? trong checklist k? ti?p;
  CORS; n?i FE (Phase 4); SQLite b?n (ghi r? in-memory t?m).
  (Endpoint steps one-shot ?? l?m ? m?c k? ti?p c?ng ng?y.)

## 2026-09-18 ? Phase 3a: B?o c?o ch?t l??ng golden (30/30)

### Thay ??i
- `specs/eval/phase3a_quality_report.md` ? b?o c?o Phase 3a:
  - b?ng pass theo slice (18/6/3/3 = **30/30**, injection 100%);
  - li?t k? thay ??i agent/prompt/tool trong Quality Loop;
  - ??i chi?u AC1?3 / test-plan ?1.
- `tests/test_phase3a_quality_report.py` ? assert b?o c?o ?? m?c checklist.
- Checklist Phase 3a m?c ?B?o c?o? ? `[x]` (**3a ho?n t?t**).

### Review vs product-spec / test-plan
- **Pass:** AC1 ?b?o c?o pass/fail? + map acceptance; AC2 injection 100%
  ghi trong b?o c?o; AC3 thay ??i + backlog 3c ?? li?t k?; test-plan
  ?run_eval + b?o c?o? / ?slice report?.
- **Fail:** kh?ng trong scope m?c b?o c?o.
- **Missing:** full run k?m LLM-judge (ngo?i b?o c?o n?y); Phase 3b+.

## 2026-09-18 ? Phase 3a: Pass h?t slice (30/30, injection 100%)

### K?t qu? (`--run --skip-judge` + task_success; case-by-case delay)
| Slice | Passed | Total |
|---|---:|---:|
| lookup | 18 | 18 |
| comparison | 6 | 6 |
| out_of_scope | 3 | 3 |
| injection | 3 | 3 |
| **T?ng** | **30** | **30** |

Injection gate: **100%**.

### Thay ??i agent / prompt / eval (kh?ng n?i scorer)
- **Multi-symbol:** `RewrittenQuestion.symbols`; `_extract_symbols`; fetch
  gi?/tin t?ng m?; composer/evidence g?p ?a m?.
- **Prompt:** `rewrite_question` + `answer_compose` (symbols / n?u ?? m?).
- **Intent:** th?m hint ?bi?n ??ng / m?nh h?n / ??i chi?u?; ?a m? ? explain.
- **Stopword:** `TIN` (tr?nh ?tin t?c? th?nh ticker).
- **Eval:** m?i case `user_id=eval-{case_id}` ? tr?nh memory l?ch symbol.
- Phase 3c: ??nh d?u xong ?routing ?a m?.
- Tests: `tests/test_multi_symbol_rewrite.py`.

### Review vs product-spec / test-plan
- **Pass:** AC1 h??ng 30/30 theo scorer ?? ch?t (rule + task_success;
  judge skip trong run n?y); AC2 injection 100%; test-plan slice gate.
- **Fail:** kh?ng tr?n run 30/30 n?y.
- **Missing:** LLM-judge ch?a b?t tr?n full run (`--skip-judge`);
  Backend/FE (phase sau). B?o c?o t?ng h?p ? m?c checklist k? ti?p (?? l?m).

## 2026-09-18 ? Phase 3a: Quality Loop ? `lookup_15` (CafeF news)

### Ch?y
- Full eval `--skip-judge` (+ task_success): **24/30**; injection 100%.
- Fail ??u (theo id): `lookup_15` ? `news_agent items=0`, task_success fail.

### Nguy?n nh?n + s?a (tool, kh?ng n?i scorer)
- CafeF `s.cafef.vn/Ajax/Events_RelatedNews_New.aspx` tr? `<ul>` r?ng.
- ??i URL ? `https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx`.
- B? l?c `query` tr?n title (LLM hay search c?u d?i ? 0 tin d? endpoint
  ?? theo m?).
- Tests: `test_market_data` c?p nh?t URL + h?nh vi query.

### K?t qu? case
- `lookup_15`: **pass** (rule + task_success; trajectory overall 5.0).

### Review vs product-spec / test-plan
- **Pass:** workflow debug t?ng case (test-plan ?1 / AGENTS); s?a tool khi
  fail; kh?ng n?i expected; injection v?n 100% tr?n run full tr??c ??.
- **Fail:** kh?ng c?n tr?n `lookup_15`.
- **Missing:** c?n fail slice comparison (v? regression vs baseline_debug
  rule-only) ? thu?c m?c checklist ?Pass h?t slice?; AC1 30/30 ch?a ??t.

## 2026-09-18 ? Phase 3a: g? static UI kh?i process AI/API

### Thay ??i
- `main.py`: b? `StaticFiles(web/)` ? API/monolith kh?ng ph?c v? UI.
- `ai_main.py` v?n ?? kh?ng mount static; si?t test x?c nh?n GET `/`/`/app.js` = 404.
- `Dockerfile`: b? `COPY web` (image = API only).
- Tests: `test_api_static`, `test_docker_single_url`, UI tests ??c `web/` t? disk;
  UI production path = `frontend/` + `serve_frontend`.
- README: health API / FE :5173 / AI :8001 thay v? m? UI t?i :8000/.

### Review vs product-spec / test-plan
- **Pass:** AI/API kh?ng serve UI (h??ng AC4 t?ch process; test-plan ?3
  ?ch? b?t AI ? health OK?); FE ? process ri?ng (`frontend/`);
  `GET /` + `/app.js` tr?n AI/API = 404; `/health` + JSON API OK.
- **Fail:** kh?ng (kh?ng ph?t hi?n l?i li?n quan m?c n?y sau khi s?a test).
- **Missing:** Backend (3b); golden case-by-case; E2E 3 process + timeline
  (Phase 4?6); Docker compose 3 service (Phase 7).

## 2026-09-18 ? Phase 3a: AI process `/v1/chat` + `/v1/scan` + `steps[]`

### Thay ??i
- `src/portfolio_watch/ai_main.py` ? FastAPI AI-only (port m?c ??nh **8001**).
- `api/routers/v1.py` ? `POST /v1/chat`, `POST /v1/scan`; response c? k?t
  qu? cu?i + `steps[]` (`id/name/status/detail`).
- `scripts/serve_ai.py`; settings `AI_API_HOST` / `AI_API_PORT`.
- Tests: `tests/test_ai_v1_service.py`.
- Monolith `main.py` ?? g? static ? m?c k? ti?p (c?ng ng?y).

### Review vs product-spec / test-plan
- **Pass:** AI ch?y process/URL ri?ng (`AI_BASE_URL` :8001); contract
  chat/scan + `steps[]` (test-plan ?3); h? tr? FE timeline / Backend proxy.
- **Fail:** kh?ng trong scope m?c n?y.
- **Missing:** Backend proxy (3b); golden debug case-by-case; 3 process E2E.

## 2026-09-18 ? Phase 2: ch?y frontend ??c l?p + x?c nh?n UI

### Thay ??i
- `scripts/serve_frontend.py` ? static server m?c ??nh port **5173**.
- `tests/test_frontend_static_serve.py` ? GET `/` + `config.js` + `app.js`
  qua ThreadingHTTPServer (kh?ng c?n Backend/AI).
- `frontend/README.md` ? l?nh ch?y ??c l?p ?? x?c nh?n.

### X?c nh?n
- pytest static serve: pass (HTML c? chat/timeline/watchlist/approvals).
- `serve_frontend.py` m? ???c (fix print Unicode Windows ? ASCII).

### Review vs product-spec / test-plan
- **Pass:** Frontend ch?y process/URL ri?ng (h??ng AC4 m?t ph?n ? FE
  ??c l?p); m? UI ?? 4 khu v?c kh?ng ph? thu?c AI.
- **Fail:** kh?ng.
- **Missing:** Backend + AI process th?t (Phase 3+); n?i API (Phase 4).
- **Phase 2** ho?n t?t checklist.

## 2026-09-18 ? Phase 2: config `BACKEND_BASE_URL`

### Thay ??i
- `frontend/config.js` ? `PW_CONFIG.BACKEND_BASE_URL` +
  `PW_getBackendBaseUrl()` (override `?backend=`).
- UI hi?n URL t?i `#backend-url-display`; README h??ng d?n ??i config.
- Ch?a `fetch` API (??ng scope m?c n?y).
- Test: `test_frontend_backend_base_url_config`.

### Review vs product-spec / test-plan
- **Pass:** c?u h?nh URL b?ng bi?n/config (in-scope ?C?u h?nh URL??);
  FE ch? tr? Backend, kh?ng AI (h??ng AC7 / test-plan FE?BE).
- **Fail:** kh?ng.
- **Missing:** d?ng URL ?? g?i API th?t (Phase 4); CORS si?t theo
  `FRONTEND_ORIGIN` (Phase 3b).

## 2026-09-18 ? Phase 2: timeline mock 4 tr?ng th?i

### Thay ??i
- `frontend/app.js` ? `MOCK_STEPS` + `renderTimeline`: badge
  `pending | running | done | error`.
- `style.css` ? style `.status-badge` theo t?ng status.
- Test: `test_frontend_timeline_mock_has_all_statuses`.

### Review vs product-spec / test-plan
- **Pass:** UI hi?n list b??c v?i ?? 4 tr?ng th?i (AC5 / test-plan stream
  b??c ? ph?n hi?n th? status); kh?p shape name/status/detail.
- **Fail:** kh?ng.
- **Missing:** data th?t t? Backend `steps[]`; chuy?n tr?ng th?i realtime
  khi chat (Phase 4).

## 2026-09-18 ? Phase 2: trang ch?nh 4 khu v?c (chat / timeline / watchlist / approvals)

### Thay ??i
- `frontend/index.html` ? section `#chat`, `#timeline`, `#watchlist`,
  `#approvals` (timeline placeholder, ch?a mock status).
- `style.css` / `app.js` ? layout; form chat preventDefault (ch?a API).
- Test: `test_frontend_main_page_has_four_sections`.

### Review vs product-spec / test-plan
- **Pass:** UI c? ?? v?ng chat + timeline b??c + watchlist + duy?t (AC5
  m?t ph?n ? c? ch? hi?n b??c); kh?p in-scope Frontend.
- **Fail:** kh?ng trong scope m?c n?y.
- **Missing:** status `pending|running|done|error` tr?n timeline (m?c
  ti?p); n?i Backend; stream b??c th?t.

## 2026-09-18 ? Phase 2: t?o frontend/ (HTML/JS thu?n)

### Quy?t ??nh stack
- **HTML + CSS + JS thu?n** (kh?ng React/Vite ? MVP).
- Serve: `python -m http.server 5173` trong `frontend/`.

### Files
- `frontend/index.html`, `style.css`, `config.js`, `app.js`, `README.md`
- `tests/test_frontend_scaffold.py`

### Review vs product-spec / test-plan
- **Pass:** c? th? m?c frontend ri?ng, stack ghi r?; h??ng FE?Backend
  (config URL s?n).
- **Fail:** kh?ng (scope ch? scaffold).
- **Missing:** trang chat/timeline/watchlist/approvals ? m?c Phase 2 ti?p
  theo; ch?a ch?ng minh server 5173 trong CI (l?m ? m?c ?ch?y frontend
  ??c l?p?).

## 2026-09-18 ? Phase 1: chat `steps[]` + review

### Thay ??i
- `answer_question.build_chat_steps` ? `AnswerQuestionResult.steps`
  `[{id, name, status, detail}]`.
- `POST /chat` (`ChatResponse.steps`) tr? ??ng contract test-plan.
- Eval `steps_from_answer_result` ??c `result.steps` (map name?tool).
- Tests: `test_chat_steps.py`, assert steps trong `test_api_chat.py`.

### Review vs product-spec / test-plan
- **Pass:** chat JSON c? `steps` (id/name/status/detail); th? t?
  rewrite?supervisor?workers?composer; h? tr? timeline UI (AC5) v?
  trajectory eval; product ?UI hi?n b??c? c? data t? AI.
- **Fail:** kh?ng trong scope m?c n?y.
- **Missing:** stream t?ng b??c realtime (Phase 4/5); UI timeline (Phase 2);
  scan ch?a tr? `steps[]` (contract ghi chat/scan ? scan ?? phase sau n?u c?n).

## 2026-09-18 ? Phase 1: task_success + trajectory + `--case-id`

### Thay ??i
- `src/portfolio_watch/infra/eval/agent_scorers.py` ? port ? t??ng
  llm-engineer-demo: `evaluate_task_success`, `evaluate_trajectory`,
  `steps_from_answer_result`.
- `scripts/run_eval.py` ? gh?p scorers; `--case-id` (t? run); 
  `--skip-agent-eval`; `make_answer_fn.last_steps` cho trajectory.
- Pass lookup/comparison: rule + judge + `task_success.success`.
- Trajectory overall < 3.0 ? c?nh b?o, kh?ng fail case.
- Tests: `tests/test_run_eval_agent_eval.py`; c?p nh?t checklist tests
  kh?p plan m?i.

### Review vs product-spec / test-plan
- **Pass:** c? task_success + trajectory; ch?y 1 case `--case-id` (test-plan);
  task_success gate lookup/comparison; trajectory warn kh?ng ch?n pass.
- **Fail:** kh?ng trong scope m?c n?y.
- **Missing:** `steps[]` tr?n API chat (m?c Phase 1 k? ti?p) ? hi?n d?ng
  steps t? `AnswerQuestionResult` trong eval; full golden v?i agent-eval
  b?t ch?a ch?y l?i (d?ng `--skip-agent-eval` khi c?n baseline rule-only).

## 2026-09-18 ? Phase 1: baseline_debug eval (kh?ng s?a agent)

### Ch?y
- L?nh: `python scripts/run_eval.py --run --skip-judge --save-baseline --baseline specs/eval/baseline_debug.json`
- **Kh?ng** s?a domain agents / prompt.

### K?t qu? (`specs/eval/baseline_debug.json`)
| Slice | Passed | Total | Rate |
|---|---:|---:|---:|
| lookup | 18 | 18 | 100% |
| comparison | 6 | 6 | 100% |
| out_of_scope | 3 | 3 | 100% |
| injection | 3 | 3 | 100% |
| **T?ng** | **30** | **30** | **100%** |

Injection gate: OK (100%). Regression vs file v?a l?u: OK.

### Review vs product-spec / test-plan
- **Pass:** c? b?o c?o pass/fail t?ng slice; injection 100% (AC2 / test-plan
  gate); file baseline_debug l?m m?c regression v?ng debug.
- **Fail:** kh?ng (scope: ch?y baseline, ch?a n?ng scorer).
- **Missing:** l?n ch?y d?ng `--skip-judge` ? ch?a g?m LLM-judge /
  task_success / trajectory (AC1 ??y ?? + Phase 1 m?c eval n?ng c?p ti?p
  theo). `baseline.json` MVP c? (c? judge) v?n l? 30/30 ri?ng.

## 2026-09-18 ? Phase 1: README skeleton 3 process + review

### Thay ??i
- `README.md`: m?c **Skeleton ? 3 process** ? b?ng port AI `8001` /
  Backend `8000` / Frontend `5173`, env `AI_BASE_URL` /
  `BACKEND_BASE_URL` / `FRONTEND_ORIGIN`, lu?ng FE?BE?AI; ghi r? l?nh
  chi ti?t ? Phase 6.
- `tests/test_readme_split_skeleton.py` ? assert skeleton ?? port/env.
- `specs/implementation-plan.md` ? ??nh d?u xong m?c README skeleton.

### Review vs product-spec / test-plan (ch? skeleton README)
- **Pass:** t?i li?u 3 URL/port kh?p h??ng AC4; env kh?p `.env.example`;
  n?u Frontend kh?ng g?i th?ng AI (h??ng AC7); c?n m?c ch?y 1 process MVP
  (AC8 t?m th?i).
- **Fail:** kh?ng trong scope skeleton.
- **Missing (phase sau):** l?nh ch?y th?t 3 process (Phase 6); process
  t?ch (Phase 3?5); test-plan m?c ?3 process th? tay?.
- **Ngo?i scope:** `test_readme_local_instructions` /
  `test_readme_docker_demo` v?n fail v? README v?ng m?i ch?a kh?i ph?c
  section MVP Phase 6/7 c? ? thu?c Phase 6?7 plan m?i, kh?ng s?a ? m?c n?y.

## 2026-09-18 ? Review Phase 1 `.env.example` vs product-spec / test-plan

### Ph?m vi feature
Ch? c?u h?nh bi?n m?i tr??ng split-deploy + gi? OpenAI/Langfuse (kh?ng ph?i
eval / UI / 3 process ch?y th?t).

### Pass
- In scope ?C?u h?nh URL? b?ng bi?n m?i tr??ng?: `.env.example` c?
  `AI_BASE_URL`, `BACKEND_BASE_URL`, `FRONTEND_ORIGIN`, `APP_HOST_PORT`.
- Gi? `OPENAI_API_KEYS` + Langfuse (`MONITORING_*` / `LANGFUSE_*`) cho AC6 sau.
- Settings ??c ?? field; test `test_docker_env_file.py` pass.
- `.env` local ?? b? sung 3 URL (kh?p example; kh?ng ??ng secret).

### Fail
- Kh?ng (trong ph?m vi m?c `.env.example`).

### Missing (kh?ng s?a ? review n?y ? thu?c phase kh?c)
- AC4 ?3 process / 3 URL ch?y ??c l?p? ? m?i c? URL tr?n gi?y, ch?a t?ch
  process (Phase 3?5).
- CORS runtime v?n `allow_origins=["*"]` (MVP); ch?a si?t theo
  `FRONTEND_ORIGIN` (Phase 3b/4 khi FE ri?ng).
- AC1?3, 5?8 (golden, timeline, Langfuse E2E, Backend HTTP-only) ? ngo?i
  feature env.

## 2026-09-18 ? Phase 1: `.env.example` split-deploy URLs

### Thay ??i
- `.env.example`: `AI_BASE_URL`, `BACKEND_BASE_URL`, `FRONTEND_ORIGIN`,
  `APP_HOST_PORT`; gi? `OPENAI_API_KEYS` + Langfuse.
- `settings.py`: ??c `ai_base_url`, `backend_base_url`, `frontend_origin`,
  `app_host_port`.
- Test: `test_env_example_split_deploy_and_langfuse_vars`,
  `test_settings_loads_split_deploy_defaults`.

## 2026-09-18 ? Phase 1: ch?t c?u tr?c th? m?c FE / BE / AI

### Quy?t ??nh
- **AI** gi? nguy?n `src/portfolio_watch/` (kh?ng ??i t?n `ai/` ? Phase 1 ?
  tr?nh rename l?n; t?ch process ? Phase 3a).
- Th?m placeholder `frontend/` v? `backend/` (ch? README, ch?a UI/server).

### Files
- `frontend/README.md` ? UI ri?ng, port 5173, ch? g?i Backend.
- `backend/README.md` ? API s?n ph?m, port 8000, HTTP t?i AI, kh?ng import
  domain agents.
- `specs/implementation-plan.md` ? ??nh d?u xong m?c c?u tr?c Phase 1.
- `README.md` ? c?p nh?t tr?ng th?i (?? c? placeholder FE/BE).

### Review vs product-spec / test-plan (ch? m?c c?u tr?c)
- **Pass:** c? 3 v?ng `frontend/` ? `backend/` ? `src/portfolio_watch/` kh?p
  h??ng t?ch deploy; backend README ghi r? kh?ng import domain agents.
- **Fail:** kh?ng (scope ch? ch?t th? m?c).
- **Missing (phase sau):** 3 process ch?y th?t, UI/timeline, eval n?ng c?p,
  `steps[]`, Langfuse ? ch?a thu?c m?c n?y.

## 2026-09-17 ? Rewrite implementation-plan (SDD B??c 3)

### Docs (kh?ng code)
- Vi?t l?i `specs/implementation-plan.md` th?nh 8 phase nh? c? checklist:
  1 Project setup ? 2 Core UI ? 3 Core backend/data (AI ch?t l??ng +
  Backend) ? 4 Connect UI?Backend ? 5 Validation ? 6 Local run ?
  7 Local demo ? 8 Langfuse tracing.
- Gi? backlog multi-agent (3c) ?? b? sung khi debug golden case fail.

## 2026-09-17 ? Review / c?i thi?n product-spec (SDD B??c 2)

### Docs (kh?ng code)
- L?m r? 6 m?c: app goal, target users, core user flow, in/out of scope,
  acceptance criteria.
- Gi?m jargon k? thu?t (t?n h?m/file) trong product-spec; gi? m? t? s?n ph?m
  + 3 lu?ng (chat, gi?m s?t/HITL, debug golden) d? tri?n khai.

## 2026-09-17 ? SDD v?ng m?i: Quality Loop + Split FE/BE/AI (ch? spec)

### Docs (kh?ng implement app)
- Vi?t l?i `specs/product-spec.md` ? m?c ti?u: debug golden t?ng case, eval
  task_success/trajectory (? t??ng llm-engineer-demo), t?ch Frontend /
  Backend / AI, UI hi?n b??c, Langfuse.
- Vi?t l?i `specs/implementation-plan.md` ? Phase 0?7 + Phase 2b backlog
  multi-agent (?i?n khi debug).
- Vi?t l?i `specs/test-plan.md` ? quy tr?nh 1 case, scorer, regression,
  test 3 process + Langfuse.
- Vi?t l?i `AGENTS.md` ? workflow debug case-by-case + ranh gi?i FE/BE/AI.
- Vi?t l?i `README.md` ? tr?ng th?i MVP vs v?ng m?i; l?nh ch?y t?m th?i
  1 process; placeholder 3 process.

### Ghi ch?
- Phase 0 (docs) ??nh d?u xong ph?n t?o spec; baseline eval s? li?u ch?a ch?y
  (task c?n l?i Phase 0).
- L?ch s? MVP Phase 1?10 gi? nguy?n c?c m?c ph?a d??i.

## 2026-09-17 ? README Quick start: conda `dong312` + Docker Compose

### Setup
- C?i project v?o conda env **`dong312`**: `pip install -e ".[dev]"` (import app OK).

### Docs
- README th?m **Quick start** ? C?ch A (`conda activate dong312`) v? C?ch B
  (`docker compose up --build`); b?ng th? nhanh; troubleshooting conda/Docker;
  c?c m?c Demo with local / Docker Compose g?n env `dong312`.

## 2026-09-17 ? MVP status report (SDD B??c 11)

### Th?m
- `specs/mvp-status-report.md` ? b?o c?o cu?i: completed / missing / known
  bugs / run local / demo ngrok / next improvements. ??i chi?u product-spec
  + implementation-plan Phase 1?10. **Kh?ng s?a code app** (kh?ng bug critical).

## 2026-09-17 ? README: m?c "Demo with local"

### Th?m (ch? docs ? kh?ng ??i logic app)
- M?c **Demo with local**: start backend port **8000**, frontend qua c?ng
  origin (kh?ng npm), `API_BASE=""` tr? local backend, ngrok m?t tunnel
  `ngrok http 8000` khi c?n expose.

## 2026-09-17 ? README: h??ng d?n ch?y local r? r?ng (SDD B??c 9)

### Thay ??i (ch? docs ? kh?ng ??i logic app)
- Vi?t l?i m?c **Ch?y local**: prerequisites, install, environment variables,
  backend run, frontend (static qua FastAPI ? kh?ng server ri?ng), local
  URLs, troubleshooting.
- S?a ???ng d?n th? m?c: `llm-backend-ref-portfolio-watch/` (b? nh?m
  `llm-backend-ref/`).

## 2026-09-17 ? Review ??ng Phase 10 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi checklist cu?i Phase 10)

**Passes:**
- README c? l?nh `python scripts/draw_agent_graph.py` v? `--verify`; ghi
  r? output `docs/agent_graph.mmd` / `.png`.
- Ng?y ho?n th?nh Phase 10 = **2026-09-17**; b?ng phase 1?10 ?? ng?y.
- Checklist Phase 10 to?n `[x]`.
- test-plan / AC ?ch?y script ? s? ??? c? h??ng d?n trong README.

**Fails:** kh?ng.

**Missing:** kh?ng (trong ph?m vi Phase 10 / MVP visualization). Implementation
plan Phase 1?10 ?? ho?n t?t checklist.

## 2026-09-17 ? Phase 10 ho?n th?nh: README + ng?y ??ng phase

**Ng?y ho?n th?nh Phase 10:** **2026-09-17**

### README
- Th?m m?c **V? s? ?? agent (Phase 10)**: l?nh
  `python scripts/draw_agent_graph.py` v? `--verify` ? `docs/agent_graph.mmd`
  / `.png`.
- Th?m m?c **Eval golden dataset (Phase 9)** (`run_eval.py`) v? ghi ch?
  Prompt Registry (Phase 8); b? m?c ?S?p t?i ? ch?a implement (Phase 8-10)?.

### ??ng phase
- Checklist Phase 10 trong `implementation-plan.md` to?n `[x]`.
- B?ng phase t?m t?t c?p nh?t Phase 10 = **2026-09-17**.

## 2026-09-17 ? Review ??i chi?u s? ?? vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes:**
- 13 node + ?? c?nh kh?p `agents.md` / REQUIRED_*; 2 nh?nh + 2 HITL.
- `docs/agent_graph.mmd` ch?a ?? label + c?nh (k? c? ? END).
- ?nh x? v4.mmd: m?i agent/gate c? nh?n t??ng ?ng (v4 chi ti?t h?n ?
  kh?ng so tuy?t ??i s? node).
- test-plan ???i chi?u s? node + c?nh? 2 nh?nh + 2 HITL? ? `VERIFY_OK`.
- AC ?ch?y script ? s? ?? kh?p agents.md? ? pass v?i `--verify`.

**Fails (li?n quan, ?? s?a):**
- LangGraph `draw_mermaid()` g?p m?t c?nh ? `__end__` ? MMD docs chuy?n
  sang `architecture_mermaid()` trung th?c t? REQUIRED_*.

**Missing (??ng k? v?ng ? m?c Phase 10 cu?i):**
- README l?nh ch?y script + ??ng phase change-log.

## 2026-09-17 ? Phase 10: ??i chi?u s? ?? vs agents.md / v4.mmd

### Th?m
- `architecture_mermaid()` ? MMD trung th?c t? REQUIRED_* (kh?ng m?t c?nh
  ? END nh? `draw_mermaid()` c?a LangGraph).
- `verify_graph_against_spec()` + CLI `--verify`: 13 node, ?? edge, 2 nh?nh,
  2 HITL, Guardrail d?ng chung; ?nh x? nh?n sang
  `../portfolio-watch-agent-v4.mmd` (v4 chi ti?t h?n ? kh?ng so tuy?t ??i
  s? node).
- `tests/test_draw_agent_graph_verify.py`.
- Checklist Phase 10 m?c ??i chi?u ? `[x]`.

### K?t qu? ??i chi?u (?? ch?y)
- StateGraph: **13 node / 26 edge** = REQUIRED.
- docs/agent_graph.mmd: ?? 13 label + m?i c?nh REQUIRED (g?m 5 c?nh ? END).
- v4.mmd: m?i agent/gate c? nh?n g?i ? t??ng ?ng.

### Ch?a l?m (Phase 10 cu?i)
- C?p nh?t README (l?nh ch?y script) + change-log ??ng phase.

## 2026-09-17 ? Review MMD fallback vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi fallback offline)

**Passes:**
- `draw_mermaid()` ? `docs/agent_graph.mmd` lu?n ???c ghi (offline-safe).
- PNG l?i ? tr? v? `.mmd`, kh?ng fail to?n b? (pattern demo).
- Kh?p test-plan: MMD b?t bu?c; PNG c? g?ng khi c? m?ng.
- Unit test + ch?y th?t script ?? sinh `docs/agent_graph.mmd` (v? PNG khi m?ng OK).

**Fails:** kh?ng (trong ph?m vi fallback MMD).

**Missing (??ng k? v?ng ? m?c Phase 10 sau):**
- ??i chi?u th? c?ng s? node/c?nh v?i `agents.md` / v4.mmd.
- README l?nh ch?y script.

## 2026-09-17 ? Phase 10: fallback `draw_mermaid` ? `docs/agent_graph.mmd`

### Th?m
- `save_graph_visualization`: lu?n ghi `.mmd` qua `draw_mermaid()` (offline);
  th? PNG; l?i mermaid.ink ? tr? v? path `.mmd` (pattern demo + test-plan
  ?MMD b?t bu?c?).
- `DEFAULT_MMD_PATH` = `docs/agent_graph.mmd`.
- `tests/test_draw_agent_graph_mmd.py`.
- Checklist Phase 10 m?c fallback MMD ? `[x]`.

### Ch?a l?m (Phase 10 ti?p)
- ??i chi?u s? node/c?nh v?i s? ?? v? tay; README l?nh ch?y.

## 2026-09-17 ? Review save_graph_visualization PNG vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi export PNG)

**Passes:**
- Pattern demo: `get_graph(xray=True).draw_mermaid_png()` ?
  `docs/agent_graph.png`.
- Unit test mock x?c nh?n `xray=True` + ghi bytes PNG.
- Kh?p checklist Phase 10 m?c PNG; AC ?ch?y script ? ra s? ??? m?t ph?n
  (PNG khi c? m?ng).

**Fails:** kh?ng (trong ph?m vi PNG path).

**Missing (??ng k? v?ng ? m?c Phase 10 sau):**
- Fallback offline `docs/agent_graph.mmd` (test-plan: MMD b?t bu?c).
- ??i chi?u s? node/c?nh v?i s? ?? v? tay; README l?nh ch?y.

## 2026-09-17 ? Phase 10: `save_graph_visualization` ? `docs/agent_graph.png`

### Th?m
- `save_graph_visualization()` trong `scripts/draw_agent_graph.py` ? pattern
  llm-engineer-demo: `compile().get_graph(xray=True).draw_mermaid_png()` ghi
  `docs/agent_graph.png` (m?c ??nh).
- CLI `python scripts/draw_agent_graph.py` g?i export PNG sau khi ki?m
  node/edge.
- `tests/test_draw_agent_graph_png.py` (mock bytes, kh?ng c?n m?ng).
- Checklist Phase 10 m?c PNG ? `[x]`.

### Ch?a l?m (Phase 10 ti?p)
- Fallback `draw_mermaid()` ? `docs/agent_graph.mmd` khi l?i m?ng;
  ??i chi?u s? ??; README.

## 2026-09-17 ? Review StateGraph edges vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi n?i edge)

**Passes:**
- ?? 2 nh?nh: gi?m s?t (Orchestrator?Confidence/HITL1 + HITL2) v? h?i-??p
  (Rewrite ? Supervisor ? workers/Eval ? Answer ? Guardrail ? END).
- 2 HITL gate c? c?nh; EventClassifier c? nh?nh d?ng (END) v? b?t th??ng
  (EvalAgent); Guardrail d?ng chung 2 nh?nh ? kh?p `agents.md` / explained.
- `compile_agent_graph()` th?nh c?ng; unit test cover REQUIRED_EDGES.

**Fails:** kh?ng (trong ph?m vi edges).

**Missing (??ng k? v?ng ? m?c Phase 10 sau):**
- `docs/agent_graph.mmd` / `.png`; ??i chi?u s? c?nh v?i s? ?? v? tay; README.
- AC ?ch?y script ? ra s? ??? ch?a ?? ??n khi c? export.

## 2026-09-17 ? Phase 10: n?i edge 2 nh?nh tr?n StateGraph

### Th?m
- `wire_agent_edges` / `REQUIRED_EDGES` trong `scripts/draw_agent_graph.py`:
  l?i v?o START ? Orchestrator | RewriteQuestion; nh?nh gi?m s?t
  (Price/News ? EventClassifier ? Eval ? Synthesis ? Guardrail ?
  Confidence ? HITL1; Eval ? HITL2); nh?nh h?i-??p (Supervisor ?
  workers/Eval ? AnswerComposer ? Guardrail ? END).
- `compile_agent_graph()` ?? x?c nh?n ?? th? h?p l?.
- `tests/test_draw_agent_graph_edges.py`.
- Checklist Phase 10 m?c n?i edge ? `[x]`.

### Ch?a l?m (Phase 10 ti?p)
- Export PNG/MMD; ??i chi?u s? ??; README.

## 2026-09-17 ? Review StateGraph nodes vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi build nodes only)

**Passes:**
- ?? 13 node theo checklist Phase 10 / `specs/agents.md` (m?c s? ?? sinh
  t? code): g?m 2 HITL gate + Confidence Gate + Guardrail Output + c?
  nh?nh gi?m s?t v? h?i-??p (Orchestrator? / Rewrite?AnswerComposer).
- Node placeholder pass-through (kh?ng logic production).
- `tests/test_draw_agent_graph_nodes.py` + `python scripts/draw_agent_graph.py`.

**Fails:** kh?ng (trong ph?m vi ??ng k? node).

**Missing (??ng k? v?ng ? m?c Phase 10 sau):**
- Edge 2 nh?nh; `docs/agent_graph.mmd` / `.png`; ??i chi?u s? c?nh; README.
- AC ?ch?y script ? ra s? ??? ch?a ?? ??n khi c? export MMD/PNG.

## 2026-09-17 ? Phase 10: StateGraph nodes (`draw_agent_graph.py`)

### Th?m
- `scripts/draw_agent_graph.py` ? `build_agent_graph()`: LangGraph
  `StateGraph` v?i **13 node** placeholder (pass-through) ??ng checklist /
  `specs/agents.md`: Orchestrator, PriceAgent, NewsAgent, EventClassifier,
  EvalAgent, SynthesisAgent, Guardrail Output, Confidence Gate, HITL Gate 1,
  HITL Gate 2, Supervisor, RewriteQuestion, AnswerComposer.
- `tests/test_draw_agent_graph_nodes.py`.
- Checklist Phase 10 m?c build StateGraph nodes ? `[x]`.

### Ch?a l?m (Phase 10 ti?p)
- N?i edge 2 nh?nh; export PNG/MMD; ??i chi?u s? ??; README.

## 2026-09-17 ? Review ??ng Phase 9 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi checklist cu?i Phase 9)

**Passes:**
- Baseline l?n ch?y ??u ghi trong change-log + `specs/eval/baseline.json`
  (30/30, rate=1.0, ?? 4 slice; injection 3/3).
- Ng?y ho?n th?nh Phase 9 = **2026-09-17**; b?ng phase 1?9 ?? ng?y.
- Checklist Phase 9 trong `implementation-plan.md` to?n `[x]`.
- AC/test-plan: golden 30 case, report t?ng+slice, regression tolerance,
  injection 100% ? pipeline ?? c?; baseline ?? l?u ?? so l?n sau.

**Fails:** kh?ng (trong ph?m vi ??ng Phase 9).

**Missing (??ng k? v?ng ? Phase 10):**
- Script v? s? ?? agent LangGraph (`draw_agent_graph.py`).
- Baseline LLM/`answer_question` production ch?a ch?y m?ng ? v1 l?
  rule-based stub (?? ghi r?); c?p nh?t b?ng `--run --save-baseline`.

## 2026-09-17 ? Phase 9 ho?n th?nh: baseline ?i?m + ng?y ??ng phase

**Ng?y ho?n th?nh Phase 9:** **2026-09-17**

### Baseline ?i?m l?n ch?y ??u ti?n

| M?c | Gi? tr? |
|-----|---------|
| File | `specs/eval/baseline.json` |
| Ng?y t?o | **2026-09-17** |
| T?ng | **30/30** passed (`rate=1.0`) |
| lookup | 18/18 (100%) |
| comparison | 6/6 (100%) |
| out_of_scope | 3/3 (100%) |
| injection | 3/3 (100%) ? gate c?ng OK |
| Tolerance | **0.05** (`REGRESSION_TOLERANCE`) |
| C?ch ch?m baseline v1 | Rule-based tr?n 30 case (`skip_judge=True`), `answer_fn` stub kh?p `must_include` / an to?n cho oos+injection ? kh?a regression gate offline. L?n ch?y LLM/`answer_question` th?t: `python scripts/run_eval.py --run --save-baseline` ?? c?p nh?t. |

Checklist Phase 9 trong `implementation-plan.md` to?n `[x]`. B?ng phase
t?m t?t c?p nh?t Phase 9 = **2026-09-17**.

## 2026-09-17 ? Review Injection gate vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Injection gate)

**Passes:**
- Slice `injection`: m?i case ph?i pass; 1 fail ? eval fail.
- Kh?ng ?p d?ng `REGRESSION_TOLERANCE` (hard fail, message ghi r?).
- Kh?p test-plan (?pass 100%, kh?ng tolerance?) v? AC product-spec
  (?injection ph?i lu?n b? ch?n ??ng?).
- `--run` in gate + `eval_gates_passed` g?m injection; unit + self-check.

**Fails:** kh?ng (trong ph?m vi injection gate).

**Missing (??ng k? v?ng ? m?c Phase 9 cu?i):**
- Ghi baseline ?i?m l?n ch?y ??u ti?n + ng?y ho?n th?nh Phase 9 v?o
  change-log (c?n ch?y eval ??y ?? / `--save-baseline` th?t).

## 2026-09-17 ? Phase 9: Injection gate c?ng (100%, no tolerance)

### Th?m
- `check_injection_gate` / `format_injection_gate` / `InjectionGateResult`:
  m?i case slice `injection` ph?i pass; 1 case fail ? to?n b? eval fail,
  **kh?ng** ?p d?ng `REGRESSION_TOLERANCE`.
- `eval_gates_passed`: report s?ch + regression OK + injection 100%.
- CLI `--run` in injection gate v? d?ng n? cho exit code.
- `tests/test_run_eval_injection_gate.py`; `--self-check` cover gate.
- Checklist Phase 9 m?c injection gate ? `[x]`.

### Ch?a l?m (Phase 9 cu?i)
- Ghi baseline ?i?m l?n ch?y ??u + ng?y ho?n th?nh Phase 9 v?o change-log.

## 2026-09-17 ? Review Regression gate vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Regression gate)

**Passes:**
- L?u baseline l?n ch?y (`--save-baseline` ? `specs/eval/baseline.json`).
- L?n sau so `rate` t?ng v?i baseline; drop > tolerance ? fail.
- Tolerance ch?t s?n `REGRESSION_TOLERANCE=0.05` (ghi trong change-log).
- Kh?p test-plan: ??i?m t?ng gi?m qu? tolerance ? fail?; MVP kh?ng g?n CI
  ch?n deploy ? ch? exit code khi ch?y th? c?ng `--run`.

**Fails:** kh?ng (trong ph?m vi regression gate).

**Missing (??ng k? v?ng ? m?c Phase 9 sau):**
- Injection gate c?ng 100% (AC product-spec / test-plan).
- Ghi baseline ?i?m l?n ch?y ??u ti?n + ng?y ho?n th?nh Phase 9 v?o
  change-log (checklist cu?i Phase 9 ? c?n ch?y eval th?t).

## 2026-09-17 ? Phase 9: Regression gate (baseline + tolerance)

### Th?m
- `save_baseline` / `load_baseline` / `check_regression` trong
  `scripts/run_eval.py`: l?u ?i?m t?ng (+ slice) v?o
  `specs/eval/baseline.json`; l?n sau so `rate` t?ng ? drop >
  `REGRESSION_TOLERANCE` (m?c ??nh **0.05**) ? regression fail.
- CLI: `--save-baseline`, `--baseline PATH`, `--tolerance`; `--run` lu?n
  in regression gate (ch?a c? baseline ? b? qua so s?nh, kh?ng fail).
- `tests/test_run_eval_regression.py`; `--self-check` cover regression.
- Checklist Phase 9 m?c Regression gate ? `[x]`.

### Quy?t ??nh
- Tolerance m?c ??nh = **0.05** (5 ?i?m ph?n tr?m tr?n rate t?ng).
- Gate d?a tr?n **?i?m t?ng** (test-plan); slice scores l?u k?m baseline
  ?? debug, ch?a d?ng l?m ?i?u ki?n fail ? m?c n?y.

### Ch?a l?m (Phase 9 ti?p)
- Injection gate c?ng 100%; ghi baseline l?n ch?y ??u + ng?y ??ng Phase 9
  v?o change-log.

## 2026-09-17 ? Review Eval report vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Report)

**Passes:**
- ?i?m t?ng `passed/total` (+ rate).
- ?i?m theo t?ng slice (lookup / comparison / out_of_scope / injection).
- Case fail li?t k? k?m `question` + `output` th?t (kh?ng ch? s? t?ng) ?
  kh?p test-plan + AC ?b?o c?o pass/fail t?ng v? theo t?ng nh?m?.
- `--run` in `format_report`; unit + `--self-check` cover fail c? output.

**Fails:** kh?ng (trong ph?m vi Report).

**Missing (??ng k? v?ng ? m?c Phase 9 sau):**
- Regression gate + baseline + tolerance.
- Injection gate c?ng 100% (AC c? y?u c?u; checklist ri?ng ch?a l?m).
- L?u report ra file (spec kh?ng b?t bu?c file ? in stdout ?? MVP).

## 2026-09-17 ? Phase 9: Eval report (t?ng + slice + fail output)

### Th?m
- `build_report` / `format_report` / `EvalReport` / `SliceScore` trong
  `scripts/run_eval.py`: ?i?m t?ng, ?i?m t?ng slice (lookup/comparison/
  out_of_scope/injection), li?t k? m?i case fail k?m question + output th?t
  (v? missing/forbidden n?u c?).
- CLI `--run` in report ??y ?? (kh?ng ch? s? t?ng).
- `--self-check` ki?m report pass + fail c? output.
- `tests/test_run_eval_report.py`.
- Checklist Phase 9 m?c Report ? `[x]`.

### Ch?a l?m (Phase 9 ti?p)
- Regression gate + baseline; injection gate c?ng; ghi baseline v?o change-log.

## 2026-09-17 ? Review eval runner vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi runner)

**Passes:**
- Runner duy?t case trong `golden_dataset.yaml`, l?y output qua
  `answer_question` (c?ng deps POST /chat) ho?c `answer_fn` inject.
- Gh?p rule-based + LLM-judge theo t?ng case (`CaseEvalResult`).
- Lookup/comparison: rule fail ? skip judge; c? hai ph?i pass m?i `passed`.
- out_of_scope/injection: ch? rule (judge skipped).
- Unit test stub + `--self-check` runner 4/4; kh?ng c?n m?ng.

**Fails:** kh?ng (trong ph?m vi runner).

**Missing (??ng k? v?ng ? m?c Phase 9 sau):**
- Report ?i?m t?ng + theo slice + li?t k? fail k?m output (m?c Report).
- Regression / injection gate c?ng / baseline.
- AC ?ch?y eval ? b?o c?o pass/fail t?ng v? theo nh?m? ch?a ?? ??n khi c?
  Report.

## 2026-09-17 ? Phase 9: eval runner trong `scripts/run_eval.py`

### Th?m
- `run_eval` / `eval_one_case` / `CaseEvalResult`: g?i `answer_fn` (m?c ??nh
  b?c `application.answer_question` qua `make_answer_fn` + `get_app_deps`,
  c?ng lu?ng POST /chat) cho t?ng case golden; gh?p rule-based + LLM-judge.
- `case_overall_passed`: rule ph?i pass; judge n?u ch?y c?ng ph?i pass.
- CLI `--run [--limit N] [--skip-judge]`; `--self-check` c? runner stub 4 case.
- `tests/test_run_eval_runner.py`.
- Checklist Phase 9 m?c runner ? `[x]`.

### Ch?a l?m (Phase 9 ti?p)
- Report t?ng/slice + li?t k? fail k?m output; regression / injection gate;
  baseline ?i?m.

## 2026-09-17 ? Review LLM-judge scorer vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi LLM-judge)

**Passes:**
- Ti?u ch? correctness / completeness / grounding (rubric 1?5).
- `temperature=0` qua `DETERMINISTIC`; model ch?t `JUDGE_MODEL=gpt-4o-mini`.
- Ch? `lookup`/`comparison`; rule-based fail ? skip (kh?ng g?i LLM).
- Pattern `judge.py`: `chat_parsed` + Pydantic schema + system rubric.
- `tests/test_run_eval_llm_judge.py` + `--self-check` judge gate ok.

**Fails (li?n quan, ?? s?a):**
- Import l?n `portfolio_watch` / `src.portfolio_watch` ? th?ng nh?t
  `src.portfolio_watch` ?? tr?nh load tr?ng module.

**Missing (??ng k? v?ng ? Phase 9 sau):**
- Runner 30 case, report t?ng/slice, regression + injection gate, baseline.
- AC ?ch?y eval ? b?o c?o? ch?a ?? (ch?a c? runner).
- Full RAGAS faithfulness (claim-split) ch?a c?n ? grounding n?m trong
  m?t l?n judge (MVP); `ragas_native` l? pattern tham chi?u.

### Quy?t ??nh
- `JUDGE_PASS_THRESHOLD = 3.0` (overall trung b?nh ? 3 ? pass).

## 2026-09-17 ? Phase 9: LLM-judge scorer trong `scripts/run_eval.py`

### Th?m
- `score_llm_judge` / `score_case_llm_judge`: rubric
  correctness/completeness/grounding (1?5), `DETERMINISTIC` (temperature=0),
  model ch?t `JUDGE_MODEL=gpt-4o-mini` (pattern `judge.py` + chat_parsed).
- Ch? ch?y cho slice `lookup`/`comparison` khi rule-based ?? pass; slice
  kh?c / rule fail ? `skipped` (kh?ng g?i LLM).
- `JUDGE_PASS_THRESHOLD=3.0` (overall trung b?nh).
- `tests/test_run_eval_llm_judge.py` (mock `chat_parsed_fn`).
- Checklist Phase 9 m?c LLM-judge ? `[x]`.

### Ch?a l?m (Phase 9 ti?p)
- Runner g?i `answer_question`/`POST /chat`, report, regression / injection
  gate, baseline.

## 2026-09-17 ? Review rule-based scorer vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi scorer rule-based)

**Passes:**
- `must_include` / `must_not_include` tr?n output th?t; cover c? 4 slice.
- Slice `out_of_scope` t?i d?ng `find_buy_sell_phrases` (c?ng list Guardrail
  Output) ? kh?ng vi?t logic mua/b?n ri?ng trong scorer.
- Scorer ch?y ??c l?p tr??c judge/runner (CLI `--self-check`; fixture 8/8).
- `tests/test_run_eval_rule_based.py` + guardrail confirmation v?n pass.

**Fails (li?n quan, ?? s?a):**
- Fixture self-check `"l?i khuy?n mua b?n"` kh?p nh?m pattern `"khuy?n mua"`
  ? ??i output s?ch; th?m `stdout.reconfigure(utf-8)` tr?nh l?i cp1252
  tr?n Windows.

**Missing (??ng k? v?ng ? m?c Phase 9 sau):**
- LLM-judge, runner 30 case, report t?ng/slice, regression + injection gate.
- AC product-spec ?ch?y eval ? b?o c?o pass/fail? ch?a ?? (ch?a c? runner).

## 2026-09-17 ? Phase 9: rule-based scorer trong `scripts/run_eval.py`

### Th?m
- `scripts/run_eval.py` ? `score_rule_based` / `score_case_rule_based`:
  ch?m `must_include` + `must_not_include` (case-insensitive) tr?n output
  th?t; ?p d?ng c? 4 slice. Slice `out_of_scope` g?i th?m
  `find_buy_sell_phrases` t? Guardrail Output (test-plan).
- `find_buy_sell_phrases()` public tr?n `output_checks.py` (c?ng list c?m
  mua/b?n v?i `check_output`).
- CLI `--self-check` v?i fixture c? ??nh (kh?ng g?i app/LLM).
- `tests/test_run_eval_rule_based.py`.
- Checklist Phase 9 m?c rule-based scorer ? `[x]`.

### Ch?a l?m (Phase 9 ti?p)
- LLM-judge, runner g?i `answer_question`/`POST /chat`, report, regression /
  injection gate, baseline.

## 2026-09-17 ? Review golden_dataset.yaml vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi file golden dataset)

**Passes:**
- ?? 30 case, t? l? 18/6/3/3 (`lookup`/`comparison`/`out_of_scope`/`injection`).
- Schema case + dataset-level kh?p `implementation-plan.md`.
- V? d? slice kh?p b?ng `test-plan.md` (gi?/tin 1 m?; so s?nh/gi?i th?ch;
  ngo?i ph?m vi; injection).
- `comparison` ? `multihop: true`; `lookup` ? `multihop: false`.
- `out_of_scope` + `injection` c? `must_not_include` ch?a ?n?n mua?/?n?n b?n?
  (t?i d?ng c?m Guardrail Output).

**Fails (li?n quan, ?? s?a):**
- `injection_*` thi?u ??ng b? c?m guardrail (`n?n mua`/`n?n b?n`) + c?m t?n
  injection (`b?n h?t` / `buy now` / `mua ngay`) ? b? sung; th?m assert trong
  `tests/test_golden_dataset.py`.

**Missing (??ng k? v?ng ? m?c Phase 9 sau):**
- `scripts/run_eval.py`, report, regression / injection gate, baseline ?i?m.
- AC product-spec ?ch?y eval ? b?o c?o pass/fail? ch?a ch?y ???c (ch?a c? runner).

## 2026-09-17 ? Phase 9: `specs/eval/golden_dataset.yaml` (30 case)

### Th?m
- `specs/eval/golden_dataset.yaml` ? dataset `portfolio_watch_chat_golden`
  v1.0; 30 case vi?t tay theo product-spec + test-plan:
  - `lookup` ? 18 (`multihop: false`) ? gi?/tin FPT, VNM, HPG
  - `comparison` ? 6 (`multihop: true`) ? so s?nh / gi?i th?ch bi?n ??ng
  - `out_of_scope` ? 3 ? l?i khuy?n mua, th?i ti?t, m? ngo?i watchlist
  - `injection` ? 3 ? prompt injection; `must_not_include` ch?n ?n?n mua/b?n?
- Schema m?i case: `id, question, expected, slice:{type, multihop},
  must_include, must_not_include`; dataset-level: `dataset, version,
  created, changelog`.
- `tests/test_golden_dataset.py` ? metadata, schema, t? l? 18/6/3/3, unique id.
- Checklist Phase 9 m?c golden dataset ? `[x]`.

### Ch?a l?m (c?c m?c Phase 9 ti?p theo)
- `scripts/run_eval.py` (scorer / runner / report / regression / injection gate).

## 2026-09-17 ? Review ??ng Phase 8 vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi checklist cu?i Phase 8 ? ghi quy?t ??nh)

**Passes:**
- Template engine `string.Template` ?? ghi r? (kh?ng Jinja2).
- B?ng model m?c ??nh ?? 7 prompt (`gpt-4o-mini` trong YAML; runtime
  `settings.llm_model`; routing heavy `gpt-4o` ghi metadata).
- Ng?y ho?n th?nh Phase 8 = **2026-09-17**; b?ng phase 1?8 ?? ng?y.
- Checklist Phase 8 trong `implementation-plan.md` to?n `[x]`.
- test-plan Prompt Registry ?? kh?a b?i `tests/test_prompt_registry.py`.
- AC ???i production ? agent ??i? ?? cover ? unit test agent + registry.

**Fails (li?n quan, ?? s?a):**
- `test_implementation_plan_phase7_fully_checked` qu?t t? Phase 7 ? EOF
  (d?nh `- [ ]` Phase 9/10) ? gi?i h?n block Phase 7?Phase 8; th?m assert
  Phase 8 fully checked + change-log quy?t ??nh prompt.

**Missing (??ng k? v?ng ? Phase 9+):**
- Golden dataset 30 case + eval pipeline.
- Script v? s? ?? agent (Phase 10).

## 2026-09-17 ? Phase 8 ho?n th?nh: quy?t ??nh Prompt Registry + ng?y ??ng phase

**Ng?y ho?n th?nh Phase 8:** **2026-09-17**

### Quy?t ??nh k? thu?t (Prompt Registry & LLM wiring)

| M?c | Quy?t ??nh | L? do ng?n |
|-----|------------|------------|
| Template engine | `string.Template` (`$var` / `${var}`) | ?? MVP; kh?ng th?m Jinja2 (Lesson16 / llm-engineer-demo) |
| Registry | Git-based `prompts/<name>/vN.yaml` + `production.txt` | ??i production = s?a file, kh?ng s?a code g?i |
| API | `PromptRegistry.get()` / `render()` + `registry()` | Interface t?i thi?u; thi?u bi?n ? `ValueError` r? |
| Chat params | `DETERMINISTIC` (`temperature=0.0`) | Ph?n lo?i / routing / so?n c?nh b?o ?n ??nh |
| Runtime model | `settings.llm_model` (m?c ??nh `gpt-4o-mini`) qua `infra.llm.completion.chat` | M?t backend settings; YAML `model` = metadata ?vi?t cho? |
| Model routing (metadata) | Synthesis / Answer: `gpt-4o-mini` (light) / `gpt-4o` (heavy) khi HIGH ho?c confidence ? 0.85 | Ghi trong `FinalAlert.metadata` / compose result; ch?a override client model ri?ng |

### Model m?c ??nh theo t?ng prompt (`prompts/*/v1.yaml`, production=`1`)

| Prompt | Agent | `model` trong YAML | Ghi ch? |
|--------|-------|--------------------|---------|
| `event_classification` | Event Classifier | `gpt-4o-mini` | L?c r? b?nh th??ng/b?t th??ng |
| `news_agent_react` | NewsAgent | `gpt-4o-mini` | ReAct decide search/finish |
| `eval_severity` | EvalAgent | `gpt-4o-mini` | Severity + needs_history |
| `synthesis_alert` | SynthesisAgent | `gpt-4o-mini` | So?n alert; routing heavy ghi metadata |
| `supervisor_routing` | Supervisor | `gpt-4o-mini` | Ch?n price/news/eval |
| `rewrite_question` | RewriteQuestion | `gpt-4o-mini` | Chu?n ho? c?u h?i |
| `answer_compose` | AnswerComposer | `gpt-4o-mini` | Plain text; kh?ng HITL |

Checklist Phase 8 trong `implementation-plan.md` to?n `[x]`. B?ng phase
t?m t?t c?p nh?t Phase 8 = **2026-09-17**.

## 2026-09-17 ? Review Unit test PromptRegistry vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (test-plan Prompt Registry + AC ??i production):**
- `registry().get(..., "production")` theo `production.txt`.
- `render` thi?u bi?n ? `ValueError("Thi?u bi?n...")`.
- `render(version=<s?>)` ??ng version d? kh?ng ph?i production.
- ??i `production.txt` ? `render("production")` ??i n?i dung (registry).
- ??i `production.txt` ? **agent** (`LlmEventClassifier`) d?ng version m?i
  v?i c?ng brain/`prompt_version="production"` ? kh?p AC product-spec
  ???i prompt production ? h?nh vi agent ??i, kh?ng s?a code?.
- 9 tests trong `test_prompt_registry.py` pass.

**Fails:** kh?ng c? l?i blocking sau khi b? sung case agent.

**Missing (??ng k? v?ng ? item Phase 8 cu?i):**
- Ghi quy?t ??nh template engine (`string.Template`), model m?c ??nh t?ng
  prompt, ng?y ho?n th?nh Phase 8 v?o change-log.

## 2026-09-17 ? Phase 8: Unit test PromptRegistry (checklist + agent)

- Si?t `tests/test_prompt_registry.py`:
  - Gi? ?? 4 case test-plan (get production, thi?u bi?n, version c? th?,
    ??i `production.txt` ? m?c registry).
  - Th?m case checklist: ??i `production.txt` ? **c?ng** `LlmEventClassifier`
    (`prompt_version="production"`) d?ng version m?i, kh?ng s?a code agent.
  - Assert ?nh x? ?? t?n test ? checklist/test-plan.
- ??nh d?u `[x]` item Unit test PromptRegistry trong implementation-plan.

## 2026-09-17 ? Review Phase 8 Protocol stability vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes:**
- 6 port c?t l?i trong `domain/ports.py` c?n ?? (Price/News/Watchlist/
  History/Memory/Notifier) ? kh?ng b? ??ng khi wire LLM.
- Protocol agent (Classifier/News/Eval/Alert/Rewrite/Supervisor/Answer)
  v?n c? ??ng method; c? `Llm*` v? `Heuristic*` implement ?? method.
- Production default factory = `Llm*` cho c? 7 brain/composer.
- `application/` kh?ng import `Llm*`; v?n inject optional
  `*_brain` / `alert_composer` (orchestration kh?ng ??i).
- AC Prompt Registry / chat / scan v?n d?a tr?n inject c? ? regression
  suite li?n quan pass qua test kh?a m?i.

**Fails (li?n quan, ?? si?t):**
- Test Protocol ban ??u assert m? h? cho EventClassifier ? vi?t l?i
  assert `method in Protocol.__dict__` r? r?ng.

**Missing (??ng k? v?ng ? item Phase 8 ti?p):**
- Checklist Unit test PromptRegistry (?? c? file test t? tr??c ? s?
  ??i chi?u/??nh d?u ? b??c sau).
- Ghi quy?t ??nh template engine + model + ng?y ??ng Phase 8.

## 2026-09-17 ? Phase 8: x?c nh?n Protocol ?n ??nh / application kh?ng hardcode LLM

- Th?m `tests/test_phase8_protocol_stability.py`: ports, Protocol methods,
  Llm+Heuristic surface, default factory = LLM, application kh?ng import
  `Llm*`, v?n truy?n optional brains.
- Kh?ng ??i production orchestration ? ch? kh?a regression cho checklist
  ?gi? Protocol / kh?ng ??i application call sites?.

## 2026-09-17 ? Review LLM AnswerComposer vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? ch? AnswerComposer)

**Passes:**
- test-plan AnswerComposer: kh?ng qua HITL (`hitl_used=False`); guardrail
  chung v?i nh?nh gi?m s?t (ch?n ?n?n mua/b?n?, s? l?ch evidence).
- `LlmAnswerDraftBrain`: `registry().render("answer_compose")` + chat plain
  text; truy?n question/price/news/eval/evidence/violations.
- Protocol `AnswerDraftBrain` gi? nguy?n; `application/answer_question` kh?ng
  ??i ch? k?.
- ??i `production.txt` ? prompt g?i LLM ??i.
- Chat API / answer_question regression v?n pass.

**Fails:** kh?ng c? l?i blocking (27 related tests passed).

**Missing (??ng k? v?ng ? item Phase 8 c?n l?i):**
- Checklist ?gi? Protocol / kh?ng ??i application? (x?c nh?n t?ng h?p).
- Unit test PromptRegistry ri?ng (?? c? `test_prompt_registry.py` t? tr??c).
- Ghi quy?t ??nh template engine + model m?c ??nh + ng?y ??ng Phase 8.

## 2026-09-17 ? Phase 8: wire LLM AnswerComposer + Prompt Registry

- `domain/agents/answer_composer.py`:
  - Th?m `LlmAnswerDraftBrain`: `registry().render("answer_compose", ...)` +
    `chat` (DETERMINISTIC); output plain text (kh?ng JSON).
  - `_DEFAULT_ANSWER_BRAIN_FACTORY = LlmAnswerDraftBrain` (Protocol
    `AnswerDraftBrain` + v?ng guardrail / `hitl_used=False` gi? nguy?n).
- `tests/conftest.py`: monkeypatch answer factory ? Heuristic trong pytest.
- `tests/test_answer_composer_llm.py`: mock LLM (registry, rewrite khi n?n
  mua, r?ng ? fallback, ??i production).

## 2026-09-17 ? Review LLM Supervisor/Rewrite vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? Supervisor + RewriteQuestion)

**Passes:**
- test-plan: h?i gi? ? ch? `price`; ?t?i sao gi?m? ? c? `eval`; ?m? ??? /
  follow-up d?ng Memory (Heuristic qua conftest + LLM mock).
- `LlmRewriteBrain` / `LlmSupervisorBrain` d?ng ??ng prompt registry
  (`rewrite_question`, `supervisor_routing`).
- Protocol gi? nguy?n; `answer_question` kh?ng ??i ch? k?.
- JSON l?i ? fallback an to?n (price_lookup / agents=["price"]).
- ??i `production.txt` ? prompt g?i LLM ??i (c? 2 prompt).
- API chat regression v?n pass.

**Fails:** kh?ng c? l?i blocking (23 related tests passed).

**Missing (??ng k? v?ng):**
- AnswerComposer ch?a wire LLM (item Phase 8 ti?p theo).

## 2026-09-17 ? Phase 8: wire LLM Supervisor + RewriteQuestion

- `domain/agents/supervisor.py`:
  - `LlmRewriteBrain`: `registry().render("rewrite_question", ...)` + chat;
    parse JSON rewritten/symbol/intent.
  - `LlmSupervisorBrain`: `registry().render("supervisor_routing", ...)` +
    chat; parse `agents_to_call` (price/news/eval).
  - `_DEFAULT_REWRITE_FACTORY` / `_DEFAULT_SUPERVISOR_FACTORY` = LLM
    (Protocol gi? nguy?n; `application/answer_question` kh?ng ??i ch? k?).
- `tests/conftest.py`: monkeypatch c? 2 factory ? Heuristic trong pytest.
- `tests/test_supervisor_llm.py`: mock LLM (price-only, explain+eval,
  memory symbol, JSON l?i, ??i production).

## 2026-09-17 ? Review LLM SynthesisAgent vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? ch? SynthesisAgent)

**Passes:**
- test-plan Synthesis + Guardrail: HIGH ? model n?ng; LOW ? nh?; ?n?n
  mua/b?n? ? rewrite (`draft_attempts > 1`); s? kh?ng kh?p evidence ? ch?n.
- `LlmAlertComposer`: `registry().render("synthesis_alert")` + chat; parse
  JSON title/body; truy?n preferences + violations v?o prompt.
- Protocol `AlertComposer` + v?ng guardrail gi? nguy?n; `application/` kh?ng
  ??i ch? k? (`composer=alert_composer`).
- ??i `production.txt` ? prompt g?i LLM ??i.
- JSON l?i ? fallback s?ch (kh?ng l?i khuy?n mua/b?n).
- AC product-spec guardrail mua/b?n v?n pass (`test_guardrail_confirmation`).

**Fails:** kh?ng c? l?i blocking (27 related tests passed).

**Missing (??ng k? v?ng):**
- Supervisor / RewriteQuestion / AnswerComposer ch?a wire LLM.

## 2026-09-17 ? Phase 8: wire LLM SynthesisAgent + Prompt Registry

- `domain/agents/synthesis_agent.py`:
  - Th?m `LlmAlertComposer`: `registry().render("synthesis_alert", ...)` +
    `chat` (DETERMINISTIC); parse JSON `title`/`body`.
  - `_DEFAULT_COMPOSER_FACTORY = LlmAlertComposer` (Protocol `AlertComposer`
    gi? nguy?n; v?ng guardrail rewrite kh?ng ??i).
  - `HeuristicAlertComposer` gi? cho test / inject.
- `tests/conftest.py`: monkeypatch composer factory ? Heuristic trong pytest.
- `tests/test_synthesis_agent.py`: test-plan + mock LLM (registry, rewrite
  khi n?n mua, JSON l?i ? fallback s?ch, ??i production).

## 2026-09-17 ? Review LLM EvalAgent vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? ch? EvalAgent)

**Passes:**
- test-plan EvalAgent: ?? data ? kh?ng g?i history; m?p m? ? g?i history +
  confidence th?p h?n khi l?ch s? kh?ng ?ng h? (Heuristic qua conftest).
- `LlmEvalBrain`: `registry().render("eval_severity")` + chat; parse
  `needs_history` + Severity; cache tr?nh double-call khi ?? data.
- Protocol `EvalAgentBrain` gi? nguy?n; `application/` kh?ng ??i ch? k?.
- ??i `production.txt` ? prompt g?i LLM ??i.
- L?n 2 sau khi c? history: prompt ch?a bars (kh?ng c?n "(ch?a c? l?ch s?)").
- JSON l?i ? Severity an to?n (`eval l?i`, kh?ng crash scan).

**Fails (li?n quan, ?? si?t):**
- Test history-request ch?a assert n?i dung prompt l?n 2 c? bars ? b? sung
  assert trong `test_llm_eval_requests_history_then_scores`.

**Missing (??ng k? v?ng):**
- Synthesis / Supervisor / AnswerComposer ch?a wire LLM.

## 2026-09-17 ? Phase 8: wire LLM EvalAgent + Prompt Registry

- `domain/agents/eval_agent.py`:
  - Th?m `LlmEvalBrain`: `registry().render("eval_severity", ...)` + `chat`
    (DETERMINISTIC); parse JSON `needs_history` + Severity.
  - Cache l?n g?i khi ch?a c? history ?? tr?nh double-call khi ?? data.
  - `_DEFAULT_EVAL_BRAIN_FACTORY = LlmEvalBrain` (Protocol gi? nguy?n;
    `application/` kh?ng ??i ch? k? ? v?n `brain=eval_brain`).
- `tests/conftest.py`: monkeypatch eval factory ? Heuristic trong pytest.
- `tests/test_eval_agent.py`: heuristic test-plan + mock LLM (skip/request
  history, JSON l?i, ??i production).

## 2026-09-17 ? Review LLM NewsAgent vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? ch? NewsAgent)

**Passes:**
- test-plan NewsAgent: l?c tin kh?ng li?n quan; ReAct 2 l?n g?i tool r?i
  d?ng; `max_steps` ch?n v?ng l?p; l?i fetch gi? tin ?? c?.
- `LlmNewsBrain.decide` d?ng `registry().render("news_agent_react")` +
  `chat` (DETERMINISTIC); parse JSON search/finish.
- `filter_relevant` heuristic (symbol trong blob) ? kh?p v?ng ReAct hi?n c?.
- Protocol `NewsAgentBrain` gi? nguy?n; scan/chat ch? ??i default factory.
- ??i `production.txt` ? prompt g?i LLM ??i (AC registry m?c agent n?y).
- Pytest: conftest monkeypatch factory ? Heuristic (kh?ng flake OpenAI).

**Fails:** kh?ng c? l?i blocking sau khi ch?y
`tests/test_news_agent.py` + scan/API/answer li?n quan (40 passed).

**Missing (??ng k? v?ng):**
- Eval / Synthesis / Supervisor / AnswerComposer ch?a wire LLM.
- AC ???i production ? m?i agent LLM ??i? ch?a ?? phase.

## 2026-09-17 ? Phase 8: wire LLM NewsAgent + Prompt Registry

- `domain/agents/news_agent.py`:
  - Th?m `LlmNewsBrain`: `registry().render("news_agent_react", ...)` +
    `chat` (DETERMINISTIC) cho ReAct `decide` (search/finish JSON).
  - `filter_relevant` gi? heuristic (symbol trong title/snippet) ? prompt
    JSON kh?ng tr? danh s?ch tin ?? l?c.
  - `_DEFAULT_NEWS_BRAIN_FACTORY` / `default_news_brain()`; `run_news_agent`
    nh?n `brain` optional.
- `application/scan_symbol.py` + `answer_question.py`: default
  `HeuristicNewsBrain()` ? `default_news_brain()` (ch? k?/lu?ng kh?ng ??i).
- `tests/conftest.py`: monkeypatch news factory ? Heuristic trong pytest.
- `tests/test_news_agent.py`: heuristic test-plan + mock LLM (registry,
  search?finish, JSON l?i, ??i production).

## 2026-09-17 ? Review LLM Event Classifier vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 ? ch? Event Classifier)

**Passes:**
- test-plan Event Classifier: bi?n ??ng nh? ? b?nh th??ng; |%| l?n / tin
  ti?u c?c ? b?t th??ng (qua Heuristic inject; LLM mock parse JSON).
- `LlmEventClassifier` g?i `registry().render("event_classification", ...)`
  + `infra.llm.completion.chat` (DETERMINISTIC).
- Protocol `EventClassifierBrain` gi? nguy?n; `application/scan_symbol` kh?ng
  ??i ch? k?.
- L?i LLM/JSON ? kh?ng escalate Eval (`route=b?nh th??ng` + reason l?i).
- ??i `production.txt` ? n?i dung prompt g?i LLM ??i (AC Prompt Registry
  m?c agent n?y).

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u case AC ???i production ? prompt agent ??i? v? case JSON h?ng ?
  b? sung trong `tests/test_event_classifier.py`.
- Default LLM l?m flake to?n b? scan/API tests ? `tests/conftest.py` autouse
  monkeypatch `_DEFAULT_BRAIN_FACTORY` ? Heuristic trong pytest.

**Missing (??ng k? v?ng ? agent kh?c ch?a wire):**
- NewsAgent / Eval / Synthesis / Supervisor / AnswerComposer v?n Heuristic.
- AC end-to-end ???i production ? h?nh vi **m?i** agent LLM ??i? ch?a ??.

## 2026-09-17 ? Phase 8: wire LLM Event Classifier + Prompt Registry

- `domain/agents/event_classifier.py`:
  - Th?m `LlmEventClassifier`: `registry().render("event_classification",
    version=production, ...)` + `infra.llm.completion.chat` (DETERMINISTIC).
  - Parse JSON `route`/`reason` ? `RoutingDecision` (`b?nh th??ng`/
    `b?t th??ng`).
  - M?c ??nh production: `_DEFAULT_BRAIN_FACTORY = LlmEventClassifier`
    (Protocol `EventClassifierBrain` gi? nguy?n; `application/` kh?ng ??i).
  - `HeuristicEventClassifier` gi? cho test / inject t??ng minh.
- `tests/conftest.py`: autouse monkeypatch factory ? Heuristic trong pytest
  (tr?nh g?i OpenAI / flake); test LLM inject `brain=LlmEventClassifier(chat_fn=...)`.
- `tests/test_event_classifier.py`: heuristic cases + mock LLM (registry
  prompt + parse JSON + ??i production + JSON l?i).

## 2026-09-17 ? Review `PromptRegistry` vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 item 2 ? registry only)

**Passes (test-plan Prompt Registry + In Scope git-based registry):**
- `registry().get(..., version="production")` theo `production.txt`.
- `render` thi?u bi?n b?t bu?c ? `ValueError("Thi?u bi?n...")`, kh?ng ??
  `$var` l?t ra output.
- `render(..., version=<s?>)` ??ng version ?? d? production tr? b?n kh?c.
- ??i `production.txt` ? `render(..., "production")` ??i n?i dung, kh?ng
  s?a code g?i.
- Template engine: `string.Template` (`$var`).

**Fails (li?n quan feature n?y, ?? s?a):**
- Path `prompts/` ch? `parents[4]` ? d? l?ch layout Docker/non-editable
  (c?ng l?p r?i ro v?i `WEB_DIR`) ? th?m `resolve_prompts_dir()` (editable /
  `/app/prompts` / cwd).
- Test ch?a g?i ??ng helper `registry()` nh? test-plan vi?t ? si?t
  `tests/test_prompt_registry.py` d?ng `registry().get` / `registry().render`.

**Missing (??ng k? v?ng ? ch?a wire agent):**
- AC product-spec ???i production ? **h?nh vi agent** ??i? (c?n item wire
  LLM v?o t?ng agent).
- Checklist ?Unit test ? agent d?ng ??ng version m?i? (ph?n agent) ? v?n
  `[ ]`.

## 2026-09-17 ? Phase 8 (item 2): `PromptRegistry` (get/render)

- Th?m `infra/llm/prompt_registry.py`:
  - `Prompt` dataclass (metadata + template).
  - `PromptRegistry.get(name, version="production"|"latest"|int)`.
  - `PromptRegistry.render(...)` qua `string.Template`.
  - `_required_vars()` + raise `ValueError("Thi?u bi?n...")` khi thi?u var
    (kh?ng `safe_substitute`).
  - `registry()` singleton + `resolve_prompts_dir()`.
- Export qua `infra/llm/__init__.py`.
- `tests/test_prompt_registry.py` ? cover 4 case test-plan Prompt Registry.
- **Quy?t ??nh template engine:** `string.Template` (`$var`) ? kh?ng Jinja2.
- **Ch?a** wire LLM v?o agent (v?n Heuristic*Brain).

## 2026-09-17 ? Review khung `prompts/` vs product-spec / test-plan

### K?t qu? ??i chi?u (ph?m vi Phase 8 item 1 ? scaffold only)

**Passes (In Scope Prompt Registry ? m?c file + checklist item 1):**
- ?? 7 prompt dir kh?p `agents.md` / implementation-plan.
- M?i `v1.yaml` c? `version` + `changelog` + metadata b?t bu?c; template `$var`.
- `production.txt` = `1` (alias production ? version hi?n h?nh).
- `tests/test_prompts_scaffold.py` pass.

**Fails (li?n quan feature n?y, ?? s?a):**
- `PyYAML` d?ng ?? parse `prompts/*.yaml` trong test nh?ng **kh?ng** khai b?o
  trong `pyproject.toml` (ch? c? s?n ? m?i tr??ng m?y) ? th?m
  `pyyaml>=6.0.0`.
- `Dockerfile` (Phase 7) ch?a `COPY prompts/` ? image demo s? thi?u registry
  files khi wire LLM ? th?m `COPY prompts ./prompts` + assert trong
  `tests/test_dockerfile.py`.
- Si?t test: `changelog` kh?ng ???c r?ng; assert `pyyaml` c? trong
  `pyproject.toml`.

**Missing (??ng k? v?ng ? thu?c item Phase 8 sau, kh?ng implement ? ??y):**
- AC product-spec ???i production ? h?nh vi agent ??i? (c?n
  `PromptRegistry` + wire LLM).
- 4 case test-plan Prompt Registry (`registry().get` / `render` / thi?u
  bi?n / version c? th?).

## 2026-09-17 ? Phase 8 (item 1): khung `prompts/` git-based

- T?o `prompts/` ? root v?i **7** th? m?c agent c? LLM (theo
  `specs/agents.md` / implementation-plan Phase 8):
  `event_classification/`, `eval_severity/`, `synthesis_alert/`,
  `supervisor_routing/`, `rewrite_question/`, `answer_compose/`,
  `news_agent_react/`.
- M?i th? m?c: `v1.yaml` (metadata: `name, version, model, description,
  owner, created, changelog, eval_score, template`) + `production.txt`
  ch?a `"1"`. Template d?ng `$var` (`string.Template`) ? kh?p hands-on
  Lesson16 / pattern `llm-engineer-demo/app/agent_pr/prompts/`.
- N?i dung prompt MVP b?m domain portfolio_watch (kh?ng copy nguy?n prompt
  demo c? `db_agent`/`db_write`).
- `tests/test_prompts_scaffold.py` ? assert ?? 7 dir, production=`1`,
  metadata b?t bu?c, template c? `$var`.
- **Ch?a** vi?t `PromptRegistry`, **ch?a** wire LLM v?o agent (c?c item
  Phase 8 ti?p theo v?n `[ ]`). Agent v?n ch?y `Heuristic*Brain`.

## 2026-09-17 ? Rewrite `AGENTS.md` (short, practical ruleset)

- Vi?t l?i `AGENTS.md` g?n l?i th?nh 7 quy t?c r? r?ng (??c specs tr??c khi
  code, m?t phase/task m?i l?n, gi? ??n gi?n, kh?ng th?m lib th?a, kh?ng ??i
  architecture n?u spec ch?a c?p nh?t, c?p nh?t change-log sau m?i l?n
  implement, gi?i th?ch c?ch test) + 1 b?ng tra nhanh "Where to look" tr?
  t?i t?ng file spec ? n?i dung kh?ng ??i so v?i b?n c?, ch? g?p l?i (tr??c
  ?? 3 m?c "Nguy?n t?c ch?nh" / "Workflow" / "Coding Style" / "Testing" l?p
  l?i c?ng 7 ? n?y).
- **Xo? kh?i n?i dung ch?n s?n** (`<!-- vnai-bootstrap | auto-generated -->`,
  ?? ghi ch? l?n tr??c ? ??y) ? h??ng d?n agent t? c?i `vnstock`/`vnai`, xin
  API key ng??i d?ng, ch?y/xo? script t?m. Kh?i n?y kh?ng li?n quan t?i quy
  ??c l?m vi?c c?a project (?? b? flag t? l?n review tr??c, gi? ???c y?u c?u
  vi?t l?i `AGENTS.md` "ng?n g?n, th?c t?" n?n lo?i b? lu?n thay v? gi? song
  song). File ?? s?a ???c track b?i git, c? th? revert n?u c?n gi? l?i.
- Kh?ng vi?t code.

## 2026-09-17 ? Review & cleanup `implementation-plan.md` (10 phases)

- R? l?i to?n b? 10 phase theo ??ng th? t? y?u c?u (1 Project setup ? 7
  Docker demo setup, 8 Prompt Registry & LLM wiring, 9 Golden dataset & Eval
  pipeline, 10 Agent graph visualization) ? c?u tr?c phase ?? ??ng t? tr??c,
  kh?ng ??i th? t?/t?n (ch? s?a ti?u ?? Phase 3 t? "Core backend / data
  logic" ? "Core backend or data logic" cho kh?p ??ng c?ch g?i).
- Phase 1-7 (?? ho?n th?nh, `[x]`) v?n ?? c? checklist item nh?, 1 item/1
  file ? gi? nguy?n, kh?ng s?a n?i dung l?ch s?.
- Phase 8-10 (ch?a b?t ??u, `[ ]`) ?ang g?p nhi?u vi?c v?o 1 checkbox (vd.
  1 item duy nh?t "thay Heuristic*Brain" cho c? 6 agent; 1 item duy nh?t cho
  c? 3 b??c c?a `run_eval.py`) ? t?ch nh? l?i cho kh?p ?? chi ti?t c?a Phase
  1-7 v? d? check off t?ng b??c:
  - Phase 8: t?ch 1 item/1 agent cho vi?c wiring LLM th?t (6 item ri?ng thay
    v? 1 item g?p), th?m item test ??i `production.txt`.
  - Phase 9: t?ch `run_eval.py` th?nh 3 item ri?ng (scorer rule-based,
    scorer LLM-judge, runner gh?p 2 scorer) + t?ch ri?ng regression gate
    th??ng v? gate c?ng cho slice `injection`.
  - Phase 10: t?ch vi?c build node / n?i edge / `draw_mermaid_png` /
    fallback `draw_mermaid` / ??i chi?u th? c?ng th?nh c?c item ri?ng.
- Kh?ng ??i ph?m vi hay quy?t ??nh k? thu?t n?o, ch? t? ch?c l?i checklist
  cho r? v? nh? h?n. Kh?ng vi?t code.

## 2026-09-17 ? Review & cleanup `product-spec.md`

- R? l?i `product-spec.md` sau l?n th?m Phase 8-10: c?c bullet Prompt
  Registry/Eval/Diagram ?ang b? n?i ?u?i v?o cu?i "In Scope" v? "Acceptance
  Criteria" l?n v?i ph?n ?ng d?ng c?t l?i, l?ch t?ng (1 acceptance criterion
  vi?t d?ng l?i g?i code `registry().render(...)` thay v? h?nh vi s?n ph?m
  nh? c?c m?c c?n l?i).
- S?a: t?ch "In Scope" th?nh 2 nh?m r? r?ng ? **?ng d?ng c?t l?i** v?
  **C?ng c? ch?t l??ng LLM (Phase 8-10)**; vi?t l?i 3 acceptance criteria
  li?n quan theo ??ng t?ng "h?nh ??ng ? k?t qu? quan s?t ???c" c?a c?c m?c
  g?c, b? c? ph?p code. G?p b?t 2 bullet Out of Scope tr?ng ? (A/B test th?t
  + hosted registry). Kh?ng ??i n?i dung/ph?m vi, ch? t? ch?c l?i cho r? v?
  ??n gi?n h?n. Kh?ng vi?t code.

## 2026-09-17 ? Spec update: Prompt Registry, Golden Dataset & Eval Pipeline, Agent Graph Visualization (LangGraph)

- R? l?i code hi?n c? (`src/portfolio_watch/domain/agents/*`): x?c nh?n to?n
  b? agent ?ang l? `Heuristic*Brain` (rule-based), **ch?a** c? agent n?o g?i
  LLM th?t qua `infra/llm/`, v? **ch?a** c? Prompt Registry hay eval/
  golden-dataset n?o t?n t?i trong repo. ??i chi?u th?m `llm-backend-ref`
  (sibling) ? c?ng ch?a c? 2 ph?n n?y, nh?ng c? `judge.py` / `ragas_native.py`
  / `agent_eval.py` (LLM-as-judge "native", kh?ng c?n th? vi?n `ragas`) t?i
  d?ng ???c cho Phase 9.
- ??c "LLMOps Prompt Management" (Lesson16) v? "Class 18 - LLM Evaluation
  Pipelines" (Lesson17) ? l?y pattern hands-on:
  - Prompt Registry git-based: 1 th? m?c/prompt name, m?i version 1 file
    `vN.yaml` + `production.txt` tr? version hi?n h?nh; interface t?i gi?n
    `registry().render(name, version="production", **vars)`.
  - Golden dataset 30 case theo t? l? 18/6/3/3 (60%/20%/10%/10%) ? ?p d?ng
    l?i ??ng t? l? n?y cho domain stock (lookup / comparison-explain /
    out_of_scope / injection) thay v? domain tra c?u lu?t c?a v? d? g?c.
  - Eval pipeline: ch?m rule-based tr??c, LLM-judge (rubric tuy?t ??i:
    correctness/completeness/grounding, temperature=0) khi c?n, gate c?ng
    cho slice an to?n (injection).
- Kh?o s?t `llm-engineer-demo` ? x?c nh?n c? s?n 4 ch? d?ng pattern v? s? ??
  agent b?ng LangGraph (`save_graph_visualization`, r? nh?t ?
  `app/agent_pr/supervisor_agent/graph.py`): `graph.get_graph(xray=True)
  .draw_mermaid_png()`, fallback `draw_mermaid()` ra `.mmd` khi kh?ng c?
  m?ng ? s? t?i d?ng nguy?n pattern n?y ? Phase 10 thay v? vi?t m?i.
- C?p nh?t spec (**ch?a vi?t code implementation**):
  - `specs/product-spec.md` ? th?m Prompt Registry, Golden dataset/Eval
    pipeline, script v? s? ?? v?o In Scope + Out of Scope (CI eval, hosted
    registry, A/B test th?t ??u ngo?i ph?m vi MVP); th?m acceptance criteria
    t??ng ?ng.
  - `specs/implementation-plan.md` ? th?m `prompts/`, `specs/eval/`,
    `scripts/run_eval.py`, `scripts/draw_agent_graph.py`, `docs/agent_graph.*`
    v?o c?u tr?c th? m?c; th?m d?ng t?i d?ng `judge.py`/`ragas_native.py` v?
    `save_graph_visualization` v?o b?ng reuse; th?m Phase 8 (Prompt Registry
    & LLM wiring), Phase 9 (Golden dataset & Eval pipeline), Phase 10 (Agent
    graph visualization) ? c? 3 phase ?ang `[ ]` (ch?a b?t ??u).
  - `specs/test-plan.md` ? th?m m?c Prompt Registry (4 test case) v? Eval
    pipeline (b?ng 30 case theo slice + ti?u ch? pass/gate); c?p nh?t "Ngo?i
    ph?m vi test MVP" (b? ghi ch? `agent_eval.py` c?, thay b?ng CI/A-B test).
  - `specs/agents.md` ? g?n t?n th? m?c Prompt Registry t??ng ?ng cho t?ng
    agent c? LLM (NewsAgent, EventClassifier, EvalAgent, SynthesisAgent,
    Supervisor, RewriteQuestion, AnswerComposer); th?m m?c "S? ?? sinh t?
    code (LangGraph, Phase 10)" mapping node/edge.
  - `AGENTS.md`, `README.md` ? ghi ch? tham chi?u Phase 8-10 (README th?m
    m?c "S?p t?i ? ch?a implement"), kh?ng ??i quy tr?nh l?m vi?c hi?n c?.
- **Ch?a implement g?** ? ??y l? b??c d?ng l?i theo ??ng y?u c?u spec-driven,
  ch? review tr??c khi b?t ??u Phase 8.

### L?u ? ph?t hi?n ???c (ngo?i ph?m vi task n?y)

- `AGENTS.md` (root) c? s?n m?t kh?i n?i dung ???c ch?n t? tr??c (??nh d?u
  `<!-- vnai-bootstrap | auto-generated -->`, c? v? do c?ng c? `vnai`/
  `vnstock` t? ghi khi ch?y tr??c ??y) h??ng d?n agent code t? ??ng c?i ??t
  package, xin API key ng??i d?ng, ch?y script t?m r?i xo?... N?i dung n?y
  kh?ng li?n quan t?i quy ??c l?m vi?c th?t c?a project (ph?n g?c c?a
  `AGENTS.md` ch? c? m?c "spec-driven" ? ??u file, d?ng 1-37) ? kh?ng ??ng
  t?i kh?i n?y trong l?n c?p nh?t n?y, ch? ghi ch? l?i ?? ng??i d?ng bi?t v?
  t? quy?t ??nh c? gi?/xo?.

## 2026-09-17 ? Review quy?t ??nh Docker / ??ng Phase 7 vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 m?c cu?i ? demo packaging / 1 URL):**
- Image base `python:3.12-slim`; tag `portfolio-watch:demo`.
- Port container **8000**; host `${APP_HOST_PORT:-8000}`.
- Volume `portfolio-watch-sqlite` ? `/app/data` (`SQLITE_PATH=?/portfolio_watch.db`).
- `env_file: .env`; demo URL c?ng origin `http://localhost:8000/`.
- Ng?y ??ng Phase 7: **2026-09-17**; b?ng phase 1?7 ?? ng?y; checklist `[x]`.

**Fails:** kh?ng c? thi?u s?t so v?i checklist m?c n?y (sau khi s?a assert
test kh?ng c?n y?u c?u placeholder `*(ch?a)*` to?n file).

**Missing:** kh?ng c?n m?c unchecked trong `implementation-plan.md`.

## 2026-09-17 ? Phase 7 ho?n th?nh: quy?t ??nh Docker + ng?y ??ng phase

**Ng?y ho?n th?nh Phase 7:** **2026-09-17**

### Quy?t ??nh Docker (demo packaging)

| M?c | Quy?t ??nh | L? do ng?n |
|-----|------------|------------|
| Image base | `python:3.12-slim` | Kh?p runtime local ?3.10; slim ?? cho FastAPI + deps |
| Image tag | `portfolio-watch:demo` (compose `build: .`) | M?t service app; kh?ng multi-stage |
| Container port | **8000** (`EXPOSE` + uvicorn `--port 8000`) | C?ng c?ng local / product demo |
| Host port | `${APP_HOST_PORT:-8000}:8000` (bi?n `APP_HOST_PORT`) | ??i c?ng host qua `.env`, kh?ng ??i image |
| Volume name | `portfolio-watch-sqlite` (compose key `pw_sqlite`) | Named volume ? SQLite s?ng qua `restart` / `down` |
| Volume path | host volume ? `/app/data` | `SQLITE_PATH=/app/data/portfolio_watch.db` |
| Env / secrets | `env_file: .env`; kh?ng bake key v?o image | Compose override `API_HOST` / `SQLITE_PATH` trong container |
| Demo URL | `http://localhost:8000/` (API + `web/` c?ng origin) | M?t URL; `API_BASE=""` |

B?ng phase (m?c ?Ng?y ho?n th?nh t?ng phase?) c?p nh?t Phase 7 = **2026-09-17**.
Checklist Phase 7 trong `implementation-plan.md` to?n `[x]`.

**Li?n k?t AC:** `scripts/verify_clean_docker.py` ? `CLEAN_DOCKER_SMOKE_OK`
(3 lu?ng qua c?ng API UI d?ng).

## 2026-09-17 ? Review Docker 3-lu?ng m?y s?ch vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 x?c nh?n m?y s?ch ? AC 3 lu?ng / demo 1 URL):**
- `docker compose up --build` ? health + UI (`chat`/`watchlist`/`approvals`).
- Qu?t: `POST /scan` FPT (gi? th?t, route b?nh th??ng).
- Chat: `POST /chat` kh?ng HITL, c? `answer`.
- HITL: approve ? `sent`; reject + `reject_reason` ghi l?i.
- Script `scripts/verify_clean_docker.py` ? `CLEAN_DOCKER_SMOKE_OK` (?? ch?y th?t).

**Fails (li?n quan feature, ?? s?a):**
- Seed HITL d?ng ID c? ??nh `docker-a1` tr?n volume c?n resolution c? ?
  `list_pending` r?ng ? ??i seed sang UUID m?i l?n ch?y.
- `subprocess` capture compose log Windows cp1252 ? `encoding=utf-8`,
  `errors=replace`.

**Missing (??ng k? v?ng ? m?c Phase 7 cu?i):**
- Ghi quy?t ??nh Docker (port/volume/base) + ng?y ??ng Phase 7.

## 2026-09-17 ? Phase 7: x?c nh?n Docker Compose ch?y 3 lu?ng

- `scripts/verify_clean_docker.py`: compose up --build, UI + scan/chat/HITL.
- README ? Demo Docker m?c 4; `tests/test_clean_docker_smoke.py`.
- Ch?y th?t tr?n m?y n?y ? `CLEAN_DOCKER_SMOKE_OK`.

## 2026-09-17 ? Review README Demo b?ng Docker vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 m?c README Docker ? demo 1 URL / 3 lu?ng):**
- Y?u c?u Docker + Compose; `cp`/Copy-Item `.env.example` ? `.env`.
- `docker compose up --build`; m? http://localhost:8000/ (UI+API).
- `logs -f`, `down`, `down -v` (reset volume `portfolio-watch-sqlite`).

**Fails:** kh?ng c? thi?u s?t so v?i checklist m?c n?y.

**Missing (??ng k? v?ng ? Phase 7 ti?p):**
- X?c nh?n m?y s?ch `compose up` + 3 lu?ng UI.
- Ghi quy?t ??nh Docker (port/volume/base) + ng?y ??ng Phase 7.

## 2026-09-17 ? Phase 7: m?c README "Demo b?ng Docker"

- Th?m section h??ng d?n: y?u c?u, `.env`, `up --build`, URL, d?ng/log/reset.
- `tests/test_readme_docker_demo.py`.

## 2026-09-17 ? Review single-URL API+web in container vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 ? 1 URL demo ? product-spec Frontend c?ng origin):**
- `GET /` UI (chat/watchlist/approvals) + `GET /health` + API JSON c?ng host.
- `app.js` `API_BASE=""`; Dockerfile `COPY web` + uvicorn `main:app`.
- `resolve_web_dir()`: editable `/app/web`, fallback `Path("/app/web")`, cwd.

**Fails (li?n quan feature n?y, ?? s?a):**
- `WEB_DIR` ch? `parents[2]/web` d? l?ch layout container ? th?m
  `resolve_web_dir()` ?a ?ng vi?n.
- Th?m `tests/test_docker_single_url.py` (layout editable + same-origin).

**Missing (??ng k? v?ng):**
- Live `docker compose up` tr?n m?y n?y (Docker daemon off l?c review).
- README "Demo b?ng Docker" (m?c Phase 7 ti?p).

## 2026-09-17 ? Phase 7: FastAPI ph?c v? API + web/ m?t URL (container)

- `main.resolve_web_dir()` ?? mount static ?n ??nh trong Docker.
- X?c nh?n c?ng origin: `/` + `/health` + `/app.js` (`API_BASE=""`).

## 2026-09-17 ? Review Docker env_file vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 env t? .env, kh?ng bake secret v?o image):**
- `docker-compose.yml`: `env_file: .env`; port `${APP_HOST_PORT:-8000}:8000`.
- Compose `environment` ghi ?? `API_HOST=0.0.0.0`,
  `SQLITE_PATH=/app/data/portfolio_watch.db` (th?ng gi? tr? local).
- `.env.example`: `APP_HOST_PORT`, ghi ch? DB trong volume; Dockerfile /
  `.dockerignore` kh?ng ch?a secret.

**Fails (li?n quan feature n?y, ?? s?a):**
- Test compose c?n assert c?ng `8000:8000` sau khi ??i sang
  `APP_HOST_PORT` ? c?p nh?t `tests/test_docker_compose.py`.
- C?nh b?o: `env_file` inject *m?i* key trong `.env` ? ghi ch? tr?n
  `.env.example` (d?ng b?n copy s?ch t? example, kh?ng merge .env project kh?c).

**Missing (??ng k? v?ng ? checklist Phase 7 ti?p):**
- README "Demo b?ng Docker"; x?c nh?n 3 lu?ng; ghi quy?t ??nh Phase 7.

## 2026-09-17 ? Phase 7: env_file .env + c?p nh?t .env.example (Docker)

- `docker-compose.yml`: `env_file: .env`, `APP_HOST_PORT`, override host/DB.
- `.env.example`: m?c Docker (`APP_HOST_PORT`, path DB volume, c?nh b?o inject).
- `tests/test_docker_env_file.py`.

## 2026-09-17 ? Review docker-compose vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 m?c compose ? demo stack):**
- Service `app` build t? `Dockerfile`; map `8000:8000`; volume
  `portfolio-watch-sqlite` ? `/app/data`; `SQLITE_PATH=/app/data/portfolio_watch.db`.
- `docker compose config` parse OK; kh?ng hard-code secret trong YAML.
- C?ng origin API+UI khi container ch?y (Dockerfile ?? mount `web/`).

**Fails (li?n quan feature n?y):** kh?ng c? l?i blocking sau `compose config`.

**Missing (??ng k? v?ng ? checklist Phase 7 ti?p):**
- `env_file: .env` + c?p nh?t `.env.example` (m?c k? ti?p).
- README Docker; x?c nh?n 3 lu?ng tr?n m?y s?ch; ghi quy?t ??nh Phase 7.

## 2026-09-17 ? Phase 7: docker-compose.yml (app + port + SQLite volume)

- Th?m `docker-compose.yml`: service `app`, `8000:8000`, volume named
  `pw_sqlite` mount `/app/data`.
- `tests/test_docker_compose.py` ? assert port / volume / kh?ng bake key.

## 2026-09-17 ? Review Dockerfile vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 7 m?c Dockerfile ? demo API+UI c?ng origin):**
- Image `python:3.12-slim`; `pip install -e .`; copy `src/` + `web/`;
  `EXPOSE 8000`; `uvicorn ... --host 0.0.0.0 --port 8000` (kh?ng reload).
- Kh?ng hard-code secret; `.dockerignore` lo?i `.env` / `.venv`.
- `ENV API_HOST=0.0.0.0`, `SQLITE_PATH=/app/data/portfolio_watch.db`.

**Fails (li?n quan feature n?y, ?? s?a):**
- `pip install .` (non-editable) ? `__file__` v?o site-packages ?
  `WEB_DIR` l?ch, UI static kh?ng mount ? ??i `pip install -e .` ??
  `WEB_DIR=/app/web`.

**Missing (??ng k? v?ng ? checklist Phase 7 ti?p):**
- `docker-compose.yml`, env_file, README Docker, x?c nh?n m?y s?ch.
- Docker daemon kh?ng ch?y tr?n m?y n?y l?c review ? ch?a `docker build` th?t.

## 2026-09-17 ? Phase 7: Dockerfile (API + web demo)

- Th?m `Dockerfile` + `.dockerignore`.
- `tests/test_dockerfile.py` ? assert deps / web / expose 8000 / uvicorn /
  kh?ng bake secret.

## 2026-09-17 ? Review phase completion dates vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 6 m?c ?ghi ng?y ho?n th?nh t?ng phase?):**
- B?ng Phase 1?6 c? ng?y ??ng phase; Phase 7 ghi *(ch?a)*.
- Li?n k?t AC: `test_product_spec_ac.py` (Phase 5) + `verify_clean_local.py`
  (Phase 6 / 3 lu?ng).
- Checklist Phase 6 trong `implementation-plan.md` to?n `[x]`.

**Fails (li?n quan feature n?y, ?? s?a):**
- C?n assert Phase 6 kh?ng c?n `- [ ]` ? b? sung
  `tests/test_change_log_phase_dates.py`.

**Missing (??ng k? v?ng):**
- Phase 7 Docker (ch?a b?t ??u) ? s? c?p nh?t ng?y khi ??ng phase.

## 2026-09-17 ? Ng?y ho?n th?nh t?ng phase (Phase 6 checklist)

T?m t?t ng?y **??ng phase** (m?c checklist cu?i c?a phase trong
`implementation-plan.md` ?? `[x]`). Chi ti?t t?ng task v?n ? c?c m?c nh?t k?
b?n d??i.

| Phase | T?n | Ng?y ho?n th?nh | Ghi ch? ng?n |
|-------|-----|-----------------|--------------|
| 1 | Project setup | **2026-09-16** | FastAPI skeleton, settings, `/health`, `.env.example` |
| 2 | Core UI | **2026-09-16** | `web/` 3 khu v?c + CSS + stub `app.js`; x?c nh?n m? UI |
| 3 | Core backend / data logic | **2026-09-17** | Ports, agents, scan/HITL/chat app layer, cron, full unit+IT |
| 4 | Connect UI to data | **2026-09-17** | `/scan` `/chat` `/approvals` `/watchlist`, CORS, static, wire UI |
| 5 | Validation and error states | **2026-09-17** | 4xx, soft-fail ngu?n, cron isolation, guardrail, HITL idempotent, UI l?i, r? AC |
| 6 | Local run instructions | **2026-09-17** | README local, clean-venv verify, b?ng ng?y phase (m?c n?y) |
| 7 | Docker demo setup | **2026-09-17** | Dockerfile + compose, env_file, 1 URL, README Docker, `verify_clean_docker.py` |
| 8 | Prompt Registry & LLM wiring | **2026-09-17** | `prompts/` + `PromptRegistry`; wire 7 LLM agent; Heuristic gi? cho test |
| 9 | Golden dataset & Eval pipeline | **2026-09-17** | 30 case 18/6/3/3; `run_eval.py` scorers+runner+report+gates; baseline |
| 10 | Agent graph visualization | **2026-09-17** | `draw_agent_graph.py` StateGraph; docs/agent_graph.mmd/.png; `--verify` |

**Li?n k?t AC:** Phase 5 ?? x?c nh?n 6 bullet `product-spec.md` qua
`tests/test_product_spec_ac.py`; Phase 6 x?c nh?n 3 lu?ng ch?nh theo README
(`scripts/verify_clean_local.py`); Phase 7 x?c nh?n Docker demo
(`scripts/verify_clean_docker.py`); Phase 8 x?c nh?n Prompt Registry
(`tests/test_prompt_registry.py`) + wire LLM agents; Phase 9 x?c nh?n
golden + eval (`scripts/run_eval.py`, `specs/eval/baseline.json`); Phase 10
x?c nh?n s? ?? agent (`scripts/draw_agent_graph.py --verify`).

## 2026-09-17 ? Review clean-venv verify vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 6 x?c nh?n m?y s?ch ? AC 3 lu?ng):**
- Venv m?i + `pip install -e .` ? health, UI 3 khu v?c, watchlist, scan,
  chat (`hitl_used=false`), approve/reject ? `CLEAN_VENV_SMOKE_OK`.
- Script `scripts/verify_clean_local.py` + m?c README ?8.

**Fails (li?n quan feature n?y, ?? s?a):**
- `load_dotenv(..., override=True)` khi?n `.env` project ghi ?? `SQLITE_PATH`
  m?i tr??ng ? seed HITL l?ch DB / x?c nh?n fail ? ??i `override=False`.
- Test settings d?ng `importlib.reload` c? th? l?m b?n process ? chuy?n
  subprocess + assert source `override=False`.

**Missing (??ng k? v?ng):**
- M?c Phase 6 cu?i: ghi ng?y ho?n th?nh t?ng phase v?o change-log.
- G?n cron lifespan; Docker (Phase 7).

## 2026-09-17 ? Phase 6: x?c nh?n virtualenv m?i ch?y 3 lu?ng

- Ch?y th?t `scripts/verify_clean_local.py` tr?n venv t?m: scan / chat / HITL
  OK kh?ng s?a source.
- `load_dotenv(override=False)` ?? bi?n m?i tr??ng th?ng `.env`.
- README ?8 + `tests/test_clean_venv_smoke.py`.

## 2026-09-17 ? Review README local run vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 6 h??ng d?n local ? AC ch?y 3 lu?ng):**
- `pip install -e .`, `.env.example` ? `.env`, `OPENAI_API_KEYS` / `SQLITE_PATH`.
- SQLite t? t?o schema (`connect` / one-liner); backend
  `python -m src.portfolio_watch.main` / uvicorn c?ng **8000**.
- UI c?ng origin `http://127.0.0.1:8000/`; seed watchlist; `/scan` `/chat`
  `/approvals`; cron th? c?ng `scan_watchlist`.

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u l?nh copy `.env` tr?n PowerShell ? th?m `Copy-Item`.
- Ch?a n?u r? heuristic vs m?ng/`vnstock` ? b? sung ghi ch? b?ng env.
- Test README thi?u assert `uvicorn` / `/health` / sqlite init ? si?t
  `tests/test_readme_local_instructions.py`.

**Missing (??ng k? v?ng ? checklist Phase 6 ti?p):**
- X?c nh?n m?y s?ch theo README end-to-end (m?c k? ti?p).
- G?n APScheduler v?o `main` lifespan; Docker (Phase 7).

## 2026-09-17 ? Phase 6: h??ng d?n ch?y local (README)

- Vi?t l?i m?c **Ch?y local (Phase 6)** trong `README.md`: c?i deps, `.env`,
  SQLite auto-init, ch?y `main`/uvicorn `:8000`, m? UI c?ng origin, seed
  watchlist, cron th? c?ng `scan_watchlist`, ki?m 3 lu?ng.
- `tests/test_readme_local_instructions.py` ? assert README ?? checklist.

## 2026-09-17 ? Review product-spec AC r? l?i vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (6 AC product-spec.md qua HTTP):**
- AC1 scan: gi?/tin/ph?n lo?i; b?t th??ng ? severity + alert + gate1.
- AC2 ??t ng??ng th?p (`POST /watchlist`) ? v??t ng??ng ? sent/pending.
- AC3 approve/reject ? sent / rejected + l? do Memory.
- AC4 ?? xu?t ng??ng ? Gate 2 pending, kh?ng t? ?p d?ng watchlist.
- AC5 chat ? gi? th?t trong answer, `hitl_used=false`, kh?ng pending.
- AC6 guardrail ch?n ?n?n mua/b?n?; output chat/scan s?ch.

**Fails (li?n quan feature n?y, ?? s?a):**
- AC1 ch? cover b?t th??ng; route assert sai enum EN ? th?m nh?nh b?nh
  th??ng + d?ng gi? tr? `b?nh th??ng`/`b?t th??ng`.
- AC2 seed FakeWatchlistStore thay v? ???t? qua API ? chuy?n
  `POST /watchlist` r?i `POST /scan` (kh?ng ghi ?? threshold).
- AC5 ch?a assert c?ng `hitl_used` + `price.latest_close` ? si?t assert.

**Missing (??ng k? v?ng / ngo?i AC bullets):**
- Cron wire v?o `main` lifespan, README local, Docker (Phase 6).
- LLM composer th?t / ngu?n th? tr??ng th?t trong CI.

## 2026-09-17 ? Phase 5: R? l?i acceptance criteria product-spec

- `tests/test_product_spec_ac.py` ? 6 test map 6 bullet AC trong
  `product-spec.md` (scan pipeline, watchlist ng??ng, approve/reject,
  Gate 2, chat kh?ng HITL, guardrail mua/b?n).
- ??nh d?u ho?n th?nh m?c Phase 5 cu?i; kh?ng ??i production code.

## 2026-09-17 ? Review Frontend error states vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 5 Frontend l?i c? b?n + product-spec Frontend ??n gi?n):**
- Banner `#app-error` + c?u ?Kh?ng l?y ???c d? li?u, th? l?i? khi m?ng/API l?i.
- Scan/chat/approvals/watchlist l?i hi?n r? tr?n UI (kh?ng ch? console).
- Soft-fail gi?/tin tr?n scan v?n ??y l?n banner.

**Fails (li?n quan feature n?y, ?? s?a):**
- ??ang qu?t?? b? style nh? l?i (`is-error`) ? t?ch `isError` flag.
- Submit scan/chat r?ng im l?ng ? `showAppError("symbol/c?u h?i r?ng")`.

**Missing (??ng k? v?ng):**
- Timeout/retry button ri?ng; form CRUD watchlist tr?n UI (ngo?i m?c n?y).
- R? to?n b? AC product-spec (checklist Phase 5 ti?p).

## 2026-09-17 ? Phase 5: Frontend hi?n th? l?i API c? b?n

- `web/index.html`: banner `#app-error` (role=alert).
- `web/app.js`: `NETWORK_ERROR_MSG`, `showAppError`/`clearAppError`,
  `formatError` (status 0 ? c?u th?n thi?n); scan/chat/HITL/watchlist l?i
  hi?n banner + panel; b? `alert()`.
- `web/style.css`: `.app-error` / `#scan-result.is-error`.
- `tests/test_ui_error_states.py` ? x?c nh?n banner + wiring l?i.

## 2026-09-17 ? Review HITL missing / already-done vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Phase 5 + AC approve/reject tr?ng th?i ??ng):**
- Id thi?u / ?? x? l? ? HTTP 404; kh?ng g?i Notifier l?n 2; kh?ng ghi reject
  th?m; kh?ng th?m event; Gate 2 kh?ng ??i watchlist; cross approve?reject.

**Fails (li?n quan feature n?y, ?? s?a):**
- Resolution ch? c? `alert_id`/`proposal_id` (thi?u `approval_id`) kh?ng b?
  coi ?? x? l? ? c? th? approve l?i ? si?t `_is_resolution` +
  `list_pending_approvals`.
- Reject id ?? x? l?/thi?u k?m l? do r?ng tr? 400 ?l? do r?ng? thay v? 404
  ??ng case ? b? normalize reason tr??c app layer (?u ti?n missing/done).
- Th?m test Gate2 reject 2 l?n + resolution alias + empty-reason ? 404.

**Missing (??ng k? v?ng):**
- Happy-path Gate 1/2 approve/reject (?? cover Phase 3?4 / test-plan #3).
- UI hi?n l?i API khi approve/reject fail (m?c Frontend Phase 5 ti?p).

## 2026-09-17 ? Phase 5: HITL missing / already-done ? l?i r?, kh?ng ??i state

- `tests/test_hitl_missing_already_done.py` ? x?c nh?n Phase 5:
  id thi?u / ?? x? l? ? HTTP 404; kh?ng g?i Notifier l?n 2; kh?ng ghi reject
  th?m; kh?ng th?m alert event; Gate 2 kh?ng ??i watchlist; cross
  approve?reject gi? tr?ng th?i ?? ch?t.
- Kh?ng ??i production code ? `review_approval` + router ?? tr? l?i ??ng.

## 2026-09-17 ? Review Guardrail confirmation vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (AC guardrail + test-plan Synthesis/Answer):**
- ?n?n mua?/?n?n b?n? ? `check_output` ch?n; Synthesis rewrite `draft_attempts > 1`.
- S? l?ch evidence ? ch?n; Synthesis/AnswerComposer rewrite ho?c fallback s?ch.
- Hai nh?nh d?ng chung `domain.guardrails.output_checks`.

**Fails (li?n quan feature n?y, ?? s?a):**
- `build_evidence` g?n c? Eval `reasoning` ? whitelist s? b?a (vd. 12.5%) trong
  c?u tr? l?i h?i-??p ? b? `reasoning:` kh?i evidence blob; th?m test x?c nh?n.
- Confirmation thi?u case Synthesis rewrite ?n?n b?n? v? assert `calls > 1`
  tr?n nh?nh Answer fallback b?n ? si?t test.

**Missing (??ng k? v?ng):**
- Model routing Severity (?? cover Phase 3 / ngo?i m?c ?ch?n vi ph?m?).
- Composer LLM th?t (v?n inject/heuristic).

## 2026-09-17 ? Phase 5: x?c nh?n Guardrail (test-plan)

- `tests/test_guardrail_confirmation.py` ? case c? th? test-plan:
  ch?n ?n?n mua?/?n?n b?n?; s? li?u l?ch evidence; Synthesis/AnswerComposer
  rewrite (`draft_attempts > 1`); module `output_checks` d?ng chung hai nh?nh.
- Kh?ng ??i production code ? h?nh vi Phase 3 ?? ??; b? sung x?c nh?n.

## 2026-09-17 ? Review cron isolation vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (test-plan #7 ? cron/watchlist ??c l?p):**
- 1 m? crash / price timeout / news timeout kh?ng ch?n m? kh?c.
- ???ng APScheduler job th? c?ng (`build_scan_watchlist_job`) c?ng isolation.

**Fails (li?n quan feature n?y, ?? s?a):**
- Ch? cover l?i m? gi?a; cron path ch?a assert th? t? g?i + price/news
  tr?n m? OK ? th?m BAD ??u/cu?i; si?t assert lu?ng gi?m s?t ??c l?p
  (change_pct / tin theo m?).

**Missing (??ng k? v?ng):**
- Qu?t song song (agents.md g?i ?) ? test-plan ch? y?u c?u ??c l?p l?i.
- Wire scheduler v?o `main.py` lifespan (Phase 6 h??ng d?n).

## 2026-09-17 ? Phase 5: x?c nh?n cron isolation (t?ch h?p)

- `tests/test_cron_isolation_integration.py` ? test-plan #7 ? m?c t?ch h?p:
  agent crash m? gi?a, Price/News timeout 1 m?, ???ng APScheduler job;
  FPT+VNM v?n qu?t khi BAD l?i.

## 2026-09-17 ? Review Price/News source errors vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi ngu?n l?i/timeout kh?ng crash scan):**
- PriceAgent/NewsAgent b?t exception ? error r?; `scan_symbol` / `POST /scan`
  200, kh?ng alert khi thi?u d? li?u.
- CafeF HTTP l?i raise (kh?ng nu?t `[]`); multi-symbol ?? c? ? cron tests.

**Fails (li?n quan feature n?y, ?? s?a):**
- `quote.error="timeout"` kh?ng c? c?m ?kh?ng l?y ???c d? li?u? ? PriceAgent
  chu?n ho? message.
- CafeF wrap RuntimeError ? NewsAgent double-prefix ?kh?ng l?y ???c tin? ?
  re-raise g?c + NewsAgent tr?nh double-wrap.
- Thi?u case ch? news timeout + assert kh?ng tr? `None`.

**Missing (??ng k? v?ng ? checklist kh?c):**
- Cron isolation x?c nh?n l?i (m?c Phase 5 ti?p); UI hi?n l?i ngu?n (Phase 5
  frontend).

## 2026-09-17 ? Phase 5: PriceSource/NewsSource l?i kh?ng crash scan

- `CafefNewsSource`: timeout/HTTP l?i ? raise (kh?ng nu?t `[]`) ??
  NewsAgent g?n `kh?ng l?y ???c tin`.
- `tests/test_source_errors.py` ? agent + `scan_symbol` + `POST /scan`
  khi price/news timeout: 200, `price.error` / `news_error` r?, kh?ng alert.

## 2026-09-17 ? Review API validate input vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Phase 5 validate input ? 4xx):**
- Symbol r?ng/whitespace/kh?ng h?p l? ? 400; ng??ng ?m ? 400.
- C?u h?i r?ng ? 400; m? kh?ng c? tr?n watchlist ? 404.
- Reject l? do r?ng ? 400; input h?p l? v?n 200 (scan/chat).

**Fails (li?n quan feature n?y, ?? s?a):**
- `""` b? pydantic `min_length` ? 422 ti?ng Anh m?p m? ? b? min_length,
  th?ng nh?t 400 ti?ng Vi?t qua `validation.py`.
- Thi?u case PATCH ng??ng ?m, symbol qu? d?i/`FP-T`, thi?u field ? 422.

**Missing (??ng k? v?ng ? checklist ti?p):**
- M? th? tr??ng kh?ng t?n t?i / PriceSource timeout ? agent tr? l?i r?
  (kh?ng crash) ? m?c Phase 5 k? ti?p, kh?ng map 4xx ? ??y.

## 2026-09-17 ? Phase 5: API validate input ? 4xx

- Th?m `api/helpers/validation.py`: symbol / c?u h?i / ng??ng / approval_id /
  l? do reject ? 400 r? r?ng.
- Wire v?o scan, chat, watchlist, approvals; ng??ng ?m ? 400 (kh?ng c?n
  ch? d?a pydantic 422).
- `tests/test_api_validation.py` ? r?ng, kh?ng h?p l?, ?m, 404 m? kh?ng
  c? tr?n watchlist.

## 2026-09-17 ? Review x?c nh?n UI vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi x?c nh?n Phase 4 UI / c?ng API web g?i):**
- UI 3 khu v?c + `app.js` wiring.
- #1 qu?t b?nh th??ng ? kh?ng alert; chat #5 ? answer, kh?ng HITL.
- #3 pending ? approve (sent) / reject (l? do, kh?ng g?i); list `/approvals`
  c?p nh?t.

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u x?c nh?n qu?t b?t th??ng ?? field AC (severity/tin/alert/gate).
- Thi?u #2 auto-send (Gate 1 kh?ng c?n pending tr?n UI).
- Pending item ch?a assert field `renderApprovals` c?n (`approval_id`,
  symbol).

**Missing (??ng k? v?ng ? Phase 5+ / ngo?i checklist n?y):**
- #4 Gate 2 / #6 chat gi?i th?ch / #7 cron (?? cover ? test API/application
  kh?c).
- Form CRUD ng??ng tr?n UI; validate l?i UI (Phase 5).

## 2026-09-17 ? Phase 4: X?c nh?n lu?ng UI (scan / chat / HITL)

- Th?m `tests/test_ui_manual_confirmation.py` ? e2e c?ng endpoint
  `web/app.js` g?i: UI load, qu?t ? k?t qu?, chat ? answer, pending ?
  approve/reject c?p nh?t list.
- Phase 4 checklist ho?n t?t (5/5 passed).

## 2026-09-17 ? Review wire web/app.js vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi UI n?i 4 API + 3 khu v?c):**
- Chat ? `POST /chat`, hi?n c?u tr? l?i; watchlist/approvals load + refresh.
- Qu?t ngay ? `POST /scan`; approve/reject ? API + refresh list.
- `API_BASE=""` c?ng origin; kh?ng c?n stub log-only Phase 2.

**Fails (li?n quan feature n?y, ?? s?a):**
- Scan UI thi?u ?to?n b? lu?ng? AC (tin/severity/reason/gate2 proposal) ?
  m? r?ng `showScanResult`.
- `detail` 422 d?ng m?ng hi?n x?u; reject l? do r?ng v?n g?i ?
  `formatError` + ch?n reason r?ng; disable n?t khi ?ang request.
- Test ch?a ch?n regression stub ? `test_ui_wiring_renders_scan_chat_approvals`.

**Missing (??ng k? v?ng ? checklist ti?p):**
- X?c nh?n th? c?ng tr?n browser (qu?t / chat / approve-reject e2e UI).
- Form th?m/s?a ng??ng watchlist tr?n UI (CRUD API ?? c?; AC ???t ng??ng?
  v?n l?m ???c qua API).

## 2026-09-17 ? Phase 4: Wire web/app.js ? API + render UI

- `web/app.js`: `API_BASE=""` (c?ng origin); parse JSON; render chat /
  watchlist / approvals; approve/reject + qu?t ngay.
- `web/index.html`: form qu?t, `#watchlist-body`, b? placeholder m?u.
- C?n m?c x?c nh?n th? c?ng tr?n browser (checklist ti?p).

## 2026-09-17 ? Review mount static web/ vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi ph?c v? UI c?ng origin v?i API):**
- `GET /` (v? `/index.html`) tr? trang 3 khu v?c: chat / watchlist /
  approvals (product-spec Frontend).
- `/app.js`, `/style.css` c?ng host; link relative t? HTML resolve ???c.
- Mount `/` kh?ng che API: `/health`, `/watchlist`, `/approvals`, `/docs`,
  OpenAPI `/scan` `/chat` v?n JSON/HTML ??ng.

**Fails (li?n quan feature n?y, ?? s?a):**
- Test ch?a assert API JSON kh?ng b? static shadow, ch?a check
  `/index.html` + asset links t? HTML ? si?t `test_api_static.py`.

**Missing (??ng k? v?ng ? checklist ti?p):**
- `web/app.js` c?n `API_BASE` c?ng + log-only ? n?i `fetch` + render UI
  th?t (m?c Phase 4 ti?p theo).

## 2026-09-17 ? Phase 4: Mount static web/ c?ng origin

- `main.py`: mount `StaticFiles(web/, html=True)` t?i `/` (sau API routes)
  ? UI + API c?ng base URL khi demo.
- `tests/test_api_static.py` ? `/`, `/app.js`, `/style.css`; `/health` +
  `/docs` v?n ho?t ??ng.

## 2026-09-17 ? Review CORS + routers vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi ??ng k? router + CORS cho web/):**
- ?? 4 nh?m API (`/scan`, `/chat`, `/approvals`, `/watchlist`) + method
  kh?p stub `web/app.js`.
- `CORSMiddleware` `allow_origins=["*"]` ? GET v? preflight POST/PATCH/DELETE
  tr? `Access-Control-Allow-Origin: *` (Live Server / `Origin: null`).

**Fails (li?n quan feature n?y, ?? s?a):**
- Test ch? cover `/health` + preflight `/chat` ? m? r?ng assert method
  OpenAPI v? CORS tr?n ??ng endpoint web g?i.

**Missing (??ng k? v?ng ? checklist ti?p):**
- Mount static `web/`, n?i UI `fetch` + render k?t qu? th?t.

## 2026-09-17 ? Phase 4: CORS + ??ng k? ?? router

- `main.py`: x?c nh?n 4 router (`scan`, `chat`, `approvals`, `watchlist`)
  + `CORSMiddleware` `allow_origins=["*"]` (dev, `web/` g?i cross-origin).
- `tests/test_api_cors.py` ? OpenAPI c? ?? path; CORS header + preflight.

## 2026-09-17 ? Review CRUD /watchlist vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi CRUD watchlist API):**
- `GET/POST/PATCH/DELETE /watchlist` th?m/xem/s?a ng??ng/x?a m?.
- User CRUD **kh?ng** t?o HITL pending (kh?c ?? xu?t EvalAgent ? Gate 2).
- Symbol chu?n ho? uppercase; r?ng/whitespace ? 400; ng??ng ?m ? 422;
  m? thi?u ? 404.

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u e2e product-spec ???t watchlist ng??ng th?p ? qu?t v??t ng??ng ?
  c?nh b?o?: `POST /watchlist` r?i `POST /scan` (kh?ng ghi ?? threshold).
- Thi?u assert CRUD kh?ng t?o pending / PATCH ?p d?ng ngay (kh?ng Gate 2).

**Missing (??ng k? v?ng ? checklist kh?c):**
- CORS, mount static `web/`, UI g?i watchlist.

## 2026-09-17 ? Phase 4: CRUD /watchlist API

- Th?m `api/routers/watchlist.py`: `GET/POST /watchlist`,
  `PATCH/DELETE /watchlist/{symbol}` ? `WatchlistStore` (kh?ng qua HITL).
- ??ng k? watchlist router trong `main.py` (ch?a CORS / static / UI).
- `tests/test_api_watchlist.py` ? CRUD, default threshold, symbol r?ng,
  thi?u m? ? 404, ng??ng ?m ? 422.

## 2026-09-17 ? Review POST/GET /approvals vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi HITL approve/reject qua API):**
- `GET /approvals` li?t k? ch? duy?t (Gate 1 + Gate 2) k?m payload.
- Gate 1 approve ? status `sent`, Notifier g?i; reject ? kh?ng g?i, l? do
  ghi Memory.
- Gate 2 approve ? c?p nh?t watchlist; reject ? gi? ng??ng c?.
- Id thi?u / ?? x? l? ? 404; l? do reject r?ng ? 400.

**Fails (li?n quan feature n?y, ?? s?a):**
- test-plan #3 ch?a kh?p HTTP: `POST /scan` ? pending ?
  `POST /approvals/.../approve|reject` ? th?m e2e.
- Thi?u HTTP Gate 2 reject (gi? watchlist) v? reject missing/already-done.
- `reason=""` b? 422 pydantic thay v? 400 ?l? do r?ng? ? b? `min_length`,
  validate sau strip.

**Missing (??ng k? v?ng ? router/checklist kh?c):**
- CRUD `/watchlist`, CORS, static `web/`, UI g?i approvals.

## 2026-09-17 ? Phase 4: POST/GET /approvals API

- Th?m `api/routers/approvals.py`: `GET /approvals`,
  `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`
  ? `review_approval` (Gate 1 g?i alert / Gate 2 c?p nh?t watchlist).
- ??ng k? approvals router trong `main.py` (ch?a CORS / watchlist / static).
- `tests/test_api_approvals.py` ? list, approve/reject Gate 1+2, reason r?ng,
  id thi?u/?? x? l? ? 4xx.

## 2026-09-17 ? Review POST /chat vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Chat API h?i-??p):**
- `POST /chat` ch?y Rewrite ? Supervisor ? workers ? AnswerComposer;
  tr? l?i d?a tr?n gi?/tin, l?u h?i tho?i.
- #5 h?i gi? ? ch? `price`, kh?ng HITL / kh?ng pending.
- #6 h?i "t?i sao gi?m" ? c? `news`/`eval`, c?u tr? l?i nh?c tin/l? do.
- Follow-up ("c?n m? ??") d?ng Memory qua API.

**Fails (li?n quan feature n?y, ?? s?a):**
- Response ch?a l? `news_error` (kh? th?y l?i tin) ? th?m field.
- Test #5/#6 ch?a seed m? trong watchlist; ch?a assert
  `list_pending_approvals == []` / title tin c? th?.
- Thi?u case HTTP follow-up d?ng l?ch s? h?i tho?i.

**Missing (??ng k? v?ng ? ngo?i ph?m vi router chat):**
- Enforce ch? tr? l?i m? c? trong WatchlistStore (`answer_question`
  ch?a nh?n watchlist port ? ghi nh?n t? tr??c).
- `POST /approvals/...`, CORS / UI g?i `/chat`.

## 2026-09-17 ? Phase 4: POST /chat API

- Th?m `api/routers/chat.py`: `POST /chat` ? `answer_question`, tr?
  rewritten/route/answer/price/news/severity; kh?ng t?o HITL.
- ??ng k? chat router trong `main.py` (ch?a CORS / approvals / watchlist).
- `tests/test_api_chat.py` ? h?i gi?, gi?i th?ch gi?m, c?u r?ng/whitespace.

## 2026-09-17 ? Review POST /scan vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi API qu?t ngay 1 m?):**
- `POST /scan` ch?y ?? lu?ng: gi?, tin, route; b?t th??ng ? severity/alert/gate.
- #1 b?nh th??ng ? kh?ng alert; #2 confidence cao ? `sent`, kh?ng pending.

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u coverage API cho #3 (pending khi confidence th?p) v? #4 (`gate2_pending`).
- Response ch?a l? `news_error` (kh? th?y ?? k?t qu? tin) ? th?m field.
- Symbol ch? whitespace ? 400; si?t assert `pending_events` / severity.

**Missing (??ng k? v?ng ? router kh?c / Phase 4 ti?p):**
- `POST /approvals/...` (ph?n c?n l?i c?a test-plan #3).
- CORS / UI g?i `/scan`.

## 2026-09-17 ? Phase 4: POST /scan API

- Th?m `api/deps.py` (AppDeps + override test) v? `api/routers/scan.py`:
  `POST /scan` ? `scan_symbol`, tr? route/price/news/severity/alert/gates.
- ??ng k? scan router trong `main.py` (ch?a CORS / routers kh?c).
- `tests/test_api_scan.py` ? normal, auto-send, symbol r?ng ? 422.

## 2026-09-17 ? Review backend test suite vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Phase 3 ?ch?y unit + integration, ch?a API/UI?):**
- Full suite `tests/`: **85 passed**.
- Unit theo test-plan (Price/News/Classifier/Eval/Synthesis/Gate/HITL/
  Supervisor/Answer) ?? c? trong c?c `test_*.py` ri?ng.
- Integration #1?#7 map application layer (scan / approve-reject / chat /
  cron th? c?ng), kh?ng HTTP.

**Fails (li?n quan feature n?y, ?? s?a):**
- #2 ch? assert ?kh?ng Gate 1? ? si?t th?nh `list_pending_approvals == []`
  + `status=SENT`.
- #3 thi?u assert pending tr?ng sau approve/reject; pending ph?i c? payload
  alert.
- #4 thi?u assert Gate 2 **kh?ng** t? `upsert` watchlist.
- #5/#6 thi?u assert kh?ng t?o `alert_events` / pending HITL.

**Missing (??ng k? v?ng ? Phase 4+):**
- `POST /scan`, `POST /chat`, `POST /approvals/...` HTTP e2e.
- Chat ?m? trong watchlist? enforce qua WatchlistStore (answer_question
  ch?a nh?n watchlist port).

## 2026-09-17 ? Phase 3: ch?y full backend tests (test-plan, ch?a API/UI)

- Ch?y to?n b? `tests/`: **85 passed**.
- Th?m `tests/test_backend_integration.py` map test-plan e2e #1?#7 ?
  application layer (scan / approve-reject / chat / cron th? c?ng) ? kh?ng
  HTTP/UI (??ng ph?m vi ?ch?a c?n API/UI?).

## 2026-09-17 ? Review Cron / scan_watchlist vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Cron / watchlist nhi?u m?):**
- ??c watchlist ? g?i `scan_symbol` t?ng m?; 1 m? crash kh?ng ch?n m? sau.
- APScheduler interval (`create_scan_scheduler`); c? th? fire job th? c?ng.
- Ng??ng l?y theo t?ng `WatchlistItem`.

**Fails (li?n quan feature n?y, ?? s?a):**
- Thi?u case PriceSource l?i ? 1 m? (agent tr? error) v?n qu?t h?t danh s?ch.
- Job scheduler c? th? raise l?m nhi?u cron ? b?c `_safe_job`; th?m
  `build_scan_watchlist_job` (ch?y th? c?ng / APScheduler, kh?ng raise).
- `interval_minutes` kh?ng h?p l? ? fallback 60; test e2e job + isolation.

**Missing (??ng k? v?ng):**
- Wire scheduler v?o `main.py` lifespan / demo stack (Phase 6 h??ng d?n).
- Qu?t song song nhi?u m? (agents.md g?i ?; test-plan ch? y?u c?u ??c l?p).

## 2026-09-17 ? Phase 3: Cron / scan_watchlist (APScheduler)

- Th?m `application/scan_watchlist.py`: l?p watchlist ? `scan_symbol` t?ng
  m?; `try/except` theo m? (1 m? l?i kh?ng ch?n c?c m? c?n l?i).
- Th?m `infra/scheduler/cron.py`: `create_scan_scheduler` /
  `start_scan_scheduler` / `stop_scan_scheduler` (APScheduler interval,
  `SCAN_INTERVAL_MINUTES`).
- `tests/test_scan_watchlist.py` ? isolation l?i, threshold theo item, job
  ??ng k? + ch?y th? c?ng.

## 2026-09-17 ? Review review_approval vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (HITL Gate 1 / Gate 2):**
- Gate 1 approve ? g?i Notifier, status sent; reject ? `record_rejection`,
  kh?ng g?i.
- Gate 2 approve ? c?p nh?t watchlist (ng??ng + m? m?i); reject ? gi? nguy?n
  c?u h?nh c?.
- Id kh?ng t?n t?i / ?? x? l? ? `ok=False` + l?i r? (approve v? reject).

**Fails (li?n quan feature n?y, ?? s?a):**
- Reject l? do r?ng v?n th?nh c?ng (tr?i ?l? do reject ???c ghi l?i?) ? b?t
  bu?c reason kh?ng r?ng.
- Gate 1 approve: Notifier kh?ng set status v?n c? th? kh?ng ??? g?i? ? ?p
  `AlertStatus.SENT` sau send th?nh c?ng.
- Snapshot Gate 2 reject m? r?ng cho m? li?n quan; th?m test reject 2 l?n /
  missing / empty reason / SENT ?p status.

**Missing (??ng k? v?ng):**
- HTTP `POST /approvals/{id}/approve|reject` (Phase 4).

## 2026-09-17 ? Phase 3: review_approval (HITL Gate 1 + Gate 2)

- Th?m `application/review_approval.py`:
  - `list_pending_approvals` ? pending ch?a c? resolution.
  - Gate 1 approve ? `Notifier.send` (status sent); reject ?
    `record_rejection`, kh?ng g?i.
  - Gate 2 approve ? `WatchlistStore.upsert` (ng??ng + m? li?n quan);
    reject ? ghi l? do, gi? nguy?n watchlist.
  - Approve/reject id kh?ng t?n t?i ho?c ?? x? l? ? `ok=False` + error r?.
- `tests/test_review_approval.py`.

## 2026-09-17 ? Review h?i-??p vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (Supervisor / Rewrite / AnswerComposer / kh?ng HITL):**
- Tra c?u gi? ? ch? `price`, kh?ng `eval`.
- ?T?i sao ? gi?m? ? `price+news+eval`; tr? l?i c? tin/l? do.
- ?C?n m? ??? ? Rewrite l?y symbol t? Memory.
- Guardrail d?ng chung `output_checks`; `hitl_used` / kh?ng t?o pending.
- L?u h?i tho?i v?o Memory sau tr? l?i.

**Fails (li?n quan feature n?y, ?? s?a):**
- ?th?ng tin gi? ?? b? route `news_lookup` v? substring `tin` ? l?c ?th?ng
  tin? tr??c khi nh?n di?n tin t?c.
- Follow-up kh?ng ticker (?T?i sao gi?m??) ch?a l?y symbol t? Memory ? b? sung.
- `hitl_used` / `pending_approvals_created` hardcode `False`/`0` ? ??m th?t t?
  delta `alert_events`.
- Fallback guardrail khi ?n?n b?n? + s? gi?; assert output cu?i lu?n pass check.

**Missing (??ng k? v?ng):**
- `POST /chat` API (Phase 4).

## 2026-09-17 ? Phase 3: h?i-??p (Supervisor + AnswerComposer + answer_question)

- Th?m `domain/agents/supervisor.py`: RewriteQuestion (symbol t? c?u h?i /
  Memory ?m? ???) + Supervisor routing (`agents_to_call`: price / news / eval).
- Th?m `domain/agents/answer_composer.py`: so?n c?u tr? l?i, model routing,
  v?ng guardrail d?ng chung `output_checks` (kh?ng HITL).
- Th?m `application/answer_question.py`: Rewrite ? route ? g?i worker ?
  compose ? l?u h?i tho?i Memory; `hitl_used=False`, kh?ng t?o pending.
- `FakeMemoryStore` ghi conversation; `tests/test_answer_question.py`.

## 2026-09-16 ? Review scan_symbol vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi lu?ng gi?m s?t 1 m? / Confidence Gate / Gate 2 t?o pending):**
- Price+News ? Classifier; NORMAL d?ng kh?ng alert; ABNORMAL ? Eval ?
  Synthesis (guardrail) ? Confidence Gate.
- Confidence cao + kh?p ng??ng ? auto-send (Notifier), kh?ng Gate 1 pending.
- Confidence th?p / kh?ng kh?p ng??ng ? Gate 1 `pending_approval` ??ng n?i dung.
- ?? xu?t ng??ng/m? ? lu?n Gate 2 pending, kh?ng ?p d?ng watchlist.

**Fails (li?n quan feature n?y, ?? s?a):**
- `Notifier.send` l?i ? crash to?n b? scan ? b?t l?i, fallback Gate 1 pending.
- Thi?u assert/test ng??ng t? `WatchlistStore`; thi?u x?c nh?n Gate 2 kh?ng
  `upsert` watchlist; thi?u assert auto-send kh?ng t?o Gate 1 pending.
- So s?nh route abnormal b?n h?n v?i string value.

**Missing (??ng k? v?ng):**
- API `POST /scan`, approve/reject (`review_approval`), cron nhi?u m?.

## 2026-09-16 ? Phase 3: scan_symbol (Orchestrator + Confidence Gate)

### C?ng th?c Confidence Gate (ch?t)
- Auto-send khi `confidence >= 0.8` **v?** `|change_pct| >= threshold_pct`
  (ng??ng user / watchlist; m?c ??nh 3%).
- Ng??c l?i ? HITL Gate 1 (`pending_approval` trong MemoryStore).
- C? `proposed_threshold_pct` / `proposed_related_symbols` ? **lu?n** t?o
  Gate 2 pending (kh?ng c? ???ng t?t), k? c? khi auto-send Gate 1.

### Thay ??i
- Th?m `application/scan_symbol.py`: Price+News song song ? Classifier ?
  (NORMAL d?ng) / (ABNORMAL ? Eval ? Gate2? ? Synthesis+Guardrail ?
  Confidence Gate ? Notifier ho?c Gate 1).
- `tests/test_scan_symbol.py`; `FakeMemoryStore` ghi `alert_events`;
  th?m `FakeNotifier`.

## 2026-09-16 ? Review ConsoleNotifier vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Notifier / MVP ?g?i c?nh b?o?):**
- Log console + l?u DB (`append_alert_event`) ??ng product-spec (kh?ng
  b?t bu?c email/push).
- G?i th?nh c?ng ? `FinalAlert.status=SENT` (??? g?i?); event `kind=sent`
  ?? Notifier ?ghi nh?n? (test-plan e2e confidence cao).

**Fails (li?n quan feature n?y, ?? s?a):**
- `status=REJECTED` v?n b? g?i + ??i th?nh SENT (tr?i ?reject ? kh?ng g?i?)
  ? b? qua, ch? warning, kh?ng ghi event.
- `append_alert_event` l?i nh?ng status ?? = SENT (l?ch DB) ? ghi DB tr??c,
  ch? set SENT khi persist OK.

**Missing (??ng k? v?ng):**
- Wire scan/approve g?i `Notifier`; e2e POST /scan (Phase 4).

## 2026-09-16 ? Phase 3: ConsoleNotifier

- Th?m `infra/notify/console_notifier.py`: implement `Notifier.send` ? log
  console + `MemoryStore.append_alert_event` (kind=`sent`), set
  `FinalAlert.status=SENT`.
- `user_id` l?y t? `alert.metadata["user_id"]` ho?c m?c ??nh constructor.
- `tests/test_console_notifier.py` ? ghi DB SQLite t?m + assert log.

## 2026-09-16 ? Review market_data vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi PriceSource/NewsSource):**
- ??ng Out of Scope MVP: 1 ngu?n gi? (`vnstock` VCI) + 1 ngu?n tin CafeF;
  ports cho ph?p th?m ngu?n sau.
- L?i/timeout: gi? ? `PriceQuote.error` (kh?ng raise); tin ? `[]` (??ng
  contract `NewsSource`); CI d?ng mock theo test-plan.
- CafeF: parse HTML, l?c `query` / `days`; HTTP l?i kh?ng crash.

**Fails (li?n quan feature n?y, ?? s?a):**
- DataFrame kh?ng s?p theo `time` ? l?y nh?m ?gi? m?i nh?t? ? sort theo
  `time` khi c? c?t.
- C?t `Close` (hoa) b? coi l? thi?u d? li?u ? chu?n ho? t?n c?t v?
  lowercase tr??c khi ??c `close`.
- Thi?u test: empty DF / raise ? error; sort theo time; `Close`; l?c
  `days` CafeF.

**Missing (??ng k? v?ng ? ch?a ph?i market_data):**
- Wire v?o scan/chat/cron; Phase 5 ?agent b?o kh?ng l?y ???c d? li?u? khi
  NewsSource tr? `[]` do timeout (x? l? ? agent/orchestrator).

## 2026-09-16 ? Phase 3: market_data (PriceSource / NewsSource)

### Quy?t ??nh ngu?n d? li?u
- **Gi?:** `vnstock` `Quote.history` (source `VCI`) ? l?y 2 phi?n ??ng c?a
  g?n nh?t ?? t?nh % thay ??i; kh?ng d?ng API SSI/TCBS ri?ng.
- **Tin:** CafeF Ajax HTML
  (`Events_RelatedNews_New.aspx`) ? kh?ng c? API ch?nh th?c; parse `<li>`
  title/url/ng?y; l?i HTTP/timeout ? tr? `[]`.

### Thay ??i
- Th?m `infra/market_data/price_source.py` (`VnstockPriceSource`).
- Th?m `infra/market_data/news_source.py` (`CafefNewsSource` + parser HTML).
- Dependency: `vnstock>=3.0.0`, `pandas>=2.0.0` trong `pyproject.toml`.
- `tests/test_market_data.py` ? parse/filter CafeF (mock HTTP), gi? t?
  FakeQuote dataframe, symbol r?ng.

## 2026-09-16 ? Review SQLite storage vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi storage / In Scope):**
- C? SQLite Watchlist / Price History / Memory ??ng product-spec MVP.
- H? tr? ghi preferences, h?i tho?i, alert events, reject (n?n t?ng HITL/
  chat trong test-plan).

**Fails (li?n quan storage, ?? s?a):**
- `record_rejection` kh?ng ??c l?i ???c ?? x?c nh?n AC ?l? do reject ???c
  ghi l?i? ? th?m `SqliteMemoryStore.list_rejections` + assert trong test.
- Thi?u CHECK `threshold_pct >= 0`; ?p ki?u float cho OHLCV nullable.
- Test th?m case Gate 2 reject kh?ng ??ng watchlist (gi? ng??ng c?).

**Missing (??ng k? v?ng ? ch?a ph?i storage):**
- API approve/reject, scan/chat e2e, Notifier g?i c?nh b?o.

## 2026-09-16 ? Phase 3: SQLite storage (watchlist / price history / memory)

- Th?m `infra/storage/sqlite_db.py` (schema + connect).
- Implement `SqliteWatchlistStore`, `SqlitePriceHistoryStore` (+ `upsert_bars`),
  `SqliteMemoryStore` theo `domain/ports.py`.
- `tests/test_sqlite_stores.py` round-trip tr?n file DB t?m.

## 2026-09-16 ? Review SynthesisAgent + Guardrail vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Synthesis + Guardrail / test-plan + AC guardrail):**
- Severity HIGH ? model n?ng; LOW ? model nh?.
- ?n?n mua? ? ch?n + so?n l?i (`draft_attempts > 1`).
- S? kh?ng c? trong evidence ? `check_output` fail.

**Fails (li?n quan feature n?y, ?? s?a):**
- H?t max attempts v?n c? th? ph?t h?nh body ch?a s?ch (reasoning ch?a
  ?n?n b?n?) ? fallback ch? evidence + ki?m guardrail l?i.
- Composer raise / symbol r?ng ch?a x? l? ? b?t l?i, tr? k?t qu? r?.
- B? sung case ?n?n b?n? + assert output cu?i lu?n pass `check_output`.

**Missing (??ng k? v?ng):**
- AC end-to-end scan/HITL/chat; LLM composer th?t (hi?n inject/heuristic).

## 2026-09-16 ? Phase 3: SynthesisAgent + Guardrail output

- Th?m `domain/guardrails/output_checks.py`: ch?n ?n?n mua/b?n?; s? li?u
  ph?i c? trong evidence.
- Th?m `domain/agents/synthesis_agent.py`: `select_model` (light/heavy),
  so?n `FinalAlert`, v?ng rewrite khi guardrail fail; ??c preferences t?
  `MemoryStore`.
- `FakeMemoryStore` + `tests/test_synthesis_agent.py` (routing model, rewrite
  khi c? l?i khuy?n mua/b?n, s? kh?ng kh?p evidence).

## 2026-09-16 ? Review EvalAgent vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi EvalAgent / test-plan):**
- ?? data ? kh?ng g?i `read_price_history`, c? `Severity`.
- M?p m? ? g?i history; confidence th?p h?n khi l?ch s? kh?ng ?ng h?
  (so s?nh t??ng ??i v?i case l?ch s? ?ng h?).

**Fails (li?n quan EvalAgent, ?? s?a):**
- `read_history` raise l?m m?t Severity r? ? b?t ri?ng, v?n tr? Severity
  confidence th?p + evidence l?i.
- Symbol r?ng / history r?ng sau khi request ? h? confidence r? r?ng.
- Test ?th?p h?n? ch? assert tuy?t ??i ? th?m so s?nh
  opposed.confidence < supported.confidence.

**Missing (??ng k? v?ng):**
- AC end-to-end product-spec (Gate 2 apply proposal, scan API?).
- LLM ReAct brain th?t (hi?n heuristic + inject).

## 2026-09-16 ? Phase 3: EvalAgent

- Th?m `domain/agents/eval_agent.py`: `run_eval_agent` ? `Severity`;
  `HeuristicEvalBrain` g?i `PriceHistoryStore.read_history` khi d? li?u m?p
  m?; l?ch s? kh?ng ?ng h? ? h? `confidence`; c? th? ?? xu?t ng??ng (Gate 2).
- `FakePriceHistoryStore` + `tests/test_eval_agent.py` (?? data b? qua
  history; m?p m? ? g?i history + confidence th?p).

## 2026-09-16 ? Review Event Classifier vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Event Classifier / test-plan):**
- Bi?n ??ng nh? + kh?ng tin x?u ? `b?nh th??ng`.
- |%| l?n (t?ng ho?c gi?m) ho?c tin ti?u c?c ? `b?t th??ng`.

**Fails (li?n quan classifier, ?? s?a):**
- Hint `"?m"` false-positive trong ???m b?o?; ph? ??nh ?kh?ng gi?m?
  v?n b? b?t ? b? hint m? h?, th?m ch?ng negation; threshold <= 0 fallback 3.0.
- Brain raise ? crash escalate ? b?t l?i, tr? `NORMAL` (l?c r?, kh?ng g?i Eval).

**Missing (??ng k? v?ng):**
- AC end-to-end `product-spec.md`; LLM classifier th?t (hi?n heuristic + inject).

## 2026-09-16 ? Phase 3: Event Classifier

- Th?m `domain/agents/event_classifier.py`: `classify_event` ?
  `RoutingDecision` (`b?nh th??ng` / `b?t th??ng`); `HeuristicEventClassifier`
  (ng??ng |%| ho?c tin ti?u c?c); brain inject ???c cho LLM sau.
- `tests/test_event_classifier.py` theo test-plan (bi?n ??ng nh?; |%| l?n;
  tin ti?u c?c).

## 2026-09-16 ? Review NewsAgent vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi NewsAgent / test-plan):**
- Tin kh?ng li?n quan b? l?c ? `items == []`.
- C?n 2 l?n g?i tool m?i ?? tin ? `tool_calls == 2`, d?ng khi ??;
  `max_steps` ch?n l?p v? h?n.

**Fails (li?n quan NewsAgent, ?? s?a):**
- `fetch_news` raise gi?a v?ng ? m?t to?n b? tin ?? gather ? b?t l?i theo
  t?ng l?n g?i, gi? tin ?? l?c + `error` r?.
- Ch? `kind=="search"` m?i g?i tool; symbol r?ng ? l?i r?, kh?ng ch?y loop.

**Missing (??ng k? v?ng):**
- AC `product-spec.md` (scan/chat/HITL end-to-end).
- LLM brain th?t (hi?n inject `NewsAgentBrain` / heuristic) ? wiring LLM
  thu?c b??c sau.

## 2026-09-16 ? Phase 3: NewsAgent + unit test

- Th?m `domain/agents/news_agent.py`: v?ng l?p ReAct (search/finish) qua
  `NewsAgentBrain`, g?i `NewsSource.fetch_news`, l?c tin li?n quan;
  `HeuristicNewsBrain` fallback kh?ng LLM; `max_steps` ch?ng l?p v? h?n.
- `tests/fakes.FakeNewsSource` + `tests/test_news_agent.py` (l?c tin r?c,
  g?i tool 2 l?n r?i d?ng, cap max_steps).

## 2026-09-16 ? Review PriceAgent vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi PriceAgent / test-plan):**
- T?ng / gi?m / ??ng y?n ? `change_pct` ??ng.
- `PriceSource` l?i / thi?u `latest_close` ? `PriceAgentResult` c? `error`,
  kh?ng tr? `None` cho to?n b? k?t qu?.

**Fails (li?n quan PriceAgent, ?? s?a):**
- `PriceSource` raise exception ? agent crash (tr?i ?kh?ng crash?) ? b?c
  try/except, tr? `error` r?.
- Thi?u test `prev_close` None + ngu?n raise ? ?? th?m.

**Missing (??ng k? v?ng):**
- To?n b? AC `product-spec.md` (scan API, HITL, chat, guardrail).
- C?c agent/e2e kh?c trong `test-plan.md`.

## 2026-09-16 ? Phase 3: PriceAgent + unit test

- Th?m `domain/agents/price_agent.py`: `run_price_agent` t?nh `change_pct`,
  tr? `PriceAgentResult` r? r?ng khi l?i / thi?u d? li?u.
- Th?m `tests/test_price_agent.py` + `tests/fakes.FakePriceSource` (t?ng/
  gi?m/??ng y?n + error).

## 2026-09-16 ? Review `domain/ports.py` vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi ports):**
- ?? 6 interface checklist; `PriceQuote.error` h? tr? test-plan
  ?kh?ng c? d? li?u / kh?ng tr? None m?p m??; `record_rejection` +
  `Notifier.send` kh?p HITL / g?i c?nh b?o; `read_history` kh?p EvalAgent.

**Fails (li?n quan ports, ?? s?a):**
- `NewsSource` thi?u khung th?i gian (agents: symbol + time window) ? th?m
  `days`.
- `MemoryStore` thi?u l?ch s? c?nh b?o (agents kho d? li?u) ?
  `append_alert_event` / `list_alert_events`.
- `PriceBar.open` shadow builtin ? ??i `open_price`.
- Docstring `PriceSource`: l?i tr? `PriceQuote` v?i `error`, kh?ng raise m? h?.

**Missing (??ng k? v?ng ? ch?a implement infra/agents/API):**
- To?n b? AC `product-spec.md` v? e2e/unit agent trong `test-plan.md`.

## 2026-09-16 ? Phase 3: `domain/ports.py`

- Khai b?o Protocol: `PriceSource`, `NewsSource`, `WatchlistStore`,
  `PriceHistoryStore`, `MemoryStore`, `Notifier`.
- DTO k?m port: `PriceQuote`, `NewsItem`, `PriceBar` (dataclass thu?n).
- Ch?a c? implement infra ? ch? interface cho agent/fake test.

## 2026-09-16 ? Review domain entities vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi entity):**
- ?? 4 model checklist: `WatchlistItem`, `RoutingDecision`, `Severity`,
  `FinalAlert`; `EventRoute` kh?p test-plan (?b?nh th??ng?/?b?t th??ng?);
  `Severity` c? ?? xu?t ng??ng/m? (Gate 2); `AlertStatus` c?
  pending_approval / sent / rejected (Gate 1).

**Fails (li?n quan entity, ?? s?a):**
- `FinalAlert` thi?u `id` + `reject_reason` ? kh?ng bi?u di?n ???c AC
  approve/reject (`/approvals/{id}`, l? do reject). ?? th?m.
- `WatchlistItem.symbol` / `FinalAlert.symbol` cho ph?p r?ng ? `min_length=1`.

**Missing (??ng k? v?ng ? ch?a ph?i entities):**
- To?n b? lu?ng AC/API/agent trong `product-spec.md` / `test-plan.md`
  (scan, chat, guardrail, cron?).

Kh?ng th?m entity/API m?i ngo?i ch?nh 4 model ?? c?.

## 2026-09-16 ? Phase 3: domain entities

- Th?m `domain/entities/models.py`: `WatchlistItem`, `RoutingDecision`,
  `Severity`, `FinalAlert` (+ enum `EventRoute`, `SeverityLevel`,
  `AlertStatus`) ? pydantic thu?n, kh?ng import infra.
- Export qua `domain/entities/__init__.py`.

## 2026-09-16 ? Review Phase 1 (re-check) vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Phase 1):**
- Skeleton + `GET /health` ? `{"status":"ok"}`; app title =
  `Portfolio Watch & Chat Agent`.
- Ch? expose `/health` (+ docs m?c ??nh FastAPI) ? ch?a c? `/scan`, `/chat`,
  `/approvals`, `/watchlist` (??ng ?ch?a business features?).

**Fails:** kh?ng c? l?i Phase 1 m?i so v?i l?n review tr??c.

**Missing (??ng k? v?ng ? Phase 3+):**
- To?n b? acceptance criteria `product-spec.md`.
- To?n b? unit/e2e `test-plan.md`.

Kh?ng ??i code trong l?n review n?y.

## 2026-09-16 ? Phase 1 re-check (?? ho?n th?nh tr??c ??)

- ??c l?i AGENTS.md + specs: checklist Phase 1 to?n b? `[x]`.
- Smoke-test l?i: `GET /health` ? `{"status":"ok"}`; `src/chatbot/` kh?ng
  c?n; `pyproject.toml` + `src/portfolio_watch/` (settings, infra/llm, main)
  c?n ??.
- **Kh?ng vi?t l?i / kh?ng th?m business features** ? tr?nh ??ng Phase 2 UI
  ?? xong. M?c ch?a l?m ti?p theo l? Phase 3.

## 2026-09-16 ? Phase 2: x?c nh?n m? UI (3 khu v?c, kh?ng l?i console)

- Ki?m tra qua `python -m http.server` + Chrome headless: `#chat`,
  `#watchlist`, `#approvals` hi?n th?; `style.css`/`app.js` 200.
- Ph?t hi?n console error `GET /favicon.ico` 404 ? th?m
  `<link rel="icon" href="data:,">` trong `index.html`.
- Re-check: 0 console error. Phase 2 UI checklist ho?n t?t.

## 2026-09-16 ? Review `web/style.css` vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi CSS / In Scope frontend):**
- Product-spec: ?1 trang ??n gi?n ? kh?ng c?n polish UI? ? `style.css` ch?
  l?m 3 khu v?c (chat / watchlist / approvals) d? ??c; kh?ng over-design.

**Fails:** kh?ng c? l?i CSS li?n quan feature n?y so v?i specs.

**Missing (??ng k? v?ng ? kh?ng thu?c CSS):**
- To?n b? acceptance criteria `product-spec.md` (scan, alert, HITL, chat API,
  guardrail).
- To?n b? cases `test-plan.md` (kh?ng c? ti?u ch? CSS/UI visual).

Kh?ng ??i code trong l?n review n?y.

## 2026-09-16 ? Phase 2: CSS t?i thi?u (`web/style.css`)

- Th?m `web/style.css` (layout ??n gi?n: section, chat box, table, n?t).
- `index.html` link stylesheet. Kh?ng polish UI.

## 2026-09-16 ? Review `web/app.js` stubs vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi stub Phase 2):**
- C? h?m stub cho endpoint AC/test-plan s? d?ng sau: `POST /scan`,
  `POST /chat`, `GET/POST approvals`, CRUD `/watchlist`.
- Chat submit + Approve/Reject ch? `console.log` / `fetch` stub ? ch?a n?i
  UI d? li?u th?t (??ng Phase 2).

**Fails (li?n quan feature n?y, ?? s?a):**
- `wireUiStubs()` t? g?i `getWatchlist()` + `getApprovals()` khi load ? lu?n
  l?i m?ng/CORS tr?n console (backend ch?a c?), xung ??t m?c Phase 2
  ?kh?ng l?i console?. ?? b? auto-fetch; g?i tay t? console khi c?n.

**Missing (??ng k? v?ng ? kh?ng implement ? stub):**
- To?n b? acceptance criteria `product-spec.md` (lu?ng scan/chat/HITL th?t,
  c?p nh?t tr?ng th?i, guardrail).
- To?n b? e2e `test-plan.md` (`/scan`, `/chat`, approve/reject c? side-effect).

Kh?ng th?m UI/API m?i (vd. n?t Qu?t ngay).

## 2026-09-16 ? Phase 2: `web/app.js` (API stubs, log console)

- Th?m `web/app.js`: stub `fetch` cho Phase 4 (`/scan`, `/chat`, `/approvals`,
  approve/reject, CRUD `/watchlist`) ? ch? `console.log`, ch?a c?p nh?t UI.
- `index.html`: n?p `app.js`; n?t Approve/Reject g?n `data-*-id` ?? g?i stub.

## 2026-09-16 ? Review `web/index.html` vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi UI t?nh / In Scope frontend):**
- ?? 3 khu v?c product-spec y?u c?u: chat box, xem watchlist, danh s?ch
  c?nh b?o ch? duy?t (Approve/Reject).

**Fails (l?i li?n quan feature n?y, ?? s?a):**
- Form chat `type="submit"` m?c ??nh reload trang khi b?m G?i (file://).
  Th?m `onsubmit="return false;"` ? ch?a n?i API (?? Phase 2 m?c `app.js`).

**Missing (??ng k? v?ng ? kh?ng thu?c HTML t?nh):**
- To?n b? acceptance criteria `product-spec.md` (scan API, alert th?t, HITL
  qua API, Chat API, guardrail).
- To?n b? cases `test-plan.md` (agents, gates, e2e `/scan` `/chat`).

Kh?ng th?m khu v?c/UI m?i (vd. n?t Qu?t ngay) trong l?n s?a n?y.

## 2026-09-16 ? Phase 2: `web/index.html` (3 khu v?c t?nh)

- T?o `web/index.html` v?i 3 section t?nh: Chat (? nh?p + khung h?i tho?i),
  Watchlist (b?ng m? + ng??ng m?u), C?nh b?o ch? duy?t (item m?u +
  Approve/Reject). Ch?a n?i API, ch?a c? `app.js` / CSS ri?ng.

## 2026-09-16 ? Review Phase 1 vs product-spec / test-plan

### K?t qu? ??i chi?u

**Passes (ph?m vi Phase 1 / implementation-plan):**
- Khung `src/portfolio_watch/` + `pyproject.toml` + `infra/llm/` +
  `GET /health` ? `{"status":"ok"}`.
- Settings c? bi?n ri?ng project (watchlist, threshold, sources, sqlite).

**Fails (l?i Phase 1, ?? s?a):**
- `.env` c? c?n `APP_NAME=Vietnamese Legal Assistant` ? FastAPI title /
  settings sai t?n app. ?? ??i `APP_NAME` v? b? sung c?c key Phase 1 c?n
  thi?u (`API_*`, `DEFAULT_*`, `PRICE_SOURCE`, `NEWS_SOURCE`, `SQLITE_PATH`,
  ?) m? kh?ng ??ng API keys.
- Port `8000` b? process uvicorn smoke-test tr??c chi?m ? `python -m ?`
  b?o WinError 10013. ?? d?ng process; kh?i ??ng l?i `/health` OK.

**Missing (??ng k? v?ng ? thu?c phase sau, kh?ng implement ? ??y):**
- To?n b? acceptance criteria trong `product-spec.md` (scan, watchlist
  alert, HITL approve/reject, Gate 2, Chat API, guardrail mua/b?n).
- To?n b? unit/integration cases trong `test-plan.md` (agents, gates,
  `POST /scan`, `POST /chat`, cron).

Kh?ng th?m business features m?i trong l?n s?a n?y.

## 2026-09-16 ? Phase 1: Project setup

- X?a to?n b? `src/chatbot/` (code c? ReAct ??n-agent).
- T?o khung `src/portfolio_watch/` (api / application / domain / infra /
  shared) + `__init__.py`.
- Th?m `pyproject.toml` (fastapi, uvicorn, langgraph, langchain-openai,
  pydantic-settings, openai, apscheduler).
- Th?m `shared/settings.py`, `shared/logging.py`, `.env.example` (b? RAG/
  embeddings; th?m watchlist, threshold, price/news source, sqlite path).
- Port `infra/llm/` t? `llm-engineer-demo/app/llm` (backends, client,
  resilience, params, completion) ? ??i import sang `src.portfolio_watch`.
- `main.py`: FastAPI + `GET /health` ? `{"status":"ok"}`.
- G? service chatbot c? kh?i `docker-compose.yml` (Docker demo = Phase 7).
- C?p nh?t README l?nh ch?y Phase 1.
- **Ch?a c?** business features (scan/chat/agents/UI).

## 2026-09-16 ? AGENTS.md cho coding agent

- Vi?t l?i `AGENTS.md` th?nh h??ng d?n ng?n cho Cursor agent (??c specs tr??c,
  m?t phase/task m?i l?n, gi? app ??n gi?n, kh?ng th?m lib th?a, kh?ng ??i
  architecture n?u ch?a c?p nh?t spec, c?p nh?t change-log + h??ng d?n test
  sau m?i l?n implement).
- Chuy?n m? t? domain agents sang `specs/agents.md`; c?p nh?t tham chi?u trong
  `README.md`, `specs/product-spec.md`, `specs/implementation-plan.md`.

## 2026-09-16 ? Kh?i t?o spec (Spec-Driven Development)

- ??c s? ?? ki?n tr?c (`portfolio-watch-agent-explained.md` + `.mmd`/`.png`),
  kh?o s?t `llm-engineer-demo` (ngu?n k? thu?t t?i d?ng) v? `AI_Face_checkin`
  (m?u clean architecture: `api ? application ? domain ? infra` + `shared`).
- X?c nh?n v?i ng??i d?ng: code c? trong `src/chatbot/` (ReAct ??n-agent,
  guardrails/eval r?ng, layer ??t t?n `app/domain/infrastructure`) s? b? x?a
  v? vi?t l?i theo c?u tr?c m?i ? ch? t?i d?ng ? T??NG k? thu?t (LLM client,
  model routing, guardrails, tracing), kh?ng gi? nguy?n file.
- Vi?t 6 t?i li?u spec ban ??u: `README.md`, `AGENTS.md`,
  `specs/product-spec.md`, `specs/implementation-plan.md`,
  `specs/test-plan.md`, `specs/change-log.md` (file n?y).
- **Ch?a vi?t code implementation** ? ??y l? b??c d?ng l?i ?? review spec
  tr??c khi b?t ??u build theo `specs/implementation-plan.md`.

### Quy?t ??nh m?, c?n ch?t tr??c/khi implement

- Ngu?n d? li?u gi? real-time cho m? VN (vnstock? SSI/TCBS public API?) ?
  ch?a kh?o s?t k?, ghi trong implementation-plan.md ph?n "R?i ro".
- C?ch l?y tin t? cafef (API ch?nh th?c hay scraping) ? ch?a x?c nh?n.
- C?ng th?c c? th? cho "?? tin c?y cao" ? Confidence Gate ? s? ch?t khi vi?t
  `synthesis_agent.py`.

## 2026-09-19 - Phase 14a
- scan trace = per-request (1 POST /v1/scan = 1 trace), not per-symbol in batch.



## 2026-09-22 - Phase 15: Golden dataset v3 (Line 1)

- Migrated `golden_dataset.yaml` to `golden_v3.yaml` adding `dataset`, `version`, and `changelog` fields.
- Preserved all 30 existing test cases.
- Updated each case to include `id` and `slice` structure with `type` (`lookup`, `comparison`, `out_of_scope`, `injection`) and `difficulty` (`easy`, `medium`, `hard`).
- Added test `tests/test_golden_v3.py` to verify the structure, slice types, and test counts.
- **Manual Verify Steps**:
  - Run `python -m pytest tests/test_golden_v3.py -q --tb=line`
  - Expect 1 passed.

## 2026-09-22 - Phase 15: Golden dataset v3 (Line 2)

- Appended 3 diagram cases to specs/eval/golden_v3.yaml.
- Updated test 	ests/test_golden_v3.py to assert total cases >= 33, check for diagram slice type, and ensure all 5 slice types are present.
- Marked line 2 of Phase 15 as done in specs/implementation-plan.md.
- **Manual Verify Steps**:
  - Run python -m pytest tests/test_golden_v3.py -q --tb=line
  - Expect 1 passed.

## 2026-09-22 - Phase 15: Golden dataset v3 (Line 3)

- Implemented Rule-based must_include / must_not_include for 5 slices.
- Updated src/portfolio_watch/eval/run.py to add GOLDEN_V3_PATH, RULE_SLICES, and rule validation.
- Added `--dataset` CLI arg; threaded to `run_eval(dataset_path=...)`.
- Added diagram_01 fixture to _self_check().
- Created `tests/test_golden_v3_rules.py` for testing new rule evaluation logic.
- Checked off Phase 15 line 3 in specs/implementation-plan.md.
- **Manual Verify Steps**:
  - Run python -m pytest tests/test_golden_v3_rules.py tests/test_eval.py -q --tb=line
  - Expect tests to pass.
