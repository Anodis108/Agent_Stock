# MVP Status Report — Portfolio Watch & Chat Agent

**Ngày báo cáo:** 2026-09-22  
**Đối chiếu:** `specs/product-spec.md`, `specs/implementation-plan.md`,  
`specs/test-plan.md`  
**Trạng thái tổng:** V3 (Phase 16) hoàn thành.

---

## Completed features

### Theo product-spec (In Scope + AC)

| Hạng mục | Trạng thái |
|----------|------------|
| API Quét ngay (`POST /scan`) — giá, tin, phân loại, eval/synthesis/gate khi bất thường | Done |
| Watchlist + ngưỡng; cảnh báo pending / đã gửi theo confidence | Done |
| HITL Gate 1 — approve/reject cảnh báo + ghi lý do reject | Done |
| HITL Gate 2 — đề xuất đổi ngưỡng/watchlist luôn chờ duyệt | Done |
| Chat API (`POST /chat`) — hỏi mã trong watchlist, không HITL | Done |
| Guardrail chặn lời khuyên mua/bán chắc chắn | Done |
| Prompt Registry git-based — đổi `production` → agent đổi hành vi | Done |
| Golden dataset 30 case (18/6/3/3) + `scripts/run_eval.py` (rule + judge + report + regression + injection gate 100%) | Done |
| `scripts/draw_agent_graph.py` → `docs/agent_graph.mmd` / `.png`, `--verify` khớp `agents.md` | Done |
| UI 1 trang: Chat / Watchlist+Quét / Approvals | Done |
| SQLite stores (watchlist, history, memory) + ConsoleNotifier | Done |
| Docker Compose demo 1 URL | Done |
| Cron/scan watchlist (script / API; interval không gắn lifespan mặc định) | Done (có lệnh quét thủ công) |

### Theo implementation-plan

- **Phase 1–7:** skeleton, UI, domain/app/API, validation, README local, Docker — `[x]`
- **Phase 8:** prompts + PromptRegistry + wire 7 LLM agent — `[x]`
- **Phase 9:** golden + eval pipeline + baseline — `[x]`
- **Phase 10:** StateGraph visualize + verify + README — `[x]`

Smoke gần đây: `test_product_spec_ac`, phase dates, graph verify — **pass**.

---

## Missing features

### Trong MVP (không còn checklist mở)

Không còn mục unchecked trong `implementation-plan.md`.

### Ngoài phạm vi MVP (đúng product-spec Out of Scope)

- Multi-tenant / auth thật
- Email / push thật (chỉ console/DB notifier)
- Nhiều nguồn giá/tin
- Fine-tune / RAG dài hạn
- Observability dashboard (LangFuse tuỳ chọn, không bắt buộc - V3 có cơ chế fallback tắt vẫn chạy)
- CI chạy eval mọi PR
- A/B testing / hosted prompt registry
- Qdrant long-term memory (tuỳ chọn - V3 fallback bỏ qua nếu không có)

### Khoảng trống vận hành (không chặn AC checklist, nên biết)

- Scheduler cron **chưa** gắn sẵn vào `main.py` lifespan — quét định kỳ cần
  script/API hoặc gắn thêm sau.
- Baseline eval v1 = rule-based + stub answer (`skip_judge`); lần chạy
  LLM/`answer_question` thật nên `--save-baseline` lại.
- PNG sơ đồ phụ thuộc mạng (mermaid.ink); MMD offline luôn có.

---

## Known bugs / hạn chế

| Mức | Mô tả |
|-----|--------|
| Thấp | LangGraph `draw_mermaid()` gộp cạnh → `__end__`; docs dùng `architecture_mermaid()` trung thực — đã xử lý cho verify. |
| Thấp | Nguồn giá/tin ngoài mạng có thể chậm/lỗi tạm — soft-fail đã có; UI hiện lỗi. |
| Thấp | Substring guardrail có thể khớp nhầm cụm kiểu “lời khuyên mua…” trong câu phủ định (hành vi rule-based đã biết). |
| Vận hành | Windows console đôi khi cần `PYTHONIOENCODING=utf-8` khi chạy script in tiếng Việt. |
| Không critical | Không phát hiện bug chặn AC trong lần rà này — **không sửa code**. |

