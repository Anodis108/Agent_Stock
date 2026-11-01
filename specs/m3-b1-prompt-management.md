# M3-B1 Prompt Management — Design + checklist

Date: 2026-11-01  
Approach: **1** — git-based registry; wire hot-path hardcodes; delete orphan YAML.  
Status: **done** (Phase 7 ticked in `implementation-plan.md`; see `change-log.md`).

## Goal

Satisfy Module III Bài 1 on this codebase:

- No hot-path system prompts hardcoded in agent graphs/nodes
- ≥2 versions + changelog where we already have A/B (`answer_compose`, `rewrite_question`)
- Change production via `production.txt` only
- Rollback = revert alias / commit
- Keep `scripts/compare_prompt_versions.py` working
- Clear unused folders under `resources/prompts/`

**Not in scope:** LangSmith Hub (demo pattern), CI/CD, Batch API, observability.

## Current state

Already present: `PromptRegistry` (`get` / `render` / alias), lint, `pick_prompt_version`, compare/rollback scripts.

Already wired via registry: `event_classification`, `synthesis_alert`, `diagram_plan`, `memory_fact`, `eval_judge`, `eval_task_success`, `eval_trajectory`.

Still hardcoded:

| Location | Constant |
|----------|----------|
| `chat/nodes.py` | `_REWRITE_SYSTEM`, `_FINAL_ANSWER_SYSTEM` |
| `multi_agent/hierarchical.py` | `_FINAL_ANSWER_SYSTEM` |
| `chat/graph.py` | `CHAT_SUPERVISOR_SYSTEM` |
| `scan/graph.py` | `SCAN_SUPERVISOR_SYSTEM` |
| `price_agent` / `news_agent` / `eval_agent` / `db_agent` / `draw_agent` `graph.py` | `SYSTEM_PROMPT` |

Orphan / unused YAML (no production caller): `supervisor_routing`, `news_agent_react` (old ReAct), `eval_severity`.

## Design

### Keep

- `src/ai_backend/infra/prompts/{registry,lint,experiment}.py`
- Scripts: `compare_prompt_versions.py`, `prompt_rollback.py`
- Swarm stays **git YAML** (not LangSmith like llm-engineer-demo).

### Wire

| Prompt name | Action |
|-------------|--------|
| `rewrite_question` | Update `v1`/`v2` template = current `_REWRITE_SYSTEM` |
| `answer_compose` | Update templates = current `_FINAL_ANSWER_SYSTEM` |
| `chat_supervisor` | YAML body = current `CHAT_SUPERVISOR_SYSTEM` |
| `scan_supervisor` | YAML body = current `SCAN_SUPERVISOR_SYSTEM` |
| `price_agent` | **Create** `v1.yaml` + `production.txt` |
| `news_agent` | **Create** (do not reuse `news_agent_react`) |
| `eval_agent` | **Create** |
| `db_agent` | **Create** |
| `draw_agent` | **Create** |

Call sites: `get_system_prompt(name)` / `registry().get(..., version="production")`.

### Delete under `resources/prompts/`

- `supervisor_routing/`
- `news_agent_react/`
- `eval_severity/`

### Follow-up

- Refresh `PRODUCTION_LLM_PROMPT_NAMES`
- Sentinel `resolve_prompts_dir` stays on `event_classification`
- Fix tests (`test_chart` supervisor_routing); README prompts; compare script if needed

### Verification

- `python -m ai_backend.infra.prompts.lint resources/prompts/`
- Targeted pytest (prompt rollback, module3 features, chart)
- Grep: no leftover hot-path hardcode constants listed above

## Out of scope

- `GREETING_RESPONSE` (static UX, not versioned LLM prompt)
- LangSmith parity with demo
