# Implementation Plan — Portfolio Watch (Module III LLMOps)

Kế hoạch triển khai theo **Spec-Driven Development** và hands-on **Module III** (*LLM-Engineer-Handbook/module-3-production-llmops.md*).

## Quy tắc làm việc

1. Chỉ mở **một Phase** tại một thời điểm.
2. **Trước khi code:** tóm tắt việc sẽ làm, file sẽ sửa, cách test.
3. **Sau khi xong:** đánh dấu `[x]`, cập nhật `specs/change-log.md`, ghi lệnh test cho user.
4. **Phase 1 đã code xong** — tiếp tục Phase 2 trở đi theo checklist bên dưới.

---

## Roadmap

| Phase | Trọng tâm | M3 | Trạng thái |
| :---: | :--- | :---: | :---: |
| 0 | Spec & tài liệu nền | — | `[x]` |
| 1 | Rà soát prompt — bỏ hardcode | B1 | `[x]` |
| 2 | Prompt v2 + changelog | B1 | `[x]` |
| 3 | Prompt lint + so sánh version | B1 | `[ ]` |
| 4 | Golden subset cho PR | B2 | `[x]` |
| 5 | Eval gate theo slice | B2 | `[x]` |
| 6 | Eval history + chứng minh gate | B2 | `[x]` |
| 7 | Cost baseline | B3 | `[x]` |
| 8 | Cache tầng 1 (exact) | B3 | `[x]` |
| 9 | Cache tầng 2 + báo cáo cost | B3 | `[x]` |
| 10 | Docker & SSE hardening | B4 | `[x]` |
| 11 | Deploy demo + smoke test | B5 | `[x]` |
| 12 | GitHub Actions CI + eval gate | B6 | `[x]` |
| 13 | Observability + playbook | B7 | `[x]` |
| 14 | Capstone — tích hợp & feedback loop | B8 | `[x]` |

---

## Phase 0: Spec & Tài Liệu Nền

**Mục tiêu:** Có bộ spec MVP rõ ràng trước khi code chu kỳ M3.

- [x] Cập nhật `README.md`
- [x] Cập nhật `AGENTS.md`
- [x] Cập nhật `specs/product-spec.md` (goal, users, flow, scope, acceptance)
- [x] Cập nhật `specs/implementation-plan.md`
- [x] Cập nhật `specs/test-plan.md`
- [x] Ghi entry spec trong `specs/change-log.md`

**Xong khi:** 6 file trên nhất quán, không mâu thuẫn với nhau.

---

## Phase 1: Rà Soát Prompt — Bỏ Hardcode

**Mục tiêu:** Mọi agent load prompt qua registry, không còn chuỗi prompt nằm trong code.

**Handbook M3-B1 · Bước 1**

- [x] Liệt kê tất cả agent nodes dùng LLM (guardrail, rewrite, supervisor, composer, …)
- [x] Tìm và ghi nhận chỗ còn hardcode prompt trong `src/backend/`
- [x] Chuyển prompt còn sót sang `resources/prompts/<name>/v1.yaml`
- [x] Thay caller bằng `prompt_registry.render("<name>", ...)` / `get_system_prompt()`
- [x] Chạy `pytest tests/test_agents.py -v` — không regression

**Xong khi:** Grep codebase không còn prompt dài hardcode trong agent logic.

**Test:**
```bash
pytest tests/test_agents.py -v
```

---

## Phase 2: Prompt v2 + Changelog

**Mục tiêu:** Có ≥ 2 version prompt với metadata và lý do đổi rõ ràng.

**Handbook M3-B1 · Bước 2**

- [x] Tạo `resources/prompts/answer_compose/v2.yaml`
  - Siết grounding số liệu VN; cấm bịa giá
- [x] Tạo `resources/prompts/rewrite_question/v2.yaml`
  - Cải thiện phân giải đại từ Turn 2
- [x] Điền `changelog` (đổi gì, **vì sao**) cho cả hai v2
- [x] Điền metadata: `name`, `version`, `model`, `owner`, `created`
- [x] *(Chưa promote)* Giữ `production.txt` trỏ v1 — chỉ test v2 thủ công

**Xong khi:** 2 prompt có v1 + v2 đầy đủ metadata; `git diff` v1→v2 đọc được.

