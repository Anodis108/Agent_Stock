You are implementing Phase 14 (Capstone — M3-B8) in the repository at cwd.

## Goal (specs/implementation-plan.md Phase 14)

### 1. `resources/docs/m3-production-pipeline.md`
Mermaid diagram of M3 end-to-end loop matching actual codebase:
- prompt registry (resources/prompts/) → eval (backend.eval) → gate → deploy (Docker/ngrok) → monitor (Langfuse/tracing) → HITL feedback → golden draft
Reference real paths: `.github/workflows/`, `deploy/smoke.py`, `scripts/hitl_to_golden_draft.py`, cache tiers, CI eval-gate

### 2. `scripts/hitl_to_golden_draft.py`
- Read `resources/data/hitl_feedback.json` (list of records)
- Filter thumbs-down: `is_positive == false` OR `rating <= 2`
- For each, emit draft YAML case to `resources/eval/drafts/hitl_draft_<id>.yaml`
- Case format must match golden_v5.yaml structure:
  ```yaml
  - id: hitl_draft_<short_id>
    question: "..."
    expected: "From HITL feedback: ..."
    slice:
      type: lookup  # infer from question or default lookup
      difficulty: medium
    must_include: []
    must_not_include: []
    metadata:
      source: hitl
      original_feedback: "..."
  ```
- CLI: `--input PATH`, `--output-dir PATH`, `--dry-run`
- If hitl_feedback.json missing, create sample at resources/data/hitl_feedback.sample.json for demo AND document in script help
- Include at least 1 sample negative entry in sample file so script produces ≥1 draft

### 3. Update `specs/mvp-status-report.md`
Add Phase 8-14 M3 production-ready section with checklist:
- Phases 1-14 status table (update from old Phases 1-7 only)
- Connection audit results (cache prompt_version, CI paths, smoke FPT)
- Capstone deliverables status

### 4. Rollback drill (prompt alias axis)
Document in specs/change-log.md a simulated rollback drill:
- Scenario: bad prompt alias `production` points to broken version
- Action: revert alias in resources/prompts/ or registry to previous version
- Verify: prompt_lint + eval gate subset pass
Do NOT break production prompts — simulate only in change-log prose + optional `resources/docs/rollback-drill-prompt-alias.md` short doc

### 5. Full eval baseline
- Verify `specs/eval/v5_baseline.json` exists; if gate passes on it, document in change-log
- Run: `PYTHONPATH=src python -m backend.eval.gate --run specs/eval/v5_baseline.json` (no live eval needed if baseline exists)
- Optionally copy/tag as M3 final baseline in change-log

### 6. Connection audit (verify in code/tests, document in mvp-status-report)
- Cache key includes prompt_version: grep exact.py / semantic.py / completion.py — assert in test
- CI eval-gate paths: resources/prompts, src/backend, resources/eval in eval-gate.yml
- Smoke has real FPT question: deploy/smoke.py POST /chat

### 7. Tests — `tests/test_capstone.py`
- test_hitl_to_golden_draft_from_sample (tmp hitl json → ≥1 yaml draft)
- test_pipeline_doc_exists
- test_v5_baseline_gate_passes (gate on specs/eval/v5_baseline.json)
- test_connection_audit_cache_prompt_version (exact cache key function)
- test_connection_audit_ci_paths (reuse pattern from test_ci_workflows or read eval-gate.yml)
- test_connection_audit_smoke_fpt_question (read deploy/smoke.py)

### 8. Mark complete
Update specs/implementation-plan.md Phase 14 all items [x]

## Existing references
- golden case format: resources/eval/golden_v5.yaml
- HITL record shape: src/backend/services/hitl_service.py (is_positive, rating, question, user_feedback)
- Gate: src/backend/eval/gate.py
- v5 baseline: specs/eval/v5_baseline.json

## Constraints
- Minimal diff; match repo style
- Do not run full 40-case live eval (too slow/costly) — use existing v5_baseline.json for gate proof
- Keep tests fast (mock/subprocess only)
- Run: PYTHONPATH=src pytest tests/test_capstone.py -v

## Output
List files changed and test results.
