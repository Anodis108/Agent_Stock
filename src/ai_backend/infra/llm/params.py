"""Generation parameters cho chat completions."""

from __future__ import annotations


from common.settings import settings
from pydantic import BaseModel


class GenerationParams(BaseModel):
    temperature: float = settings.llm_temperature
    max_completion_tokens: int = settings.llm_max_completion_tokens
    top_p: float = settings.llm_top_p

    def to_openai_kwargs(self) -> dict:
        return self.model_dump()


DETERMINISTIC = GenerationParams(temperature=0.0)
BALANCED = GenerationParams(temperature=0.5)
CREATIVE = GenerationParams(temperature=0.9)
