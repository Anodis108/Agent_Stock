# MVP Status Report — Portfolio Watch & Chat Agent

**Ngày báo cáo:** 2026-09-17  
**Đối chiếu:** `specs/product-spec.md`, `specs/implementation-plan.md`,  
`specs/test-plan.md`  
**Trạng thái tổng:** MVP **hoàn thành** theo checklist Phase 1–10 (không còn
`- [ ]` trong `implementation-plan.md`).

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
- Observability dashboard (LangFuse tuỳ chọn, không bắt buộc)
- CI chạy eval mọi PR
- A/B testing / hosted prompt registry

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

## How to run locally

Chi tiết: [README.md](../README.md) mục **Chạy local**.

```bash
cd llm-backend-ref-portfolio-watch
python -m pip install -U pip
pip install -e .
cp .env.example .env          # điền OPENAI_API_KEYS nếu dùng LLM OpenAI
python -m src.portfolio_watch.main
```

- UI + API: **http://127.0.0.1:8000/** (port **8000**)
- Health: http://127.0.0.1:8000/health
- Frontend = static `web/` mount bởi FastAPI — **không** cần `npm`

Seed watchlist nếu trống:

```bash
curl -X POST http://127.0.0.1:8000/watchlist -H "Content-Type: application/json" -d "{\"symbol\":\"FPT\",\"threshold_pct\":3.0}"
```

---

## How to demo with ngrok

Chi tiết: [README.md](../README.md) mục **Demo with local** (§ ngrok).

Vì UI và API **cùng origin** trên cổng 8000, chỉ cần **một** tunnel:

```bash
# Terminal 1
python -m src.portfolio_watch.main

# Terminal 2
ngrok http 8000
```

Mở URL HTTPS ngrok in ra. Giữ `API_BASE = ""` trong `web/app.js` (cùng host).
Không cần tunnel backend riêng trừ khi tách process/port (không phải kiến trúc MVP hiện tại).

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

## Kết luận

MVP theo `product-spec.md` và toàn bộ Phase 1–10 trong `implementation-plan.md`
đã **đạt checklist**. Có thể demo local (và ngrok một tunnel) theo README.
Ưu tiên tiếp theo là vận hành (cron lifespan, baseline eval thật, CI nhẹ),
không phải feature cốt lõi còn thiếu trong scope MVP.