**Test:** Load v2 qua registry với `version=2` — không lỗi thiếu biến.

---

## Phase 3: Prompt Lint + So Sánh Version

**Mục tiêu:** CI-ready lint prompt; script so sánh output v1 vs v2.

**Handbook M3-B1 · Bước 3–4**

- [x] Tạo `src/backend/infra/llm/prompt_lint.py`
  - [x] Kiểm metadata bắt buộc (`name`, `version`, `model`, `owner`, `changelog`)
  - [x] Kiểm biến template khớp khai báo
- [x] Tạo `scripts/compare_prompt_versions.py`
  - [x] 5 câu hỏi stock mẫu
  - [x] In output v1 và v2 cạnh nhau
- [ ] *(Tùy chọn MVP)* Scaffold `pick_prompt_version()` sticky theo `session_id`
- [x] Bổ sung test lint trong `tests/test_eval.py` hoặc file test phù hợp

**Xong khi:**
- `python -m backend.infra.llm.prompt_lint resources/prompts/` → exit 0
- Script compare chạy được, có output so sánh

**Test:**
```bash
python -m backend.infra.llm.prompt_lint resources/prompts/
python scripts/compare_prompt_versions.py
```

---

## Phase 4: Golden Subset Cho PR

**Mục tiêu:** Bộ eval nhỏ (~20 cases) chạy nhanh trên PR.

**Handbook M3-B2 · Bước 1 (rút gọn)**

- [x] Rà soát `resources/eval/golden_v5.yaml` — mỗi case có `slice`, `expected`, assertions
- [x] Tạo `resources/eval/golden_pr_subset.yaml` (~20 cases)
  - [x] Ưu tiên: `injection`, `out_of_scope`, `comparison`, `session_memory`
- [x] Cập nhật runner hỗ trợ flag `--subset`
- [x] Subset chạy xong < ~3 phút (local, có API key)

**Xong khi:** `python -m backend.eval.run --subset` chạy 20 cases và ra report.

**Test:**
```bash
python -m backend.eval.run --subset --report specs/eval/pr_subset_report.md
```

---

## Phase 5: Eval Gate Theo Slice

**Mục tiêu:** Script gate chặn merge khi điểm tụt quá ngưỡng — đặc biệt slice bảo mật.

**Handbook M3-B2 · Bước 5**

- [x] Tạo `src/backend/eval/gate.py` với ngưỡng:
  - [x] `overall` ≥ 0.85 (tolerance 0.03)
  - [x] `rule_pass_rate` ≥ 0.95 (tolerance 0.02)
  - [x] `slice:injection` = 100% (tolerance 0)
  - [x] `slice:out_of_scope` = 100% (tolerance 0)
- [x] Runner xuất `--json` cho gate đọc
- [x] Report markdown liệt kê **case fail** kèm output (không chỉ số tổng)
- [x] Report có `by_slice` aggregate

**Xong khi:** `python -m backend.eval.gate --run <report.json>` trả exit 0/1 đúng.

**Test:**
```bash
python -m backend.eval.run --subset --json specs/eval/pr_report.json
python -m backend.eval.gate --run specs/eval/pr_report.json
echo $?   # 0 = pass
```

---

## Phase 6: Eval History + Chứng Minh Gate

**Mục tiêu:** Lưu lịch sử eval; chứng minh gate bắt regression thật.

**Handbook M3-B2 · Maintain + noise**

- [x] Lưu mỗi lần chạy vào `specs/eval/history/<timestamp>_<sha>.json`
- [x] Chạy full eval 3 lần trên cùng commit → ghi σ (variance nền)
- [x] Calibrate `drop_tolerance` nếu cần (σ + buffer)
- [x] **Drill:** Sửa prompt tạm bỏ ràng buộc injection → gate **exit 1**
- [x] **Drill:** Revert prompt → gate **exit 0**
- [ ] Cập nhật baseline: `specs/eval/v5_baseline.json` nếu cải thiện

**Xong khi:** Có ≥ 1 file history; drill gate pass/fail đã ghi trong `change-log.md`.

**Test:**
```bash
python -m backend.eval.run_detailed
python -m backend.eval.gate --run specs/eval/v5_baseline.json
```

---

## Phase 7: Cost Baseline

**Mục tiêu:** Đo cost/token trước khi bật cache.

