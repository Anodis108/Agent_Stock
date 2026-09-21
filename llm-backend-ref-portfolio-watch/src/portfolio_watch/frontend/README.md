# frontend/

UI static HTML + JS — chat, watchlist, quét, approvals timeline.

- Port **5173** (compose `frontend` service)
- `config.js`: `BACKEND_BASE_URL` (mặc định `http://127.0.0.1:8000`)
- `PW_getBackendBaseUrl()` — override qua query `?backend=`
