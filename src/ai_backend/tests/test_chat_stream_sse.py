"""SSE wire format cho ChatService.stream_sse (demo: token + [DONE])."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ai_backend.application import chat_service as mod


async def _fake_run_chat_graph(*_args, **_kwargs):
    yield "token", "Hel"
    yield "token", "lo"
    yield "result", {
        "final_answer": SimpleNamespace(
            question="hi",
            answer="Hello",
            drawed_paths=[],
        ),
    }


@pytest.mark.asyncio
async def test_swarm_sse_demo_format(monkeypatch):
    svc = mod.ChatService()

    async def _fake(self, question, *, user_id, request_id, request_deps=None):
        async for item in _fake_run_chat_graph():
            yield item

    monkeypatch.setattr(mod.ChatService, "_run_chat_graph", _fake)

    chunks = [c async for c in svc.stream_sse("hi", user_id="u1", request_id="r1")]
    body = "".join(chunks)
    assert 'data: {"token": "Hel"}' in body
    assert 'data: {"token": "lo"}' in body
    assert '"complete": true' in body
    assert body.strip().endswith("data: [DONE]")

    lines = [ln for ln in body.split("\n") if ln.startswith("data: ")]
    complete_line = next(ln for ln in lines if '"complete": true' in ln)
    payload = json.loads(complete_line[len("data: ") :])
    assert payload["answer"] == "Hello"
    assert payload["request_id"] == "r1"