---

## How to run (Docker-first)

Chi tiết: [README.md](../README.md) mục **Quick Start (Docker-first)**.
Ứng dụng ưu tiên chạy bằng Docker Compose cho môi trường product.
Việc chạy `uvicorn` local không còn là đường chính.

```bash
docker compose up --build -d
docker compose run --rm app python -m src.portfolio_watch.eval.run --self-check
```

- UI + API: **http://localhost:8000/** (port **8000**)
- Health: http://localhost:8000/health
- Frontend = static `src/portfolio_watch/frontend/` mount bởi FastAPI

Seed watchlist nếu trống:

```bash
curl -X POST http://localhost:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

---

## Recommended next improvements

1. **Gắn APScheduler vào lifespan** (opt-in bằng env) cho cron thật theo
   `SCAN_INTERVAL_MINUTES`.
2. **Baseline eval production:** chạy `python scripts/run_eval.py --run --save-baseline`
   với LLM + `answer_question` thật; ghi điểm vào change-log.
3. **Notifier email/push** phía sau interface hiện có (vẫn out-of-scope MVP
   nhưng sẵn port).
4. **CI nhẹ:** pytest + `draw_agent_graph.py --verify` + `run_eval.py --self-check`
   trên PR (eval full 30 case để nightly).
5. **Auth / multi-user** nếu demo nhiều người.
6. **Siết guardrail** (word-boundary / negation) giảm false positive.

---

## V2 complete (2026-09-19)

| Hạng mục V2 | Trạng thái |
|---|---|
| Monorepo `src/portfolio_watch/` (agents, graph, backend, frontend, eval) | Done |
| LangGraph chat + scan thật; `steps[]` từ graph | Done |
| Langfuse trace 3 cấp (root → agent → step) | Done |
| Docker product-only (`docker compose up --build`) | Done |
| Eval `python -m src.portfolio_watch.eval.run` / `regression` | Done |
| Xóa `scripts/`, root `backend/`, `frontend/` | Done |
| Golden baseline `v2_baseline.json` 30/30; injection 3/3 pass | Done |
| README demo + Langfuse + troubleshooting | Done |

Chạy: `docker compose up --build` → http://localhost:5173

---

## V3 complete (2026-09-22)

| Hạng mục V3 (AC 1-9) | Trạng thái | Evidence |
|---|---|---|
| 1. Docker E2E (UI, chat, market status, HITL) | Done | `docker-compose.yml`, README Docker quick start |
| 2. Chat UI: live graph panel + hover I/O | Done | `frontend/app.js` live graph; `tests/test_frontend.py` |
| 3. Langfuse: 1 root trace + node info (tắt vẫn chạy) | Done | `infra/monitoring/`; `MONITORING_ENABLED=false` smoke |
| 4. Structured output parse/validate | Done | Pydantic schemas; `tests/test_structured_output.py` |
| 5. Memory: short-term + long-term (TTL, fallback) | Done | `memory_store.py`; `tests/test_short_term_memory.py`, `test_long_term_memory.py` |
| 6. Single app kiến trúc (API + UI cùng product) | Done | `backend/main.py`; compose 1 service `app`; `tests/test_docker.py` |
| 7. Golden eval version/slice, `by_slice`, injection 100% | Done | `golden_v3.yaml`, `eval/run.py`, `v3_baseline.json`; Phase 15 gates |
| 8. Yêu cầu vẽ sơ đồ hiện sơ đồ trên UI | Done | `diagram_agent/`; Mermaid trong `frontend/app.js` |
| 9. Docs (README) chỉ Docker product + lệnh eval trong container | Done | `README.md`; `tests/test_readme_phase16.py` |

- **V3 notes:** Qdrant và Langfuse là các thành phần tuỳ chọn, có thể chạy dự phòng không crash.

---

## Kết luận

MVP Phase 1–10 **done**. **V2 Phase 1–16 done** — xem `specs/implementation-plan.md`.
**V3 hoàn thành** (Phase 16 done): AC 1–9, README demo walkthrough, eval in container.
