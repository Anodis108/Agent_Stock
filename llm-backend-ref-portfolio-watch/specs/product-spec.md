# Product Spec — Portfolio Watch V3

## App goal

Web app **theo dõi cổ phiếu VN + chat multi-agent**, chạy product bằng Docker:

- User chat kiểu Claude, bên phải thấy **từng node đang chạy**; hover xem input/output.
- Mỗi câu hỏi tạo **đúng 1 Langfuse trace** (đủ bước đến khi xong).
- Quét watchlist, cảnh báo + HITL; trang trạng thái các mã đang theo dõi.
- Có thể trả lời yêu cầu **vẽ sơ đồ**; chất lượng giữ bằng golden dataset (Class 18).

V3 dựa trên V2 đã xong — tinh gọn UI, observability, memory, eval; không viết lại
toàn bộ nghiệp vụ từ đầu.

## Target users

| Vai trò | Mục tiêu |
|---|---|
| **Người demo** | `docker compose up --build` → chat, xem graph live, xem trạng thái mã, duyệt cảnh báo |
| **Developer** | Sửa từng agent theo phase; chạy 1 golden case; mở Langfuse kiểm tra 1 trace |

Không có đăng nhập hay multi-tenant ở vòng này.

## Core user flow

### A. Chat hỏi–đáp

1. Mở UI → thấy hội thoại (trái) và panel graph (phải), composer phía dưới.
2. Gõ câu hỏi (vd. “Giá FPT hôm nay?” hoặc “Vẽ sơ đồ luồng scan”).
3. Gửi → các node trên panel phải **sáng lần lượt** theo bước thật.
4. Hover một node → hiện **input** và **output** của bước đó.
5. Nhận câu trả lời cuối; nếu là yêu cầu vẽ sơ đồ → sơ đồ hiện trên UI.
6. (Tuỳ chọn) Mở Langfuse → **1 root trace** cho lần gửi đó, expand thấy đủ node + I/O.

### B. Trạng thái mã đang check

1. Mở trang / tab **Market status**.
2. Xem danh sách mã watchlist / vừa quét: giá, % đổi, trạng thái
   (normal / abnormal / chờ duyệt), thời gian cập nhật.

### C. Giám sát & duyệt cảnh báo

1. Thêm mã + ngưỡng vào watchlist.
2. Bấm quét → hệ thống lấy giá + tin → phân loại bình thường / bất thường.
3. Bất thường → đánh giá → soạn cảnh báo → tự gửi **hoặc** chờ duyệt (HITL).
4. User approve / reject trên UI.

### D. Siết chất lượng (developer)

1. Chọn **một** case trong golden dataset (có nhãn slice).
2. Chạy eval trong Docker → xem pass/fail **tổng** và **theo slice**.
3. Fail → sửa agent/prompt (không nới scorer) → chạy lại cùng case.

## Features in scope

- Chat UI gần Claude + panel graph live (hover = input/output từng node).
- Trang Market status cho mã đang theo dõi / vừa quét.
- Agent/node vẽ sơ đồ khi user yêu cầu; UI render sơ đồ.
- Watchlist, quét, HITL Gate 1 & 2 (giữ từ V2).
- **Một** app Docker: UI + API + LangGraph cùng product (reuse code `backend/`,
  không tách service backend như V2).
- Structured output cho vòng LLM/agent cần quyết định có cấu trúc.
- Memory short-term (window + TTL/freshness) + long-term (recall/store; Qdrant
  hoặc fallback) — pattern `llm-engineer-demo`.
- Prompt tối giản, một nơi đăng ký.
- Langfuse: 1 request = 1 trace; tên node rõ; mọi span có input + output;
  tắt monitoring vẫn chat được.
- Golden dataset version hoá + slice (lookup, comparison, out_of_scope,
  injection, diagram); report có `by_slice`; injection pass 100%.
- README chỉ hướng dẫn Docker + eval trong container.

## Features out of scope

- Đăng nhập, phân quyền, multi-tenant.
- Email / push notification thật.
- Đóng gói full stack Langfuse (Postgres, ClickHouse, …) vào `docker-compose`
  product — Langfuse UI vẫn chạy riêng tại `:3000`.
- Fine-tune model, RAG tài liệu dài, thêm nhiều nguồn giá/tin.
- Graph editor kéo-thả trên UI.
- Bắt buộc CI chạy full golden mọi PR.
- Chạy product bằng nhiều process uvicorn local làm đường chính
  (**product = Docker**).

## Acceptance criteria

1. **`docker compose up --build`** mở được UI; chat, market status, quét và duyệt
   HITL chạy end-to-end.
2. **Chat UI:** panel phải hiện node lần lượt; hover một node thấy input/output
   khớp bước vừa chạy.
3. **Langfuse:** 1 request chat (và scan) → đúng 1 root trace; tên node đọc được;
   mỗi node chính có input + output; `MONITORING_ENABLED=false` vẫn chat OK.
4. **Structured output:** các quyết định LLM có schema; có test chứng minh parse /
   validate được.
5. **Memory:** short-term + long-term + TTL/freshness hoạt động; không `user_id`
   thì bỏ qua long-term không crash; không Qdrant thì fallback.
6. **Kiến trúc:** không còn container/service `backend` tách; API + UI cùng app
   product (reuse store/routes cũ).
7. **Golden / eval:** dataset có version + slice; report có `by_slice`; injection
   **100%**; regression không tụt quá tolerance so với baseline V3.
8. **Diagram:** câu yêu cầu vẽ sơ đồ hiện sơ đồ trên UI.
9. **Docs:** README chỉ Docker product + lệnh eval trong container; prompt ngắn
   hơn V2 mà regression vẫn trong tolerance.

---

Chi tiết triển khai: `specs/implementation-plan.md`.  
Cách chấm: `specs/test-plan.md`.  
Tham chiếu: `Lesson17/Class 18 - LLM Evaluation Pipelines.pdf`,
`../llm-engineer-demo/app/agent_pr/`.
