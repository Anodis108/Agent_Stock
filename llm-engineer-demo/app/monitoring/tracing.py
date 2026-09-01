"""LangFuse — cây span lồng nhau: root (supervisor) → agent (price/news/db/...) → step.

Không dùng ContextVar/OTEL baggage (không tin cậy qua Send/subgraph). Span cha
được tra theo `turn` (uuid mỗi câu hỏi) trong 2 registry nhỏ:
  _roots[turn]           — span "agent_pr_ask" (mở trong trace_answer)
  _agents[(turn, name)]  — span "price_agent"/"db_agent"/... (mở trong agent_span)

Node bên trong mỗi subgraph gọi step_parent(state, agent_name) để lấy đúng
span cha của agent mình — từ đó trace_step() tạo span lồng đúng cấp. Tắt mặc
định (MONITORING_ENABLED=false) — mọi hàm ở đây no-op khi đó.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import settings

_roots: dict[str, Any] = {}
_agents: dict[tuple[str, str], Any] = {}
_client: Any = None


def _get_langfuse():
    global _client
    if _client is None:
        import os

        from langfuse import Langfuse

        # Windows dev machine: SSL_CERT_FILE có thể trỏ tới file không tồn tại
        # (leftover từ env khác) — httpx crash lúc tạo SSL context nếu vậy.
        cert = os.environ.get("SSL_CERT_FILE")
        if cert and not os.path.isfile(cert):
            os.environ.pop("SSL_CERT_FILE", None)

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _client


def step_parent(state: Any, agent_name: str | None = None) -> Any:
    """Span cha cho trace_step() trong 1 node.

    agent_name=None (node chạy trực tiếp trong supervisor, vd coordinator/reply)
    → span root của turn. agent_name="price_agent" (node trong 1 subgraph con)
    → span của agent đó, đã mở qua agent_span().
    """
    turn = str((state or {}).get("turn") or "")
    if not turn:
        return None
    if agent_name:
        return _agents.get((turn, agent_name))
    return _roots.get(turn)


@contextmanager
def trace_answer(name: str, question: str, metadata: dict[str, Any] | None = None):
    """Span ROOT — 1 lần / câu hỏi (agent_pr_ask). `t["_span"]` / `t["output"]`."""
    if not settings.monitoring_enabled:
        yield {}
        return

    langfuse = _get_langfuse()
    meta = dict(metadata or {})
    turn = str(meta.get("turn") or "")
    span = langfuse.start_observation(name=name, as_type="agent", input=question, metadata=meta)
    if turn:
        _roots[turn] = span
    box: dict[str, Any] = {"_span": span}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()
        langfuse.flush()
        if turn:
            _roots.pop(turn, None)


@contextmanager
def agent_span(turn: str, name: str, input: Any = None, metadata: dict[str, Any] | None = None):
    """Span AGENT con của root — bọc quanh 1 subgraph (price/news/db/eval/synth).

    Node bên trong subgraph tìm span này qua step_parent(state, name). No-op
    nếu turn rỗng hoặc không tìm thấy root (monitoring tắt).
    """
    root = _roots.get(turn)
    if not settings.monitoring_enabled or root is None:
        yield {}
        return

    span = root.start_observation(name=name, as_type="agent", input=input, metadata=metadata or {})
    key = (turn, name)
    _agents[key] = span
    box: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        _agents.pop(key, None)
        span.update(output=box.get("output"), metadata={"latency_s": time.perf_counter() - start})
        span.end()


def _usage_details(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        prompt = usage.get("input_tokens", usage.get("prompt_tokens"))
        completion = usage.get("output_tokens", usage.get("completion_tokens"))
        total = usage.get("total_tokens")
    else:
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
    if prompt is None:
        return None
    inp, out = int(prompt), int(completion or 0)
    return {"input": inp, "output": out, "total": int(total if total is not None else inp + out)}


@contextmanager
def trace_step(
    parent_span: Any,
    name: str,
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    *,
    model: str | None = None,
):
    """SPAN (bước) hoặc GENERATION (LLM, nếu `model` truyền vào) — con của
    parent_span. No-op nếu parent_span là None (monitoring tắt hoặc agent
    chưa mở span cha — xem step_parent())."""
    if not settings.monitoring_enabled or parent_span is None:
        yield {}
        return

    as_type = "generation" if model else "span"
    kwargs: dict[str, Any] = {"name": name, "as_type": as_type, "input": input, "metadata": metadata or {}}
    if model:
        kwargs["model"] = model
    span = parent_span.start_observation(**kwargs)
    box: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield box
    except Exception as exc:
        span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        update: dict[str, Any] = {
            "output": box.get("output"),
            "metadata": {"latency_s": time.perf_counter() - start},
        }
        usage = _usage_details(box.get("usage"))
        if usage:
            update["usage_details"] = usage
        span.update(**update)
        span.end()


def trace_stream(name: str, question: str, tokens: Iterator[str]) -> Iterator[str]:
    """Bọc quanh answer_stream(): trace toàn bộ output ghép lại sau khi stream kết thúc."""
    if not settings.monitoring_enabled:
        yield from tokens
        return
    chunks: list[str] = []
    with trace_answer(name, question) as t:
        try:
            for token in tokens:
                chunks.append(token)
                yield token
        finally:
            t["output"] = "".join(chunks)
