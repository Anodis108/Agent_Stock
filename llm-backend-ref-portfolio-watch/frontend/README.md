# frontend/

UI riêng, deploy độc lập.

## Stack (đã chốt)

**HTML + CSS + JS thuần** — không React/Vue/Vite bắt buộc ở MVP.
Phục vụ static (vd. `python -m http.server 5173` trong thư mục này).

## Config `BACKEND_BASE_URL`

Frontend **chỉ** gọi Backend — không gọi AI.

1. Sửa mặc định trong `config.js`:
   ```js
   window.PW_CONFIG = { BACKEND_BASE_URL: "http://127.0.0.1:8000" };
   ```
2. Hoặc override tạm trên URL:
   `http://127.0.0.1:5173/?backend=http://127.0.0.1:8000`
3. Code đọc qua `PW_getBackendBaseUrl()` (Phase 4 dùng để `fetch`).

Khớp biến cùng tên trong `.env.example` / Settings backend (tài liệu).

| | |
|---|---|
| Port Frontend | `5173` |
| Backend mặc định | `http://127.0.0.1:8000` |
| AI | **không** gọi thẳng |

## Files

- `index.html` — trang entry (chat, timeline, watchlist, approvals)
- `style.css` — style tối giản
- `config.js` — `PW_CONFIG` + `PW_getBackendBaseUrl`
- `app.js` — gọi Backend: `/chat`, `/scan`, `/watchlist`, `/approvals`

## Chạy (cần Backend + AI để dùng thật)

```bash
# Terminal 1 — AI :8001
# Terminal 2 — Backend :8000
# Terminal 3 — Frontend
python scripts/serve_frontend.py
# hoặc: cd frontend && python -m http.server 5173
```

Mở **http://127.0.0.1:5173/** — UI gọi `BACKEND_BASE_URL` (mặc định
`http://127.0.0.1:8000`). Không gọi AI thẳng từ browser.

## Kiểm thử tay (Phase 4)

1. Chat: hỏi «Giá FPT?» → Timeline có bước + Chat hiện câu trả lời cuối.
2. Watchlist: Thêm mã (vd. HPG) + ngưỡng → hiện trong bảng.
3. Quét mã → Timeline cập nhật; nếu có pending → Duyệt / Từ chối.

In checklist: `python scripts/phase4_manual_checklist.py`  
Smoke API (AI mock): `python -m pytest tests/test_phase4_manual_checklist.py -q`

Kiểm tự động khác:
`python -m pytest tests/test_frontend_scaffold.py tests/test_frontend_backend_wiring.py tests/test_frontend_static_serve.py -q`
