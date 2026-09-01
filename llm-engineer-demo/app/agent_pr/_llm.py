"""ChatOpenAI cho ReAct — chỉ vì bind_tools; app/llm native SDK không có.

Key + backend (Ollama/vLLM) lấy từ get_client(). Không cache: mỗi lần một key.
Khi 429: cooldown key rồi thử lại (giống completion.py).
"""

from __future__ import annotations

import random
import time

from openai import RateLimitError

from app.config import settings
from app.llm.client import get_client, mark_current_key_limited


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


def invoke_with_tools(messages, tools=None):
    n = settings.llm_max_retries
    for i in range(n):
        client = get_client()
        llm = base_llm(client)
        if tools:
            llm = llm.bind_tools(tools)
        try:
            return llm.invoke(messages)
        except RateLimitError:
            mark_current_key_limited(client)
            if i == n - 1:
                raise
            time.sleep(2**i + random.uniform(0, 1))
