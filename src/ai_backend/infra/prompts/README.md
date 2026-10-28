# Prompts (code)

| llm-engineer-demo | vn-stock-swarm |
|-------------------|----------------|
| `app/prompts/registry.py` | `ai_backend/infra/prompts/registry.py` |
| `app/prompts/lint.py` | `ai_backend/infra/prompts/lint.py` |
| `app/prompts/templates.py` (fallback) | N/A — fallback = YAML trong `resources/prompts/` |
| LangSmith push | `scripts/prompt_rollback.py`, `resources/prompts/` git |

**Dữ liệu prompt** (YAML, alias): `resources/prompts/<name>/`.

**LLM runtime** (client, completion, stream): `ai_backend/infra/llm/`.
