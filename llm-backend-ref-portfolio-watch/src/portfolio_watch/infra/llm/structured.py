"""Structured output utilities — schema validation, JSON parsing, retry & guard."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from src.portfolio_watch.infra.llm.params import DETERMINISTIC, GenerationParams

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)
Messages = list[ChatCompletionMessageParam]

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_str(text: str) -> str:
    """Trích xuất khối JSON từ chuỗi text (hỗ trợ markdown codeblock và raw JSON)."""
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    match = _JSON_BLOCK_RE.search(s)
    return match.group(0) if match else s


def parse_structured(raw_or_obj: Any, schema: type[TModel]) -> TModel:
    """Parse và validate dữ liệu (đối tượng, dict, string JSON) thành instance của Pydantic schema."""
    if isinstance(raw_or_obj, schema):
        return raw_or_obj

    if isinstance(raw_or_obj, dict):
        return schema.model_validate(raw_or_obj)

    if isinstance(raw_or_obj, str):
        cleaned = extract_json_str(raw_or_obj)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return schema.model_validate(data)
        except json.JSONDecodeError:
            pass
        return schema.model_validate_json(cleaned)

    if hasattr(raw_or_obj, "model_dump"):
        return schema.model_validate(raw_or_obj.model_dump())

    return schema.model_validate(raw_or_obj)


def call_llm_structured(
    messages: Messages,
    schema: type[TModel],
    *,
    chat_fn: Callable[..., str] | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
    params: GenerationParams | None = None,
    max_retries: int = 1,
) -> TModel:
    """Gọi LLM với structured output:
    1. Ưu tiên chat_parsed_fn nếu được inject.
    2. Dùng chat_fn nếu được inject (test / fake string), validate schema.
    3. Production: gọi chat_parsed; nếu lỗi thì thử chat() + parse_structured.
    4. Tự động retry khi gặp lỗi schema validation hoặc parse JSON.
    """
    params = params or DETERMINISTIC
    last_exc: Exception | None = None
    from src.portfolio_watch.infra.llm.completion import chat, chat_parsed

    for attempt in range(max_retries + 1):
        try:
            if chat_parsed_fn is not None:
                res = chat_parsed_fn(messages, schema, params)
                return parse_structured(res, schema)

            if chat_fn is not None:
                raw_text = chat_fn(messages, params)
                return parse_structured(raw_text, schema)

            # Production mặc định
            try:
                return chat_parsed(messages, schema, params)
            except Exception as e:
                logger.warning("chat_parsed gặp lỗi, thử fallback chat() + schema validate: %s", e)
                raw_text = chat(messages, params)
                return parse_structured(raw_text, schema)
        except (ValidationError, ValueError, json.JSONDecodeError, Exception) as exc:
            last_exc = exc
            logger.warning(
                "Structured output attempt %d/%d thất bại (%s): %s",
                attempt + 1,
                max_retries + 1,
                schema.__name__,
                exc,
            )
            if attempt < max_retries:
                continue
            raise

    if last_exc is not None:
        raise last_exc
    raise ValueError(f"Không thể parse output khớp schema {schema.__name__}.")
