You are implementing Phase 12 in the repository at the cwd.

## Goal (specs/implementation-plan.md Phase 12)
GitHub Actions CI + Eval Gate (Handbook M3-B6).

## Requirements

### 1. `.github/workflows/ci.yml`
- Trigger: pull_request and push to main
- Jobs:
  - Python 3.12
  - Install: `pip install -e ".[dev]"` with PYTHONPATH=src
  - Prompt lint: `python -m backend.infra.llm.prompt_lint resources/prompts/`
  - Unit tests: `PYTHONPATH=src pytest tests/ -q` (mock LLM — no API keys required)
- Do NOT run full eval in ci.yml (that's eval-gate.yml)

### 2. `.github/workflows/eval-gate.yml`
- Trigger: pull_request only
- Path filters (skip if only README/docs changed):
  - `resources/prompts/**`
  - `src/backend/**`
  - `resources/eval/**`
- Jobs when triggered:
  - Cache `.eval_cache` keyed by hash of `resources/prompts/**` (use actions/cache)
  - Set env: PYTHONPATH=src, LLM_BACKEND=openai
  - Use secrets: OPENAI_API_KEYS (from GitHub secret), LLM_MODEL=gpt-4o-mini
  - Run eval subset (20 cases):
    `python -m backend.eval.run --subset --skip-agent-eval --json specs/eval/pr_report.json --report specs/eval/pr_report.md`
  - Run gate:
    `python -m backend.eval.gate --run specs/eval/pr_report.json`
  - Upload artifacts: pr_report.json, pr_report.md
  - Gate failure must fail the job (exit 1)

### 3. README.md
Add section "CI/CD & Branch Protection" documenting:
- ci.yml runs on every PR (lint + pytest)
- eval-gate.yml runs only when prompts/backend/eval paths change
- Recommended branch protection: require ci + eval-gate checks
- Required GitHub secret: OPENAI_API_KEYS
- How to run drill locally: `python scripts/eval_gate_drill.py`

### 4. Tests
Add `tests/test_ci_workflows.py` (or extend tests/test_system.py) to verify:
- `.github/workflows/ci.yml` and `eval-gate.yml` exist
- YAML contains expected steps: prompt_lint, pytest, eval subset, gate
- Path filters present in eval-gate

### 5. Drill documentation
Run `python scripts/eval_gate_drill.py` and note results in specs/change-log.md entry.
Also add brief drill note in README or reference existing script.

### 6. Mark complete
Update specs/implementation-plan.md Phase 12 items to [x] (except optional cd.yml + rollback .lkg).

## Existing commands (use exactly)
```bash
python -m backend.infra.llm.prompt_lint resources/prompts/
PYTHONPATH=src pytest tests/ -q
python -m backend.eval.run --subset --json specs/eval/pr_report.json --report specs/eval/pr_report.md
python -m backend.eval.gate --run specs/eval/pr_report.json
python scripts/eval_gate_drill.py
```

## Constraints
- Minimal diff; match repo style
- Do not modify unrelated files
- Do not implement optional cd.yml unless trivial
- Do not commit secrets
- Run relevant tests after changes

## Output
List files created/changed and verification commands run.
