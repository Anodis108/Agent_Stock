"""SSE của swarm chat — không ghi session vào database.

Wire format (giống llm-engineer-demo `/chat/stream-sse`):
  ``data: {"token": "..."}`` từng chunk, payload cuối ``data: {"complete": true, ...}``,
  kết thúc ``data: [DONE]``. Lỗi: ``data: {"error": "..."}``.

Process web (AI_TRANSPORT=http) parse qua ``stream_remote_sse`` rồi có thể bọc lại ``event:``.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from ai_backend.domain.agents.graph import start_graph


def swarm_public_payload(state: dict[str, Any], *, started: float) -> dict[str, Any]:
    """Payload final SSE từ state checkpoint (``start_graph`` yield ``result``)."""
    final = state["final_answer"]
    return {
        "question": final.question,
        "answer": final.answer,
        "drawed_paths": final.drawed_paths,
        "total_duration_s": round(time.perf_counter() - started, 3),
    }


def _sse_data(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _token_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, dict) and "delta" in chunk:
        return str(chunk["delta"])
    return str(chunk)


async def swarm_sse(
    question: str,
    request_deps: dict[str, Any],
    *,
    user_id: str,
    request_id: str,
) -> AsyncIterator[str]:
    """Chạy start_graph (mode=chat) và yield SSE demo-format. Client đóng → generator huỷ, graph dừng theo."""
    started = time.perf_counter()

    try:
        async for kind, payload in start_graph(
            "chat", question, request_deps, user_id=user_id, request_id=request_id
        ):
            if kind == "token":
                yield _sse_data({"token": _token_text(payload)})
            elif kind == "result":
                yield _sse_data(
                    {
                        **swarm_public_payload(payload, started=started),
                        "request_id": request_id,
                        "complete": True,
                    }
                )
        yield _sse_data("[DONE]")
    except Exception as exc:  # noqa: BLE001 — báo lỗi cho client thay vì cắt stream
        yield _sse_data({"error": str(exc)})
