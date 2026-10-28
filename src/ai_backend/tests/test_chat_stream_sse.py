"""SSE wire format cho swarm_sse (demo: token + [DONE])."""

from __future__ import annotations

import json

import pytest

from ai_backend.infra.llm import chat_stream as mod


async def _fake_start_graph(*_args, **_kwargs):
    yield "token", "Hel"
    yield "token", "lo"
    yield "result", {
        "question": "hi",
        "rewritten": None,
        "answer": "Hello",
        "error": None,
        "prices": [],
        "news": [],
        "eval_result": None,
        "chart_result": None,
        "source_file": None,
        "notes": {},
        "guardrail_result": None,
    }


@pytest.mark.asyncio
async def test_swarm_sse_demo_format(monkeypatch):
    monkeypatch.setattr(mod, "start_graph", _fake_start_graph)

    chunks = [c async for c in mod.swarm_sse("hi", {}, user_id="u1", request_id="r1")]
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