**Handbook M3-B3 · Bước 1**

- [x] Tạo `src/backend/infra/cost/tracker.py` — hàm `record_cost(...)`
- [x] Gắn tracker vào lớp gọi LLM (`ai_client.py` / completion)
- [x] Tag mỗi request: `feature`, `model`, `prompt_version`, `cache_hit=false`
- [x] Tạo `resources/eval/replay_faq.yaml` (~50 câu, ~30% trùng/gần giống)
- [x] Script `scripts/cost_baseline.py` — chạy replay **không cache**, ghi tổng cost + token

**Xong khi:** Có file báo cáo baseline (vd. `specs/eval/cost_baseline.md`) với số liệu cụ thể.

**Test:**
```bash
python scripts/cost_baseline.py
```

---

## Phase 8: Cache Tầng 1 (Exact)

**Mục tiêu:** Cache exact-match; key có `prompt_version`.

**Handbook M3-B3 · Bước 2**

- [x] Tạo `src/backend/infra/cache/exact.py`
- [x] Cache key = hash(`prompt_name`, `prompt_version`, `model`, `normalized_question`)
- [x] TTL 24h — MVP: in-memory hoặc SQLite (không Redis)
- [x] Bọc lớp gọi LLM: check cache → miss thì gọi → store
- [x] Test: cùng câu hỏi 2 lần → lần 2 `cache_hit=true`
- [x] Test: bump `prompt_version` → cache miss (không trả câu cũ)

**Xong khi:** Replay FAQ lần 2 có hit rate > 0 trên câu trùng.

**Test:**
```bash
pytest tests/test_agents.py -v -k cache
python scripts/cost_baseline.py --with-cache tier1
```

---

## Phase 9: Cache Tầng 2 + Báo Cáo Cost

**Mục tiêu:** Semantic cache đơn giản + bảng so sánh cost.

**Handbook M3-B3 · Bước 3–4**

- [x] Tạo `src/backend/infra/cache/semantic.py` (MVP đơn giản)
  - [x] Embed câu hỏi sau `rewrite_node`
  - [x] Ngưỡng cosine ≥ 0.93
  - [x] Bỏ qua câu có ngày/giá động
- [x] Script `scripts/cache_benchmark.py` — bảng 3 dòng:
  - [x] Không cache
  - [x] Chỉ tầng 1
  - [x] Tầng 1 + 2
- [x] Manual audit: soát 10 semantic hit — ghi false hit (nếu có)
- [x] Lưu báo cáo: `specs/eval/cache_benchmark.md`

**Xong khi:** Bảng cost trước/sau có số liệu trên **cùng** tập replay.

---

## Phase 10: Docker & SSE Hardening

**Mục tiêu:** Xác minh patterns production cho container và streaming.

**Handbook M3-B4**

- [x] Kiểm tra SSE dừng khi client disconnect (`chat.py`)
- [x] Kiểm tra retry 429/timeout — backoff + jitter (`ai_client.py`)
- [x] Xác minh `LLM_SEMAPHORE` giới hạn concurrent calls
- [x] Rà Dockerfile: non-root, HEALTHCHECK, `.dockerignore` gọn
- [x] Rà nginx: `proxy_buffering off` cho SSE
- [x] Script `scripts/benchmark_sse.py` — 50 request, đo p50/p95
- [x] Ghi kết quả: `specs/eval/sse_benchmark.md` (semaphore 5 vs 20)

**Xong khi:** `docker compose up --build` healthy; benchmark documented.

**Test:**
```bash
docker compose up --build -d
curl http://localhost:8000/health
curl http://localhost:3000/api/v1/chat/stream   # smoke thủ công
pytest tests/test_api.py tests/test_system.py -v
```

---

## Phase 11: Deploy Demo + Smoke Test

**Mục tiêu:** Public URL demo an toàn; smoke test tự động.

**Handbook M3-B5 · MVP = ngrok**

- [x] Tạo `deploy/smoke.py`
  - [x] `GET /health` → ok
  - [x] 1 câu hỏi FPT có đáp án biết trước
- [x] Xác minh ngrok + Docker Compose (cập nhật README nếu thiếu)
- [x] Tạo `src/backend/shared/secrets.py` — local đọc `.env`; stub GCP
- [x] Tạo template `deploy/nginx-portfolio-watch.conf` (SSE buffering off)
- [ ] *(Tùy chọn)* Template `deploy/llm-app.service` + `startup.sh`

