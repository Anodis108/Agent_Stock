"""Async client: slot trả lại sau success và lỗi. Không gọi API."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from ai_backend.infra.llm import async_client
from common.settings import settings


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _timeout_error() -> APITimeoutError:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return APITimeoutError(request)


async def _no_sleep(*_args, **_kwargs) -> None:
    return None


def test_slot_released_after_success(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_concurrency", 1)
    async_client.reset_async_semaphore_for_tests()

    async def scenario() -> str:
        async with async_client.async_llm_slot():
            return await async_client.acall_with_retry(lambda: _ok())

    async def _ok() -> str:
        return "ok"

    assert asyncio.run(scenario()) == "ok"
    assert async_client.async_semaphore_available() == 1


def test_slot_released_after_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_concurrency", 1)
    monkeypatch.setattr(async_client.asyncio, "sleep", _no_sleep)
    async_client.reset_async_semaphore_for_tests()

    async def always_fail():
        raise _timeout_error()

    async def scenario() -> None:
        async with async_client.async_llm_slot():
            await async_client.acall_with_retry(always_fail, max_retries=2)

    with pytest.raises(APITimeoutError):
        asyncio.run(scenario())
    assert async_client.async_semaphore_available() == 1


def test_retry_uses_asyncio_sleep_then_succeeds(monkeypatch):
    sleeps: list[float] = []

    async def record_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(async_client.asyncio, "sleep", record_sleep)
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _rate_limit_error()
        return "ok"

    assert asyncio.run(async_client.acall_with_retry(flaky, max_retries=2)) == "ok"
    assert calls["n"] == 2
    assert len(sleeps) == 1


class _Delta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str | None) -> None:
        self.delta = _Delta(content)


class _Chunk:
    def __init__(self, content: str | None) -> None:
        self.choices = [_Choice(content)]


class _FakeStream:
    def __init__(self, tokens: list[str], error_after: int | None = None, error: Exception | None = None) -> None:
        self._tokens = tokens
        self._error_after = error_after
        self._error = error

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for index, token in enumerate(self._tokens):
            if self._error_after is not None and index >= self._error_after:
                raise self._error or RuntimeError("stream failed")
            yield _Chunk(token)
        if self._error_after is not None and self._error_after >= len(self._tokens):
            raise self._error or RuntimeError("stream failed")


class _FakeCompletions:
    def __init__(
        self,
        tokens: list[str] | None = None,
        error: Exception | None = None,
        error_after: int | None = None,
    ) -> None:
        self.tokens = tokens or []
        self.error = error
        self.error_after = error_after
        self.calls = 0
        self.kwargs: dict | None = None

    async def create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self.error is not None and self.error_after is None:
            raise self.error
        return _FakeStream(self.tokens, error_after=self.error_after, error=self.error)


class _FakeAsyncClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.api_key = "test-key"
        self.chat = type("Chat", (), {"completions": completions})()


def _patch_stream(monkeypatch, client: _FakeAsyncClient) -> None:
    monkeypatch.setattr(settings, "llm_max_concurrency", 1)
    async_client.reset_async_semaphore_for_tests()

    def _sync_client(*_args, **_kwargs):
        raise AssertionError("chat_stream gọi SDK sync")

    monkeypatch.setattr("ai_backend.infra.llm.completion.get_client", _sync_client)
    monkeypatch.setattr(
        "ai_backend.infra.llm.completion.get_async_client",
        lambda backend_name=None: client,
    )


def test_chat_stream_uses_async_client_and_releases_slot(monkeypatch):
    completions = _FakeCompletions(["Xin ", "chào"])
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    from ai_backend.infra.llm.completion import chat_stream

    assert list(chat_stream([{"role": "user", "content": "hi"}])) == ["Xin ", "chào"]
    assert completions.calls == 1
    assert completions.kwargs is not None
    assert completions.kwargs["stream"] is True
    assert async_client.async_semaphore_available() == 1


def test_chat_stream_releases_slot_on_error(monkeypatch):
    completions = _FakeCompletions(error=RuntimeError("boom"))
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    from ai_backend.infra.llm.completion import chat_stream

    with pytest.raises(RuntimeError, match="boom"):
        list(chat_stream([{"role": "user", "content": "hi"}]))
    assert async_client.async_semaphore_available() == 1

    again = _FakeCompletions(["sau lỗi"])
    monkeypatch.setattr(
        "ai_backend.infra.llm.completion.get_async_client",
        lambda backend_name=None: _FakeAsyncClient(again),
    )
    assert list(chat_stream([{"role": "user", "content": "hi"}])) == ["sau lỗi"]
    assert async_client.async_semaphore_available() == 1


def test_chat_stream_releases_slot_when_stream_fails_midway(monkeypatch):
    completions = _FakeCompletions(tokens=["Một "], error_after=1, error=RuntimeError("đứt stream"))
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    from ai_backend.infra.llm.completion import chat_stream

    received: list[str] = []
    with pytest.raises(RuntimeError, match="đứt stream"):
        for delta in chat_stream([{"role": "user", "content": "hi"}]):
            received.append(delta)
    assert received == ["Một "]
    assert async_client.async_semaphore_available() == 1


def _stream_cache_context(prompt_version: str, question: str) -> None:
    from ai_backend.infra.cache.exact import set_llm_cache_context

    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version=prompt_version,
        normalized_question=question,
    )


def test_chat_stream_exact_cache_skips_model_on_same_prompt_version(monkeypatch):
    from ai_backend.infra.cache.exact import clear_llm_cache_context, get_exact_cache
    from ai_backend.infra.llm.completion import chat_stream

    get_exact_cache().clear()
    completions = _FakeCompletions(["Xin ", "chào"])
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")
    messages = [{"role": "user", "content": "hi"}]
    try:
        _stream_cache_context("production", "Giá FPT hôm nay?")
        first = list(chat_stream(messages))
        second = list(chat_stream(messages))
    finally:
        clear_llm_cache_context()
        get_exact_cache().clear()

    assert first == ["Xin ", "chào"]
    assert second == ["Xin chào"]
    assert completions.calls == 1


def test_chat_stream_exact_cache_miss_when_prompt_version_changes(monkeypatch):
    from ai_backend.infra.cache.exact import clear_llm_cache_context, get_exact_cache
    from ai_backend.infra.llm.completion import chat_stream

    get_exact_cache().clear()
    completions = _FakeCompletions(["lần 1"])
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")
    messages = [{"role": "user", "content": "hi"}]
    try:
        _stream_cache_context("production", "Giá FPT?")
        list(chat_stream(messages))
        completions.tokens = ["lần 2"]
        _stream_cache_context("2", "Giá FPT?")
        second = list(chat_stream(messages))
    finally:
        clear_llm_cache_context()
        get_exact_cache().clear()

    assert second == ["lần 2"]
    assert completions.calls == 2


def test_chat_stream_error_does_not_write_exact_cache(monkeypatch):
    from ai_backend.infra.cache.exact import clear_llm_cache_context, get_exact_cache
    from ai_backend.infra.llm.completion import chat_stream

    get_exact_cache().clear()
    completions = _FakeCompletions(error=RuntimeError("boom"))
    _patch_stream(monkeypatch, _FakeAsyncClient(completions))
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")
    messages = [{"role": "user", "content": "hi"}]
    try:
        _stream_cache_context("production", "Giá FPT?")
        with pytest.raises(RuntimeError, match="boom"):
            list(chat_stream(messages))
        calls_after_error = completions.calls
        completions.error = None
        completions.tokens = ["mới"]
        again = list(chat_stream(messages))
    finally:
        clear_llm_cache_context()
        get_exact_cache().clear()

    assert again == ["mới"]
    assert calls_after_error >= 1
    assert completions.calls == calls_after_error + 1
