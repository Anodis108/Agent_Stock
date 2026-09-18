# Phase 8 — Langfuse E2E report

**Date:** 2026-09-18  
**Item:** `MONITORING_ENABLED=true` + valid keys → 1 chat → 1 root + agent spans

## How verified

1. Automated (always): `python -m pytest tests/test_phase8_langfuse_e2e.py -q`
   - FE calls Backend `/chat` (not AI `/v1`)
   - Backend returns `request_id` for correlation
   - AI `/v1/chat` with monitoring on → root `chat` + child spans
2. Live: `python scripts/phase8_langfuse_e2e.py` (Langfuse host from `.env`)
3. Manual UI: `python scripts/phase8_langfuse_e2e.py --print-checklist`

## Live run result (2026-09-18)

| Field | Value |
|-------|--------|
| Result | **PASS** |
| request_id | `phase8-e2e-20260918-082046` |
| HTTP | 200, answer present |
| trace_id | `263a251adab2a85ebb3dab9d834343d2` |
| root observation | name=`chat`, id=`08d0a88e5873c4d6` |
| spans | `chat`, `rewrite_question`, `supervisor`, `price_news_fetch`, `answer_composer` |

Log: `specs/eval/phase8_langfuse_e2e_run.log`

## Notes

- Spans are created on the **AI** process; UI path is Frontend → Backend → AI.
- Langfuse v4 `events_only`: read via SDK `api.observations.get_many` (v2 observations), not legacy `/api/public/traces`.
- Open Langfuse UI (e.g. `LANGFUSE_HOST`) and search by time / span name `chat` / `request_id`.

## AC mapping

| Criterion | Status |
|-----------|--------|
| product-spec AC6: 1 chat + monitoring → 1 trace on Langfuse | Pass (live) |
| test-plan §4: true + keys → 1 request = 1 trace + agent spans | Pass |
| test-plan acceptance map: Langfuse trace evidence in report | Pass (this file) |
