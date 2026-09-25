# frontend/

UI tĩnh (HTML/JS) — phục vụ **cùng origin** bởi
`backend.main` (StaticFiles).

- `config.js`: `BACKEND_BASE_URL` mặc định `""` (same-origin)
- `PW_getBackendBaseUrl()` — override qua query `?backend=`

Chạy gộp (khuyến nghị):

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
# mở http://127.0.0.1:8000/
```
