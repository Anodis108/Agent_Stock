"""OpenAI client factory — Bài 1 (Section 1 + 6) + Buổi 2 (Local Serving).

Bọc việc tạo client vào một chỗ. Phần còn lại của app chỉ gọi `get_client()`
mà không cần biết đang nói chuyện với OpenAI Cloud hay model local.

Bài 1 — NGUYÊN TẮC BẢO MẬT: key đọc từ env qua settings, KHÔNG hardcode/commit.
Buổi 2 — LOCAL SERVING: chọn backend qua LLM_BACKEND. Ollama/vLLM cũng dùng
OpenAI-compatible API nên chỉ khác `base_url` + `api_key` (key giả cho local).
Key rotation chỉ áp dụng khi backend cần key thật (OpenAI Cloud).

Module II — `base_llm()` trả LangChain `ChatOpenAI` cho ToolNode / bind_tools (Bài 2–6).
Text thuần, structured, stream không qua LangChain → dùng `completion.*` (OpenAI SDK).
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI
import httpx

from ai_backend.infra.llm.backends import get_backend
from ai_backend.infra.llm.resilience import RotatingKeyPool
from common.settings import settings

# Lazy: chỉ tạo pool khi backend cần key thật.
_pool: RotatingKeyPool | None = None


def _get_pool() -> RotatingKeyPool:
    global _pool
    if _pool is None:
        _pool = RotatingKeyPool(settings.api_keys)
    return _pool


def _resolve_base_url(default_base_url: str) -> str | None:
    """LLM_BASE_URL (nếu đặt) > mặc định backend > None (SDK → OpenAI Cloud)."""
    if settings.llm_base_url:
        return settings.llm_base_url
    return default_base_url or None


def _api_key_for_backend(backend_name: str) -> str:
    backend = get_backend(backend_name)
    if backend.requires_real_key:
        return _get_pool().get_key()
    return backend.dummy_key


def get_client() -> OpenAI:
    """Trả về OpenAI client trỏ tới backend đang cấu hình.

    - openai: key kế tiếp trong pool (round-robin).
    - ollama/vllm: key giả, không cần pool.
    """
    name = settings.llm_backend.strip().lower()
    backend = get_backend(name)
    base_url = _resolve_base_url(backend.default_base_url)
    api_key = _api_key_for_backend(name)
    http_client = httpx.Client(trust_env=False)
    return OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)


def mark_current_key_limited(client: OpenAI, cooldown_seconds: float = 60.0) -> None:
    """Đưa key của `client` vào cooldown sau khi gặp 429.

    No-op với backend local (không dùng key thật nên không có gì để cooldown).
    """
    backend = get_backend(settings.llm_backend)
    if backend.requires_real_key and client.api_key:
        _get_pool().mark_limited(client.api_key, cooldown_seconds)


def base_llm():
    """Client LangChain chưa bind tool — cùng backend/settings với `get_client()`.

    Không cache: mỗi lần gọi lấy key mới từ pool (khớp rotation SDK path).
    ReAct: `.bind_tools()`, `.ainvoke()`, `.with_structured_output()`.
    """
    from langchain_openai import ChatOpenAI

    name = settings.llm_backend.strip().lower()
    backend = get_backend(name)
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=_api_key_for_backend(name),
        base_url=_resolve_base_url(backend.default_base_url),
    )


def bind_tools_llm(tools: list[Any]):
    """ReAct worker: base_llm + tool binding (tránh lặp _worker_llm trong từng graph)."""
    return base_llm().bind_tools(tools)
