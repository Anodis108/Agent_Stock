"""Generation parameters cho chat completions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.shared.settings import settings


@dataclass(slots=True)
class GenerationParams:
    temperature: float = settings.llm_temperature
    max_completion_tokens: int = settings.llm_max_completion_tokens
    top_p: float = settings.llm_top_p

    def to_openai_kwargs(self) -> dict:
        return asdict(self)


DETERMINISTIC = GenerationParams(temperature=0.0)
BALANCED = GenerationParams(temperature=0.5)
CREATIVE = GenerationParams(temperature=0.9)
