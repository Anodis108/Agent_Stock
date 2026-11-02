"""Parse SSE demo-format từ AI (data-only, không event:)."""

from __future__ import annotations

from common.transport.transport import stream_remote_sse


class _Body:
    def __init__(self, raw: bytes) -> None:
        self._lines = raw.split(b"\n")
        self._i = 0

    def readline(self) -> bytes:
        if self._i >= len(self._lines):
            return b""
        line = self._lines[self._i]
        self._i += 1
        return line + b"\n"

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_stream_remote_sse_parses_demo_tokens(monkeypatch):
    sse = (
        b'data: {"token": "a"}\n\n'
        b'data: {"answer": "ab", "question": "q", "complete": true}\n\n'
        b"data: [DONE]\n\n"
    )

    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: _Body(sse))

    events = list(stream_remote_sse(question="q", user_id="u"))
    assert [e[0] for e in events] == ["token", "complete"]
    assert events[0][1]["delta"] == "a"
    assert events[1][1]["answer"] == "ab"