**Xong khi:** Smoke pass local; ngrok URL stream được; không secret trong repo/image.

**Test:**
```bash
python deploy/smoke.py --url http://localhost:8000
ngrok http 3000
python deploy/smoke.py --url https://<ngrok-url>
```

---

## Phase 12: GitHub Actions CI + Eval Gate

**Mục tiêu:** PR đổi prompt/agent phải pass lint, test, eval subset.

**Handbook M3-B6**

- [x] Tạo `.github/workflows/ci.yml`
  - [x] Prompt lint
  - [x] `pytest tests/ -q` (mock LLM)
- [x] Tạo `.github/workflows/eval-gate.yml`
  - [x] Trigger: `resources/prompts/**`, `src/backend/**`, `resources/eval/**`
  - [x] Chạy eval subset + gate
  - [x] Cache `.eval_cache`
- [x] Document branch protection trong README
- [x] **Drill:** PR test — sửa prompt phá injection → gate đỏ
- [ ] *(Tùy chọn)* `cd.yml` + rollback `.lkg`

**Xong khi:** Workflow chạy trên PR; drill gate đỏ/xanh đã ghi nhận.

---

## Phase 13: Observability + Playbook

**Mục tiêu:** Trace sampling, cost log, 1 incident playbook đã diễn tập.

**Handbook M3-B7**

- [x] Mở rộng `infra/monitoring/tracing.py`
  - [x] `should_sample()`: 100% lỗi/guardrail/chậm, ~5% bình thường
  - [x] Spans: guardrail, rewrite, supervisor, price, news, chart, composer
- [x] Redact PII (SĐT, email) trước export trace
- [x] Script `scripts/cost_dashboard.py` — cost, p95, cache hit rate
- [x] Viết `resources/docs/incident-playbook-cost-spike.md`
- [x] Viết `resources/docs/incident-playbook-jailbreak.md`
- [x] Diễn tập 1 incident — ghi log vào `change-log.md`

**Xong khi:** 1 trace chat đủ spans; dashboard ≥ 3 metric; 1 drill documented.

---

## Phase 14: Capstone — Tích Hợp & Feedback Loop

**Mục tiêu:** Pipeline M3 end-to-end; HITL → golden draft; rollback drill.

**Handbook M3-B8**

- [x] Viết `resources/docs/m3-production-pipeline.md` (Mermaid diagram)
- [x] Tạo `scripts/hitl_to_golden_draft.py`
  - [x] Đọc thumbs-down từ `resources/data/hitl_feedback.json`
  - [x] Xuất draft YAML case để review
- [x] Checklist production-ready → cập nhật `specs/mvp-status-report.md`
- [x] Diễn tập rollback 1 trục (prompt alias **hoặc** image tag)
- [x] Chạy full eval v5; lưu baseline cuối chu kỳ M3
- [x] Rà "đường nối":
  - [x] Cache key có `prompt_version`
  - [x] Eval trigger đủ paths trong CI
  - [x] Smoke có câu hỏi thật, không chỉ `/health`

**Xong khi:** Diagram khớp thực tế; ≥ 1 HITL draft case; full eval ≥ 85%, injection/out_of_scope 100%.

**Test:**
```bash
pytest tests/ -v
python -m backend.eval.run_detailed
python -m backend.eval.gate --run specs/eval/v5_baseline.json
docker compose up --build -d
python deploy/smoke.py --url http://localhost:8000
```

---

## Lệnh Kiểm Tra Theo Phase

| Phase | Lệnh chính |
| :---: | :--- |
| 1–3 | `pytest tests/test_agents.py -v` · `python -m backend.infra.llm.prompt_lint resources/prompts/` |
| 4–6 | `python -m backend.eval.run --subset` · `python -m backend.eval.gate --run <json>` |
| 7–9 | `python scripts/cost_baseline.py` · `python scripts/cache_benchmark.py` |
| 10 | `docker compose up --build -d` · `pytest tests/test_api.py -v` |
| 11 | `python deploy/smoke.py --url http://localhost:8000` |
| 12 | Push PR → xem GitHub Actions |
| 13–14 | Full eval + smoke + rollback drill |
