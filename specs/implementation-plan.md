# Implementation Plan — VN Stock Swarm

Làm đúng một ô checklist mỗi lần. Phase trước tick hết rồi mới sang phase sau. Xong một ô thì tick ô đó và ghi `specs/change-log.md`.

Đợt này tách `src/backend` thành `src/web_backend` và `src/ai_backend`, rồi public từ máy này. Không viết lại swarm, UI, golden v6, cache, hay HITL. Không tạo lại `src/ai` hay `src/web`. Không thuê cloud.

## 1. Project setup

- [x] Tạo `src/shared`: đọc `config.yaml` và model JSON của `/v1/chat`, `/v1/chat/stream`, `/v1/scan`.
- [x] Tạo `src/web_backend` với entry `web_backend.main:app`.
- [x] Tạo `src/ai_backend` với entry `ai_backend.app:app`.
- [x] `pyproject.toml` nhận ba package trên. `src/backend` vẫn còn cho đến phase 3.

Kiểm: `pytest tests/unit/test_config.py -q`

## 2. Core UI

- [x] Trang chat vẫn một màn hình, vẫn chọn User A, User B, Default.
- [x] Câu trả lời vẫn hiện từng token trong khung chat hiện có.
- [x] Tên file nguồn, nút thích, không thích, đã copy, hỏi lại, và bỏ dở vẫn ở cạnh câu trả lời.

Kiểm: mở `http://localhost:8000`, gửi một câu, thấy chữ hiện dần và các nút cũ còn đó.

## 3. Core backend or data logic

- [x] Session, tin nhắn, watchlist, holdings, và HITL nằm trong `web_backend`. Postgres giữ nguyên.
- [x] Swarm, retrieval, và Qdrant nằm trong `ai_backend`. AI chỉ `/health`, `/v1/chat`, `/v1/chat/stream`, `/v1/scan`.
- [x] Hai cây không import lẫn nhau. Chỉ dùng `src/shared` cho phần chung.
- [x] Xóa `src/backend` khi hai entry trên chạy được.

Kiểm: `pytest tests/unit/test_concept_rag.py tests/e2e/test_docker_setup.py -q`

## 4. Connect UI to data

- [x] Compose build hai Dockerfile mới. Web gọi `AI_BASE_URL`. Postgres, Qdrant, Redis, MinIO giữ container riêng.
- [x] Web chỉ chuyển SSE từ AI ra UI.
- [x] Câu số liệu hoặc danh mục kèm watchlist và holdings. Câu khái niệm không kèm hai danh sách đó.
- [x] "RSI là gì" có tên file nguồn. "RSI của HPG" đi agent chỉ báo.

Kiểm: `pytest tests/unit/test_ai_http_stream.py tests/unit/test_concept_rag.py -q`

## 5. Validation and error states

- [x] Import `web_backend.main` không kéo `openai`, `answer_question`, hay `ai_backend`.
- [x] Câu chào không gọi agent giá. Injection và câu ngoài phạm vi vẫn bị từ chối.
- [x] Không đủ đoạn khái niệm thì câu trả lời là `Không có trong tài liệu.`
- [x] Client ngắt stream thì pipeline dừng. Nút thích và không thích vẫn ghi PostgreSQL.
- [x] `pytest tests/` pass, không gọi internet, không tạo file `.db`.

Kiểm: `pytest tests/unit/test_config.py tests/unit/test_greeting_fastpath.py tests/unit/test_guardrails.py tests/unit/test_concept_rag.py -q`

## 6. Local run instructions

- [x] `src/deploy/nginx.conf` chỉ `listen 80`, proxy về `127.0.0.1:8000`. Route `/chat` tắt `proxy_buffering`. Không có block 443.
- [x] `src/deploy/release.ps1` có `up`, `smoke`, `rollback`, `status`. Không gọi `gcloud`. Không dùng systemd.
- [x] README nói cách chạy hai cây và `release.ps1` trên máy này.

Kiểm: `pytest tests/integration/test_system.py -q` và đọc `release.ps1`.

## 7. ngrok demo setup

- [x] README vẫn có demo ngrok cho cổng 8000, và cổng 3001 khi chạy Docker.
- [x] `src/deploy/publish.ps1` chạy Cloudflare Tunnel vào nginx cổng 80.
- [x] URL https in ra trả `GET /health` 200. Một câu khái niệm trên URL đó vẫn có tên file nguồn.

Kiểm: làm theo README, mở URL https, gửi "RSI là gì".
