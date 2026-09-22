# frontend/

UI tĩnh (HTML/JS) — Phase 2 phục vụ **cùng origin** bởi
`src.portfolio_watch.backend.main` (StaticFiles).

- `config.js`: `BACKEND_BASE_URL` mặc định `""` (same-origin)
- `PW_getBackendBaseUrl()` — override qua query `?backend=`
- V2 tách `:5173`: set `BACKEND_BASE_URL = "http://127.0.0.1:8000"` hoặc
  `python -m http.server 5173 --directory .`

Chạy gộp (khuyến nghị):

```bash
uvicorn src.portfolio_watch.backend.main:app --host 127.0.0.1 --port 8000
# mở http://127.0.0.1:8000/
```
