# Refactor: Slim SwarmInput + DBAgent + MinIO chart_path

## Goals (user-approved direction)

1. **SwarmInput public API**: only `question`, `user_id`, `request_id`.
2. **Remove from HTTP/API**: `watchlist`, `holdings`, `news_days`, `limit`, `ttl_minutes`.
3. **Settings**: `news_days`, `memory_short_term_window`, `memory_short_term_ttl_minutes` from `common.settings.settings` in orchestrator → `run_chat_graph`. Add `news_days` to settings if missing (env + default 7).
4. **Watchlist/holdings**: no body snapshot; **DBAgent** (new) reads PG/repos when supervisor routes portfolio/watchlist. Reference: `other/llm-engineer-demo/app/agent_pr/db_agent/` (read tools, HITL pattern for writes — reads only for this phase).
5. **chart_path**: always MinIO public/served URL after upload; delete local temp PNG after successful MinIO put. User expects 100% MinIO in prod (`CHART_BACKEND=minio`).
6. **Remove**: transport `_attach_account_lists`, orchestrator watchlist upsert from input, `SnapshotWatchlistStore` from v1 chat body path where applicable.
7. **Tests**: fix/update affected tests; run targeted pytest.

## DBAgent scope (MVP)

- Location: `src/ai_backend/infra/agents/chat/db_agent/` (nodes + schemas; wired from `portfolio_report_agent` or supervisor when intent portfolio/watchlist).
- READ-only tools/repos: `list_watchlist(user_id)`, `list_holdings(user_id)` via existing PG/repos (same data as web DB), no LLM free SQL in MVP.
- Do not break scan cron (`PgWatchlistStore` on AI for scheduled scan).

## MinIO chart URL

- Extend `ChartObjectStore.put` or chart_agent to return HTTP URL (settings: minio public base or `/charts/{name}` proxy pattern already used — unify to one canonical form documented in code).
- After MinIO put success: `unlink` local file if created.

## Files likely touched

- `swarm_orchestrator.py`, `chat.py` router, `stream_models.py`, `common/transport/transport.py`, `v1.py`, `chart_agent.py`, `minio_store.py`, `portfolio_report_agent/nodes.py`, graph/workflow wiring, tests under `ai_backend/tests`, `tests/e2e`, `web_backend` if any.

## SDD

- Update `specs/change-log.md` after implementation.
