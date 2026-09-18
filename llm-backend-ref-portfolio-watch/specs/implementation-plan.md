# Implementation Plan — Quality Loop + Split FE/BE/AI

Nền tảng: MVP multi-agent đã có (`src/portfolio_watch/`, golden dataset,
`scripts/run_eval.py`). Vòng này **tách Frontend / Backend / AI**, siết
chất lượng từng case, hiện bước trên UI, và trace Langfuse.

Nguyên tắc:

- Frontend chỉ gọi Backend; Backend chỉ gọi AI qua HTTP.
- Sửa chất lượng = sửa multi-agent / prompt — không nới scorer.
- Một phase (hoặc một golden case) tại một thời điểm.
- Tham khảo eval/tracing: `../llm-engineer-demo` (ý tưởng, không copy nguyên file).

Kiến trúc mục tiêu:

```
frontend/     # UI — chat, timeline bước, watchlist, approvals
backend/      # API sản phẩm — proxy AI, CRUD, stream bước
AI service    # src/portfolio_watch (hoặc ai/) — multi-agent + eval hooks
```

Chi tiết agent: `specs/agents.md`. Lịch sử MVP: `specs/mvp-status-report.md`.

---

## Phase 1 — Project setup

- [x] Chốt cấu trúc thư mục: `frontend/`, `backend/`, AI giữ
      `src/portfolio_watch/` (hoặc đổi tên `ai/` — ghi quyết định vào
      change-log).
- [x] `.env.example`: thêm `AI_BASE_URL`, `BACKEND_BASE_URL` (hoặc
      `VITE_`/`API` tương ứng), `APP_HOST_PORT` nếu cần; giữ
      `OPENAI_API_KEYS`, Langfuse vars.
- [x] README skeleton: sẽ chạy 3 process (port ví dụ AI `8001`, Backend
      `8000`, Frontend `5173`) — lệnh chi tiết điền ở Phase 6.
- [x] Chạy baseline eval hiện tại (`scripts/run_eval.py`), lưu
      `specs/eval/baseline_debug.json`, ghi pass/fail theo slice vào
      change-log — **chưa sửa agent**.
- [x] Nâng eval: port ý tưởng `task_success` + `trajectory` từ
      llm-engineer-demo; hỗ trợ `--case-id` chạy **một case**.
- [x] AI (trong process hiện tại hoặc stub) trả `steps[]` tối thiểu cho
      chat (tên bước + thứ tự) để sau này UI/trajectory dùng được.

## Phase 2 — Core UI

- [x] Tạo `frontend/` (HTML/JS tối giản hoặc stack nhẹ — ghi vào
      change-log).
- [x] Trang chính gồm: ô chat, **timeline bước** (placeholder), watchlist,
      danh sách chờ duyệt (approvals).
- [x] Timeline: hiển thị list bước với trạng thái
      `pending | running | done | error` (data giả / hardcode trước).
- [x] Config `BACKEND_BASE_URL` (chưa gọi API thật cũng được ở phase này).
- [x] Chạy frontend độc lập (dev server hoặc static) — xác nhận mở được UI.

## Phase 3 — Core backend or data logic

**3a — AI service & chất lượng**

- [x] Tách AI thành process riêng (port riêng): `POST /v1/chat`,
      `POST /v1/scan`, `GET /health`; response có kết quả cuối + `steps[]`.
- [x] Gỡ phục vụ static UI khỏi process AI.
- [x] Debug golden **từng case**: fail → sửa multi-agent/prompt → chạy lại
      cùng case → pass mới sang case khác.
      (đã chạy full skip-judge+task_success; sửa fail đầu `lookup_15`;
      còn comparison_* → mục «Pass hết slice».)
- [x] Pass hết slice: lookup → comparison → out_of_scope → injection
      (injection **100%**).
- [x] Báo cáo: số case pass; liệt kê thay đổi agent/prompt.

**3b — Backend sản phẩm (chưa nối UI)**

- [x] Tạo `backend/`: health, watchlist CRUD, approvals, proxy
      `chat`/`scan` tới `AI_BASE_URL`.
- [x] Endpoint trả / stream bước (SSE hoặc trả đủ `steps` one-shot MVP).
- [x] **Không** import `domain.agents` — chỉ HTTP client tới AI.
- [x] CORS cho origin frontend (có thể tạm `* ` lúc dev).

**3c — Backlog multi-agent** (điền thêm khi debug case fail)

