"""Swarm graph gốc: top_supervisor → chat_team | scan_team (subgraph dựng ở chat/graph.py, scan/graph.py).

Checkpointer (HITL), start_graph / resume_graph (entrypoint chat + scan), vẽ sơ đồ.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from ai_backend.domain.agents.chat.graph import _build_graph as build_chat_graph
from ai_backend.domain.agents.nodes import route_from_top, top_supervisor_node
from ai_backend.domain.agents.scan.graph import build_graph as build_scan_graph
from ai_backend.domain.agents.scan.nodes import resolve_scan_threshold
from ai_backend.domain.agents.state import AssistantState
from ai_backend.infra.monitoring.tracing import trace_answer
from ai_backend.shared.logging import get_logger
from ai_backend.shared.settings import ai_settings
from common.domain.entities import AlertStatus

_logger = get_logger(__name__)

_CHECKPOINTER: MemorySaver | Any | None = None

def _serde():
    return JsonPlusSerializer(pickle_fallback=True, allowed_msgpack_modules=True)


async def _ensure_checkpointer() -> None:
    global _CHECKPOINTER
    if _CHECKPOINTER is not None:
        return
    serde = _serde()
    url = ai_settings.database_url
    if url:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg import AsyncConnection
            from psycopg.rows import dict_row

            conn = await AsyncConnection.connect(
                url, autocommit=True, prepare_threshold=0, row_factory=dict_row, connect_timeout=3
            )
            saver = AsyncPostgresSaver(conn, serde=serde)
            await saver.setup()
            _CHECKPOINTER = saver
            _logger.info("Checkpointer: AsyncPostgresSaver")
            return
        except Exception as exc:  # noqa: BLE001
            _logger.warning("AsyncPostgresSaver không dùng được (%s) → MemorySaver", exc)
    _CHECKPOINTER = MemorySaver(serde=serde)
    _logger.info("Checkpointer: MemorySaver")
    build_graph.cache_clear()


@lru_cache(maxsize=1)
def build_graph():
    graph = StateGraph(AssistantState)
    graph.add_node("top_supervisor", top_supervisor_node)
    graph.add_node("chat_team", build_chat_graph())
    graph.add_node("scan_team", build_scan_graph())
    graph.add_edge(START, "top_supervisor")
    graph.add_conditional_edges("top_supervisor", route_from_top, ["chat_team", "scan_team"])
    graph.add_edge("chat_team", END)
    graph.add_edge("scan_team", END)
    return graph.compile(checkpointer=build_checkpointer())


def build_checkpointer():
    return _CHECKPOINTER if _CHECKPOINTER is not None else MemorySaver(serde=_serde())


async def _collect_turn_state(
    app: Any,
    config: RunnableConfig,
    request_deps: dict[str, Any],
    thread_id: str | None,
    user_id: str,
    *,
    watch_hitl: bool,
) -> dict[str, Any]:
    """Checkpoint sau lượt chạy: copy state và gắn tool scan_tools đang chờ duyệt."""
    snap = await app.aget_state(config, subgraphs=True)
    pending = None
    if watch_hitl:
        pending = next(
            (
                t.state.values["messages"][-1].tool_calls[0]
                for t in snap.tasks
                if t.state and "scan_tools" in t.state.next
            ),
            None,
        )
    state = dict(snap.values)
    state["thread_id"] = thread_id
    state["pending_tool_call"] = pending
    if pending and "memory_store" in request_deps and request_deps["memory_store"] is not None:
        request_deps["memory_store"].append_alert_event(
            state["user_id"] or user_id,
            {
                "kind": "pending_approval",
                "approval_id": pending["id"],
                "thread_id": thread_id,
                "gate": pending["name"],
                "symbol": pending["args"]["symbol"] if "symbol" in pending["args"] and pending["args"]["symbol"] else ", ".join(state["symbols"] or []),
                "args": pending["args"],
                "status": AlertStatus.PENDING_APPROVAL.value,
            },
        )
    return state


async def start_graph(
    mode: Literal["chat", "scan"],
    question: str,
    request_deps: dict[str, Any],
    user_id: str,
    request_id: str,
) -> AsyncIterator[tuple[str, Any]]:
    """Lượt mới (demo start_conversation): yield ``token`` rồi ``result``.

    Chat: ``result`` = {final_answer, eval_data} yield ngay khi node answer xong (UI hiển thị luôn), graph vẫn chạy
    tiếp save_long_term_memory → caller phải đọc hết generator (không return ở ``result``) để lượt chạy trọn.
    ``question``: mode ``scan`` = các mã CK, cách nhau bởi dấu phẩy; mode ``chat`` = câu hỏi user.
    ``request_id`` (hoặc UUID mới) vừa là id tracing/SSE vừa là ``thread_id`` checkpointer (HITL resume).
    """
    await _ensure_checkpointer()
    config = RunnableConfig(recursion_limit=40, configurable={"thread_id": request_id})

    app = build_graph()
    initial = AssistantState(
        mode=mode,
        messages=[{"role": "user", "content": question.strip()}],
        user_id=user_id,
        request_id=request_id,
    )
    if mode == "scan":
        symbols = [s.strip().upper() for s in question.split(",") if s.strip()]
        if not symbols:
            raise ValueError("cần ít nhất một mã")
        pct = resolve_scan_threshold(symbols[0], user_id, request_deps)
        initial.update(
            task=f"Quét mã {', '.join(symbols)}, ngưỡng biến động {pct}%",
            symbols=symbols,
            threshold_pct=pct,
        )

    with trace_answer(name=mode, question=question, metadata={"thread_id": request_id}) as trace:
        # get_runtime().context của node: port (request_deps) + trace_span — như resume_graph
        context = {
            "news_days": 7,
            "threshold_pct": None,
            "concept_client": None,
            **request_deps,
            "trace_span": trace["_span"] if "_span" in trace else None,
        }
        if mode == "chat":
            # top_supervisor → chat_team → guardrail_input | rewrite_question → chat_supervisor ⇄
            # scan_team | draw_agent | portfolio_report | concept_retrieval → answer → save_long_term_memory
            async for _ns, stream_mode, chunk in app.astream(
                initial,
                config=config,
                context=context,
                stream_mode=["updates", "custom"],
                subgraphs=True,
            ):
                if stream_mode == "custom":
                    yield "token", chunk  # chat_team.answer_node
                elif "answer" in chunk:  # answer xong → trả kết quả trước, save_long_term_memory chạy sau
                    final = chunk["answer"]["final_answer"]
                    trace["output"] = final.answer
                    yield "result", {"final_answer": final, "eval_data": chunk["answer"]["eval_data"]}
            return

        # top_supervisor → scan_team → scan_supervisor ⇄ price_agent | news_agent | db_agent |
        # event_classifier_node | eval_agent | synthesis_node; interrupt_before scan_tools (HITL)
        await app.ainvoke(initial, config=config, context=context)
        state = await _collect_turn_state(app, config, request_deps, request_id, user_id, watch_hitl=True)
        trace["output"] = (
            {"status": "pending_approval", "tool_call": state["pending_tool_call"]}
            if state["pending_tool_call"]
            else state
        )
        yield "result", state


async def resume_graph(
    thread_id: str,
    approve: bool,
    rejection_reason: str,
    request_deps: dict[str, Any],
) -> dict[str, Any]:
    """Tiếp checkpoint sau interrupt scan_tools (demo resume_conversation)."""
    await _ensure_checkpointer()
    config = RunnableConfig(recursion_limit=40, configurable={"thread_id": thread_id})
    app = build_graph()
    snap = await app.aget_state(config, subgraphs=True)
    
    if not approve:
        task = snap.tasks[0].state if snap.tasks else None
        if task is None or "scan_tools" not in task.next:
            raise ValueError(f"thread {thread_id} không có hành động chờ duyệt")
        call = task.values["messages"][-1].tool_calls[0]
        await app.aupdate_state(
            task.config,
            {
                "messages": [
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": call["name"],
                        "content": f"Người dùng TỪ CHỐI hành động này. Lý do: {rejection_reason or 'không nêu rõ'}.",
                    }
                ]
            },
            as_node="scan_tools",
        ) 

    user_id = snap.values["user_id"]
    with trace_answer("scan_resume", f"approve={approve}", metadata={"thread_id": thread_id}) as trace:
        # input None = tiếp cùng thread_id (sau approve hoặc sau inject từ chối).
        await app.ainvoke(
            None,
            config=config,
            context={
                "news_days": 7,
                "threshold_pct": None,
                **request_deps,
                "trace_span": trace["_span"] if "_span" in trace else None,
            },
        )
        state = await _collect_turn_state(
            app, config, request_deps, thread_id, user_id, watch_hitl=True
        )
        trace["output"] = (
            {"status": "pending_approval", "tool_call": state["pending_tool_call"]}
            if state["pending_tool_call"]
            else state
        )
        return state


def save_graph_visualization(path: str = "resources/docs/agent_graph.png", width: int = 4000) -> str:
    """Vẽ PNG qua mermaid.ink với `width` lớn (draw_mermaid_png mặc định ~1900px nên ảnh mờ); lỗi → ghi .mmd."""
    import base64

    import requests

    graph = build_graph().get_graph(xray=1)
    try:
        encoded = base64.b64encode(graph.draw_mermaid().encode("utf8")).decode("ascii")
        resp = requests.get(f"https://mermaid.ink/img/{encoded}?type=png&bgColor=!white&width={width}", timeout=60)
        resp.raise_for_status()
        png_bytes = resp.content
        with open(path, "wb") as f:
            f.write(png_bytes)
        return path
    except Exception:
        mmd_path = path.rsplit(".", 1)[0] + ".mmd"
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(graph.draw_mermaid())
        return mmd_path


if __name__ == "__main__":
    print(save_graph_visualization("resources/docs/agent_graph.png"))
