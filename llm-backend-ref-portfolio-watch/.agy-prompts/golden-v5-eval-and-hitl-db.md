# Task: Golden v5 eval bundle + HITL SQLite enrichment

Repository: `d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/llm-backend-ref-portfolio-watch`

## Part A — Golden v5 eval runner with timestamped artifacts

Create `scripts/run_golden_v5_eval_bundle.py` that:
1. Runs detailed eval on `resources/eval/golden_v5.yaml` via `backend.eval.run_detailed.run_detailed_evaluation`
2. Writes timestamped outputs under `specs/eval/runs/<YYYYMMDD-HHMMSS>/`:
   - `eval_results.json` (full machine-readable, copy from run_detailed output)
   - `eval_results.md` (human-readable report)
   - `summary.json` with: run_id, timestamp, dataset path, total_cases, passed, failed, pass_rate, slice breakdown
3. Also updates latest symlinks/copies at `specs/eval/eval_results_golden_v5.json` and `.md` (keep existing behavior)
4. CLI flags: `--limit`, `--slice`, `--case-id`, `--skip-judge`, `--skip-agent-eval`, `--delay`
5. Print final paths on stdout

Add minimal test in `tests/test_eval.py` (or new `tests/test_eval_bundle.py`) that mocks runner and verifies output directory structure (no live LLM).

## Part B — HITL human feedback in local SQLite (enhance existing)

Existing: UI thumbs/stars in `src/frontend/app.js`, API `src/backend/api/routers/hitl.py`, table `hitl_evaluations`, JSON export `resources/data/hitl_feedback.json`.

Enhance so feedback is fully usable from DB without joining messages:
1. Migration in `src/backend/database/connection.py`: add nullable columns `question TEXT`, `answer TEXT` to `hitl_evaluations` if missing
2. Update `HITLEvaluationRepository` in `repositories.py`: accept/store `question`, `answer` on create; include in list/get
3. Update `hitl_service.record_hitl_telemetry` and `_create_feedback_record` in hitl router to persist question+answer into SQLite row (not only JSON file)
4. Extend `FeedbackOut` API model with optional `question`, `answer`
5. Create `scripts/export_hitl_feedback.py`:
   - Reads from SQLite (`SQLITE_PATH` env)
   - Exports to `resources/data/hitl_feedback_export.json` and `.csv`
   - Columns: id, timestamp, session_id, message_id, question, answer, rating, is_positive, reason, user_feedback
   - `--limit`, `--session-id`, `--output-dir`
6. Add test in `tests/test_api.py` verifying question/answer stored in DB after feedback POST

## Constraints
- Minimal diff; match existing style
- Do NOT change swarm/chat logic
- UTF-8 safe on Windows
- Run: `PYTHONPATH=src pytest tests/test_api.py tests/test_eval.py -q -k "hitl or eval_bundle or golden_v5"` after changes

## Verify eval (smoke, no full 40-case run in agent)
```bash
PYTHONPATH=src python scripts/run_golden_v5_eval_bundle.py --limit 2 --skip-judge --skip-agent-eval
```

Output: list files changed, how user runs full eval, how user exports HITL feedback.
