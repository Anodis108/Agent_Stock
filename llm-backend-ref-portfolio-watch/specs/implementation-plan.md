# Implementation Plan — V3

**Nền:** V2 done (monorepo, graph, Langfuse cơ bản, Docker 3 service).  
**Mục tiêu:** `specs/product-spec.md`.  
**Quy tắc:** chỉ **một** phase / lần; không code ngoài checklist đang mở.

```
Browser → App (:8000) → LangGraph + agents
              ↘ Langfuse (:3000, ngoài compose)
              ↘ Qdrant (optional)
```

Tham chiếu: `../llm-engineer-demo/app/agent_pr/`,  
`Lesson17/Class 18 - LLM Evaluation Pipelines.pdf`.

---

## Phase 1 — Project setup (baseline V3)

Chốt docs + baseline — **không** đổi hành vi.

- [x] Chạy `docker compose up --build`; xác nhận 1 chat + 1 quét OK.
- [x] Ghi `specs/eval/v3_baseline.json` (điểm hiện tại, version dataset, scorer flags).
- [x] Change-log: quyết định 1 app Docker, memory+TTL, UI Claude+graph, Class 18.
- [x] README: mục «V3 in progress» trỏ product-spec + plan này.
- [x] AGENTS.md: 1 phase / lần; không code ngoài checklist.

**Xong khi:** baseline + docs có; V2 vẫn chạy.

---

## Phase 2 — Gộp entry app (reuse backend)

- [x] Một FastAPI entry: mount static UI + routes watchlist / chat / scan / approvals.
- [x] Gọi LangGraph **nội bộ** (không bắt buộc HTTP sang service AI riêng).
- [x] Reuse code store/routes từ `src/portfolio_watch/backend/` — không viết service mới.
- [x] Endpoint `/health` trả 200.

**Xong khi:** `uvicorn` một process phục vụ UI + API (dev hoặc container).

---

## Phase 3 — Docker product 1 service

- [x] `docker-compose.yml`: service chính `app` (port 8000).
- [x] Optional service `qdrant` (profile hoặc comment rõ).
- [x] Gỡ / ngừng bắt buộc 3 service `frontend` + `backend` + `ai`.
- [x] Volume SQLite — ghi path trong change-log.
- [x] Healthcheck compose cho `app`.

**Xong khi:** `docker compose up --build` → một URL product chính.

---

## Phase 4 — Clean code chết

- [x] Chốt 1 nguồn agent (`agents/` *hoặc* `domain/agents/` — ghi change-log).
- [x] Xóa stub / `web/` cũ / import không dùng.
- [x] `pytest` smoke (Docker) không fail vì path cũ.

**Xong khi:** không còn path chết trong README/compose.

---

## Phase 5 — Prompt tối giản

- [x] Rút mỗi prompt: role + schema/ràng buộc + an toàn; bỏ ví dụ dài.
- [x] Một nơi đăng ký prompt (giữ hoặc rút gọn registry hiện có).
- [x] Chạy subset golden: `lookup` + `injection` — không tụt quá tolerance.

**Xong khi:** subset pass; change-log liệt kê prompt đã rút.

---

## Phase 6 — Structured output

- [x] Schema Pydantic (hoặc tương đương) cho: rewrite, supervisor, classifier,
      eval, synthesis draft, memory extract.
- [x] LLM path dùng structured output / parse schema — không dựa free-text thuần.
- [x] Schema lỗi → retry/guard; **không** crash graph.
- [x] Pytest tối thiểu 1 path rewrite + 1 path supervisor.

**Xong khi:** test structured pass.

---

## Phase 7 — Memory short-term + TTL

- [x] Short-term history/messages + sliding window (env cấu hình được).
- [x] TTL / freshness phút (env); ghi `.env.example`.
- [x] Follow-up trong session nhớ mã/ngữ cảnh trong window.
- [x] Pytest short-term + expiry/freshness.

**Xong khi:** test short-term pass.

---

## Phase 8 — Memory long-term

- [x] `recall_memory` đầu chat; `store_memory` cuối chat (pattern agent_pr).
- [x] Qdrant optional + fallback in-memory khi không có Qdrant/key.
- [x] Không `user_id` → bỏ qua long-term, không crash.
- [x] Pytest có/không `user_id`; fallback.

