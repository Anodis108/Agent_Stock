"""ChatOpenAI cho ReAct — chỉ vì bind_tools; app/llm native SDK không có.

Key + backend (Ollama/vLLM) lấy từ get_client(). Không cache: mỗi lần một key.
Khi 429: cooldown key rồi thử lại (giống completion.py).
"""

from __future__ import annotations

import random
import time

from typing import Any

from openai import RateLimitError

from app.config import settings
from app.llm.client import get_client, mark_current_key_limited
from app.monitoring.tracing import record_usage, trace_step


def base_llm(client=None, model: str | None = None):
    from langchain_openai import ChatOpenAI

    client = client or get_client()
    kwargs = {
        "model": model or settings.llm_model,
        "temperature": settings.llm_temperature,
        "api_key": client.api_key,
        "max_retries": 0,
    }
    if getattr(client, "base_url", None):
        kwargs["base_url"] = str(client.base_url)
    return ChatOpenAI(**kwargs)


def invoke_with_tools(messages, tools=None, parent_span=None, model: str | None = None, turn: str = ""):
    """model=None dùng settings.llm_model — truyền vào để áp Model Routing (Bài 8).
    turn: khi có, cộng dồn token/cost vào Cost Tracking (Bài 8/13) — xem monitoring.tracing.record_usage."""
    n = settings.llm_max_retries
    used_model = model or settings.llm_model
    with trace_step(parent_span, "llm.bind_tools", input=messages, model=used_model) as t:
        last: Any = None
        for i in range(n):
            client = get_client()
            llm = base_llm(client, used_model)
            if tools:
                llm = llm.bind_tools(tools)
            try:
                last = llm.invoke(messages)
                t["output"] = getattr(last, "content", None) or str(last)
                usage = getattr(last, "usage_metadata", None)
                t["usage"] = usage
                if turn and usage:
                    record_usage(
                        turn,
                        used_model,
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                return last
            except RateLimitError:
                mark_current_key_limited(client)
                if i == n - 1:
                    raise
                time.sleep(2**i + random.uniform(0, 1))
        return last
