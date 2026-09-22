# backend/

Product entry (Phase 2): FastAPI phục vụ **API + static UI**.

- Routes: `/health`, `/watchlist`, `/chat`, `/scan`, `/approvals`, `/runs/…`
- UI: mount `../frontend/` tại `/`
- AI: mặc định **in-process** LangGraph (`ai_client.py`). HTTP proxy chỉ khi
  `AI_TRANSPORT=http`.

Entry: `uvicorn src.portfolio_watch.backend.main:app --port 8000`
