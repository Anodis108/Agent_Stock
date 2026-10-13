# Implementation Plan — VN Stock Swarm

Làm đúng một ô checklist mỗi lần. Chưa viết code cho đến khi được yêu cầu. Xong một ô thì chạy lệnh kiểm của ô đó, tick ô, và ghi `specs/change-log.md`.

App chat, swarm, golden v6, và Module III Bài 1–8 đã chạy. Các phase dưới chỉ khép lỗ trong `specs/product-spec.md`. Không xây lại UI, agent, lint, eval gate, hay cache memory.

Phase tái cấu trúc cũ (config, dọn `resources/`, dọn `scripts/`, chuyển `deploy/`, tách `src/backend/`, test 3 tầng) đã xong và nằm trong `specs/change-log.md`.

---

## 1. Project setup

- [x] App chạy bằng `uvicorn` cổng 8000 và bằng `docker compose`.
- [x] `.env` chỉ chứa secret. Tham số nằm trong `resources/configs/config.yaml`.
- [x] Test nằm ở `tests/unit/`, `tests/integration/`, `tests/e2e/`.
- [x] Thêm `llm.max_concurrency` vào `config.yaml`. Bỏ chỗ đọc giới hạn từ biến môi trường `LLM_SEMAPHORE`.
- [x] Thêm `cache.backend` với giá trị `memory` hoặc `redis`. Mặc định `memory`.
- [x] Thêm cờ bật Secret Manager trong `config.yaml`, mặc định tắt.

Kiểm: `pytest tests/unit/test_config.py -q`

## 2. Core UI

- [x] Trang chat có chọn User A, User B, Default.
- [x] Câu trả lời hiện bằng stream.
- [x] Có nút thích và không thích, gửi `/hitl/feedback`.
- [x] Thêm ba hành động trên câu trả lời: đã copy, hỏi lại, bỏ dở. Chưa cần gọi API ở phase này.

Kiểm: mở `http://localhost:8000`, gửi một câu, thấy ba hành động mới cạnh nút thích.

## 3. Core backend

- [x] `chat()` và `chat_parsed()` dùng exact cache, semantic cache, và semaphore thread.
- [x] SSE dừng khi client ngắt.
- [x] `prompt_lint.py` và eval gate đã có.
- [x] Thêm async client: `AsyncOpenAI`, retry bằng `asyncio.sleep`, semaphore asyncio lấy giới hạn từ `config.yaml`.
- [x] `chat_stream` gọi async client đó.
- [x] `chat_stream` đọc và ghi exact cache trước khi mở stream. Cùng câu và cùng `prompt_version` thì không gọi model.
- [x] Tách store `get` / `setex`. Thêm `RedisStore`, import `redis` trong `__init__`. Mặc định vẫn memory.
- [x] Thêm service `redis` trong `docker-compose.yml`.
- [x] Thêm script rollback: ghi `production.txt` về version trước, không xoá `vN.yaml`.
- [x] `should_sample` nhận `cache_hit=True` thì bỏ trace. Lỗi, guardrail, và request chậm vẫn giữ.
- [x] Khi cờ Secret Manager bật, đọc `OPENAI_API_KEYS`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` lúc chạy.

Kiểm từng ô: `pytest tests/unit/test_async_client.py tests/unit/test_redis_store.py tests/unit/test_prompt_rollback.py tests/integration/test_monitoring.py tests/unit/test_secret_manager.py -q`

## 4. Connect UI to data

- [x] Nút thích và không thích đã ghi SQLite và có thể thành draft golden.
- [x] Ba hành động copy, hỏi lại, bỏ dở gọi API feedback.
- [x] API lưu điểm từ 0 đến 1 và nhãn explicit hoặc implicit. Test không gọi Langfuse.
- [x] Luồng stream trên UI vẫn hiện chữ từng phần sau khi `chat_stream` đổi sang async client.

Kiểm: `pytest tests/unit/test_feedback_signals.py tests/integration/test_api.py -q` 

## 5. Validation and error states

- [x] Injection và câu ngoài phạm vi bị từ chối. Câu chào không gọi agent giá.
- [x] Client ngắt stream thì pipeline dừng.
- [x] Async client trả slot semaphore khi lời gọi lỗi.
- [x] Secret Manager lỗi hoặc thiếu project thì giữ giá trị `.env` và không làm app sập.
- [x] Cache hit trên stream không ghi trace.

Kiểm: `pytest tests/unit/test_async_client.py tests/unit/test_secret_manager.py tests/integration/test_monitoring.py tests/unit/test_guardrails.py -q`

## 6. Local run instructions

- [x] `README.md` có cài đặt, `uvicorn` cổng 8000, và `docker compose` (UI 3001, API 8000).
- [x] Sau phase 3, README nói rõ cache mặc định là memory và cách bật Redis.
- [x] README liệt kê secret trong `.env.example` và nói tham số nằm ở `config.yaml`.

Kiểm: làm theo README trên máy sạch đến khi mở được `http://localhost:8000`.

## 7. ngrok demo setup

- [x] `README.md` có mục "Demo with ngrok" cho cổng 8000, và cổng 3001 khi chạy Docker.
- [x] Nginx tắt `proxy_buffering` trên route stream.
- [x] `scripts/start_ngrok_demo.py` có sẵn.
- [x] Sau khi stream đi qua async client, demo ngrok vẫn nhận token dần, không đợi hết câu.

Kiểm: chạy app cổng 8000, chạy `ngrok http 8000`, gửi một câu từ URL ngrok và thấy chữ hiện dần.

---

Mọi ô checklist đã tick.
