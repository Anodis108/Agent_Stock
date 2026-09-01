"""LLM client — ChatOpenAI cho ReAct (bind_tools). Offline mode khi thiếu API key / đang pytest."""

from __future__ import annotations

import os

from app.config import settings


def use_offline_tools() -> bool:
    """Không key, hoặc đang pytest: giả 1 tool_call — không gọi OpenAI thật."""
    return (not settings.openai_api_key) or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def base_llm():
    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "api_key": settings.openai_api_key,
    }
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return ChatOpenAI(**kwargs)


def invoke_with_tools(messages, tools=None):
    llm = base_llm()
    if tools:
        llm = llm.bind_tools(tools)
    return llm.invoke(messages)