- [x] (gợi ý) Supervisor routing câu hỏi đa ý / đa mã.
- [x] (gợi ý) Luôn có evidence giá trước khi so sánh %.
- [x] (gợi ý) Rewrite/memory với đại từ (“mã đó”).
- [x] (gợi ý) Guardrail không làm mất grounding khi viết lại câu trả lời.
- [x] Rà soát backlog (2026-09-18): không có gap multi-agent mới —
      `specs/eval/blocked_cases.yaml` → `blocked: []`; Phase 5 regression
      30/30, injection 100%. Không thêm task ảo.

Khi case fail chưa sửa được hệ thống: thêm dòng `- [ ] …` ngay dưới đây
+ entry trong `blocked_cases.yaml` (kèm `phase3c_task`). Không nới scorer.

## Phase 4 — Connect UI to data, backend to frontend

- [x] Frontend gọi Backend cho: chat, scan, watchlist, approvals (bỏ mock).
- [x] Chat: Backend forward AI → Frontend nhận câu trả lời cuối.
- [x] Timeline: cập nhật theo `steps` / sự kiện stream từ Backend (không
      gọi thẳng AI từ browser).
- [x] Watchlist + approvals: CRUD / approve / reject qua Backend; dữ liệu
      thật (SQLite phía AI hoặc Backend — ghi rõ nơi lưu trong change-log).
- [x] Kiểm thử tay: hỏi 1 câu → thấy bước + trả lời; thêm mã → quét →
      duyệt (nếu có cảnh báo chờ).

## Phase 5 — Validation and error states

- [x] Backend: input lỗi (câu rỗng, symbol invalid, ngưỡng âm) → 4xx rõ.
- [x] AI down / timeout → Backend trả lỗi có message; Frontend hiện thông
      báo, không treo.
- [x] Stream/steps lỗi giữa chừng → timeline đánh `error` trên bước đó.
- [x] Approvals: approve/reject id không tồn tại hoặc đã xử lý → lỗi rõ,
      không đổi state sai.
- [x] Eval: không nới scorer; case fail phải sửa hệ thống hoặc ghi blocked
      + task 3c.
- [x] Regression: full golden sau khi nối FE/BE — không tụt quá tolerance
      trong test-plan; injection vẫn 100%.

## Phase 6 — Local run instructions

- [x] README: prerequisites (conda `dong312` hoặc venv, `.env`).
- [x] Ba lệnh chạy: AI → Backend → Frontend (kèm port mặc định).
- [x] Biến môi trường bắt buộc / tuỳ chọn (bảng ngắn).
- [x] Lệnh eval một case và full golden.
- [x] Troubleshooting: thiếu key, port trùng, AI unreachable, CORS.

## Phase 7 — Local demo setup

- [x] Kịch bản demo local (không cần internet công cộng): mở Frontend URL,
      seed watchlist, chat 1 câu (thấy timeline), quét 1 mã, duyệt nếu có.
- [x] (Tuỳ chọn) `docker compose` 2–3 service (AI + Backend ± Frontend
      static) — ghi lệnh `up` / `down` / xem log.
- [x] Xác nhận trên máy sạch (hoặc env `dong312`): làm đúng README là demo
      được 3 luồng chính.
- [x] Ghi change-log: port, volume DB, quyết định compose.

**Đóng Phase 7 (2026-09-18):** quyết định Docker / image base
`python:3.12-slim`, tag `portfolio-watch:split`, 3 service — chi tiết
bảng port/volume trong `specs/change-log.md`.

## Phase 8 — Tracing with Langfuse

- [x] AI: mỗi `chat`/`scan` → 1 trace cha; mỗi bước agent → span con
      (pattern llm-engineer-demo `tracing.py`).
- [x] Propagate `request_id` (hoặc tương đương) Backend → AI → metadata
      Langfuse.
- [x] `MONITORING_ENABLED=false` hoặc thiếu key → chat vẫn OK (no-op).
- [x] `true` + key hợp lệ: 1 chat từ UI → thấy trace đủ span trên Langfuse.
- [x] README: bật monitoring, mở Langfuse, tìm trace theo câu hỏi /
      request id.
- [x] `.env.example` cập nhật đủ biến Langfuse.

---

## Thứ tự thực hiện

`1 → 2 → 3 → 4 → 5 → 6 → 7 → 8`

Ghi chú: trong Phase 3, làm **3a (AI + golden)** đủ ổn trước khi khóa
contract; 3b Backend có thể song song nhẹ sau khi `/v1/chat` + `steps[]`
đã có. Phase 8 có thể prototype sớm trên AI, nhưng **đóng phase** sau khi
UI→Backend→AI đã nối (sau Phase 4).
