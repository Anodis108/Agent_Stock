"""Backend presets — Ollama/vLLM dùng OpenAI-compatible API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Backend:
    name: str
    default_base_url: str  # "" = SDK mặc định (OpenAI Cloud)
    requires_real_key: bool
    dummy_key: str = "not-needed"


BACKENDS: dict[str, Backend] = {
    "openai": Backend(
        name="openai",
        default_base_url="",
        requires_real_key=True,
    ),
    "ollama": Backend(
        name="ollama",
        default_base_url="http://localhost:11434/v1",
        requires_real_key=False,
        dummy_key="ollama",
    ),
    "vllm": Backend(
        name="vllm",
        default_base_url="http://localhost:8000/v1",
        requires_real_key=False,
        dummy_key="vllm",
    ),
}


def get_backend(name: str) -> Backend:
    key = name.strip().lower()
    if key not in BACKENDS:
        raise ValueError(
            f"LLM_BACKEND='{name}' không hợp lệ. "
            f"Chọn một trong: {', '.join(BACKENDS)}."
        )
    return BACKENDS[key]