**Xong khi:** test long-term pass; chat Docker ổn.

---

## Phase 9 — Langfuse: 1 request = 1 trace

- [x] Đúng 1 root `trace_request` / chat đến END.
- [x] Đúng 1 root / scan đến END.
- [x] Mỗi graph node = span tên = node id; mọi step con có **input + output**.
- [x] `MONITORING_ENABLED=false` → no-op, chat 200.
- [x] Pytest mock hierarchy parent/child.

**Xong khi:** mock test pass; checklist thủ công ghi trong change-log (nếu có host).

---

## Phase 10 — Core UI chat (Claude-like)

- [x] Layout: cột trái hội thoại; composer dưới.
- [x] Gửi câu hỏi → hiện câu trả lời (reuse API chat hiện có).
- [x] Trạng thái lỗi mạng / timeout hiện rõ trên UI.
- [x] Desktop demo dùng được (không cần mobile hoàn hảo).

**Xong khi:** demo thủ công 1 câu hỏi–đáp trên Docker.

---

## Phase 11 — Live graph + hover I/O

- [x] Panel phải: node theo `steps[]` (hoặc event tương đương).
- [x] Node sáng lần lượt khi chạy.
- [x] Hover node → hiện input + output của bước đó.
- [x] API/response đủ field I/O cho UI (nếu thiếu thì bổ sung contract).

**Xong khi:** 1 chat thấy node sáng + hover có I/O.

---

## Phase 12 — Market status page

- [ ] Trang/tab **Market status**.
- [ ] Liệt kê mã đang watchlist / vừa quét: giá, % đổi, trạng thái, thời gian.
- [ ] Nối dữ liệu thật từ store/API (không mock cứng trên UI).
- [ ] Lỗi tải dữ liệu hiện message rõ.

**Xong khi:** mở trang thấy mã đang check.

---

## Phase 13 — Connect UI ↔ product data

- [ ] Chat / graph / market / watchlist / HITL cùng origin app (Phase 2–3).
- [ ] Quét + approve/reject hoạt động từ UI mới.
- [ ] Không gọi AI service tách (nếu đã gộp).

**Xong khi:** flow A–C trong product-spec chạy trên một URL.

---

## Phase 14 — Diagram agent

- [ ] Intent “vẽ sơ đồ” → node/agent `diagram_agent` (hoặc nhánh supervisor).
- [ ] Output Mermaid hoặc graph JSON.
- [ ] UI render sơ đồ trong bubble hoặc panel.
- [ ] Structured output cho plan sơ đồ (nếu dùng LLM).

**Xong khi:** câu “vẽ sơ đồ luồng scan …” hiện sơ đồ trên UI.

---

## Phase 15 — Golden dataset Class 18

- [ ] `specs/eval/golden_v3.yaml`: `version`, mỗi case có `id` + `slice`.
- [ ] Slice: `lookup`, `comparison`, `out_of_scope`, `injection`, `diagram` (≥3 case).
- [ ] Rule-based `must_include` / `must_not_include`.
- [ ] Runner aggregate **overall + by_slice**.
- [ ] Gate: injection **100%**; regression vs `v3_baseline` + tolerance.

**Xong khi:** `docker compose run --rm app python -m …eval…` in được by_slice.

---

## Phase 16 — Validation, errors, docs close

- [ ] UI: lỗi API / timeout / HITL fail không làm trắng trang.
- [ ] `.env.example`: memory, Langfuse, freshness, Qdrant (optional).
- [ ] README **chỉ** Docker product + eval trong container.
- [ ] Status report: section «V3 complete» khi AC product-spec 1–9 tick.
- [ ] Demo ngắn trong README: chat → graph hover → market → (tuỳ chọn) Langfuse.

**Xong khi:** acceptance criteria product-spec đều đạt.

---

## Thứ tự & phụ thuộc

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16
```

| Phase | Cần xong trước |
|---|---|
| 2–3 | 1 |
| 4–5 | 3 |
| 6 | 4 |
| 7–8 | 6 |
| 9 | 3 + 6 |
| 10 | 3 |
| 11 | 9 + 10 (I/O span + UI) |
| 12 | 3 |
| 13 | 10–12 |
| 14 | 6 + 11 |
| 15 | 5 + 14 |
| 16 | 15 |

**Một lần chỉ mở 1 phase.**
