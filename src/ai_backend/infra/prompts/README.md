# Prompts (code)

| llm-engineer-demo | vn-stock-swarm |
|-------------------|----------------|
| LangSmith Hub definitions/push | Git YAML `resources/prompts/<name>/vN.yaml` + `production.txt` |
| `app/prompts/registry.py` | `ai_backend/infra/prompts/registry.py` |
| `app/prompts/lint.py` | `ai_backend/infra/prompts/lint.py` |
| A/B sticky | `experiment.py` (`pick_prompt_version`) |

Hot-path load: `get_system_prompt(name)` (alias `production`).

**Names (M3-B1):** `rewrite_question`, `answer_compose`, `chat_supervisor`, `scan_supervisor`, `price_agent`, `news_agent`, `eval_agent`, `db_agent`, `draw_agent`, plus eval/scan helpers (`event_classification`, `synthesis_alert`, `diagram_plan`, `memory_fact`, `eval_*`).

Rollback: `scripts/prompt_rollback.py`. Compare v1/v2: `scripts/compare_prompt_versions.py`.
