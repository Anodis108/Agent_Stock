# Product Spec — Portfolio Watch V2

## App goal

Xây dựng web app **theo dõi cổ phiếu VN + chat hỏi–đáp** bằng multi-agent,
dễ demo và dễ bảo trì:

- Người dùng: watchlist, quét biến động, duyệt cảnh báo, chat thấy từng bước agent.
- Developer: code sạch (1 agent = 1 folder, tham chiếu `agent_pr`), chạy product
  **chỉ bằng Docker**, trace **1 câu hỏi = 1 trace** trên Langfuse self-host `:3000`.

V2 **không viết lại nghiệp vụ** — refactor MVP đã có; golden 30 case vẫn là chuẩn
chất lượng.

## Target users

| Vai trò | Làm gì với app |
|---|---|
| **Người demo** | `docker compose up` → chat, xem timeline bước, thêm mã, quét, duyệt cảnh báo |
| **Developer** | Đọc/sửa từng agent trong `src/`; debug 1 golden case; mở Langfuse xem trace |

Không có đăng nhập hay multi-tenant ở vòng này.

## Core user flow

### 1) Chat

1. Mở Frontend → nhập câu hỏi (vd. "Giá FPT hôm nay?").
2. Frontend gọi Backend → Backend gọi AI (`POST /v1/chat`).
3. UI hiện timeline: chuẩn hoá câu hỏi → chọn agent → lấy giá/tin → soạn trả lời
   → kiểm tra an toàn.
4. Hiện câu trả lời cuối.
5. Nếu bật Langfuse: **đúng 1 trace** cho lần hỏi đó; mở trace thấy cây bước
   lồng nhau (graph node → bước con trong agent).

### 2) Giám sát & duyệt

1. Thêm mã + ngưỡng vào watchlist.
2. Bấm quét (hoặc cron) → AI lấy giá + tin → phân loại bình thường / bất thường.
3. Bất thường → đánh giá → soạn cảnh báo → tự gửi **hoặc** chờ duyệt (HITL).
4. User approve / reject trên UI (qua Backend).

### 3) Siết chất lượng (developer)

1. Chọn **một** case trong golden dataset.
2. Chạy eval trong container AI → pass/fail.
3. Fail → sửa agent/prompt (không nới điểm) → chạy lại cùng case → pass mới
   sang case tiếp.

## Features in scope

**Sản phẩm (giữ MVP):**

- Watchlist + ngưỡng cảnh báo.
- Quét 1 mã / watchlist; HITL Gate 1 (gửi cảnh báo) và Gate 2 (đổi cấu hình).
- Chat với timeline bước trên UI.

**Kiến trúc & code (V2):**

- Mỗi agent một folder dưới `src/portfolio_watch/agents/<name>/` (nodes, state,
  tools, graph nếu cần) — pattern `llm-engineer-demo/app/agent_pr`.
- Frontend + Backend + AI **đều trong `src/portfolio_watch/`**.
- LangGraph chạy orchestration thật (chat + scan).
- Ba container Docker: `frontend` `:5173`, `backend` `:8000`, `ai` `:8001`.
- Xóa `scripts/`; eval/regression qua `python -m` trong container.
- Langfuse: trace lồng nhau, tên bước rõ, mỗi span có input/output; AI kết nối
  Langfuse self-host qua `LANGFUSE_HOST=http://host.docker.internal:3000`.

## Features out of scope

- Đăng nhập, phân quyền, multi-tenant.
- Email / push notification thật.
- RAG tài liệu dài, fine-tune model, đổi hàng loạt nguồn giá/tin.
- Gói stack Langfuse (Postgres, ClickHouse, …) vào `docker-compose` — user tự
  chạy UI tại port `3000`.
- Graph editor trên UI, CI bắt buộc full golden mọi PR.
- Chạy product bằng `python scripts/serve_*.py` (sẽ bỏ hẳn sau V2).

## Acceptance criteria

1. **`docker compose up --build`** mở được 3 URL; chat, watchlist, quét, duyệt
   hoạt động end-to-end.
2. **Cấu trúc code:** mỗi agent có folder riêng trong `src/portfolio_watch/agents/`;
   Backend **không** import agents.
3. **Không còn `scripts/`**; README chỉ hướng dẫn Docker + `python -m` trong
   container cho eval.
4. **Langfuse:** 1 câu chat từ UI → 1 trace; expand thấy span graph node và span
   con bên trong agent; tắt `MONITORING_ENABLED` vẫn chat bình thường.
5. **Chất lượng:** golden regression không tụt quá tolerance; slice injection
   pass 100%.

---

Chi tiết triển khai: `specs/implementation-plan.md` (Phase 11–16).  
Mô tả agent: `specs/agents.md`. MVP đã xong: `specs/mvp-status-report.md`.
