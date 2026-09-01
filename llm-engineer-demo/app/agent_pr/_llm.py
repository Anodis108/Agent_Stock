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
from app.monitoring.tracing import trace_step


def base_llm(client=None):
    from langchain_openai import ChatOpenAI

    client = client or get_client()
    kwargs = {
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "api_key": client.api_key,
        "max_retries": 0,
    }
    if getattr(client, "base_url", None):
        kwargs["base_url"] = str(client.base_url)
    return ChatOpenAI(**kwargs)


def invoke_with_tools(messages, tools=None, parent_span=None):
    n = settings.llm_max_retries
    with trace_step(
        parent_span, "llm.bind_tools", input=messages, model=settings.llm_model
    ) as t:
        last: Any = None
        for i in range(n):
            client = get_client()
            llm = base_llm(client)
            if tools:
                llm = llm.bind_tools(tools)
            try:
                last = llm.invoke(messages)
                t["output"] = getattr(last, "content", None) or str(last)
                t["usage"] = getattr(last, "usage_metadata", None)
                return last
            except RateLimitError:
                mark_current_key_limited(client)
                if i == n - 1:
                    raise
                time.sleep(2**i + random.uniform(0, 1))
        return last
