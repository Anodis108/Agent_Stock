"""Prompt management — git YAML registry (tương tự `app/prompts/` trong llm-engineer-demo).

- **Code**: package này (`registry`, `lint`, `experiment`).
- **Dữ liệu prompt**: `resources/prompts/<name>/vN.yaml` + `production.txt` (không nằm dưới `src/`).
"""

from ai_backend.infra.prompts.experiment import pick_prompt_version
from ai_backend.infra.prompts.registry import (
    PRODUCTION_LLM_PROMPT_NAMES,
    Prompt,
    PromptRegistry,
    get_system_prompt,
    registry,
    resolve_prompts_dir,
)

__all__ = [
    "PRODUCTION_LLM_PROMPT_NAMES",
    "Prompt",
    "PromptRegistry",
    "get_system_prompt",
    "pick_prompt_version",
    "registry",
    "resolve_prompts_dir",
]
