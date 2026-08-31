"""Graph Hierarchical Coordinator — hub + 5 worker subgraph.

    START → recall → compact → coordinator ─┬─ db_lookup (đọc DB)
                                            ├─ gather: price_agent / news_agent (nếu DB thiếu)
                                            ├─ eval_agent
                                            ├─ synth_agent
                                            ├─ db_write (soạn lệnh)
                                            ├─ hitl_commit  ← interrupt_before, user duyệt mới ghi
                                            └─ reply → store → END

HITL giống agent_m2: compile(interrupt_before=["hitl_commit"]). Resume ainvoke(None).

Nhúng `_build_graph()` của từng agent. Cửa sổ đổi tên field vì LangGraph chỉ
khớp field trùng tên.

Vẽ sơ đồ: python -m app.agent_pr.supervisor_agent.graph
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.agent_pr.craw_agent.graph import _build_graph as _craw_graph
from app.agent_pr.db_agent.graph import _build_graph as _db_graph
from app.agent_pr.eval_agent.graph import _build_graph as _eval_graph
from app.agent_pr.news_agent.graph import _build_graph as _news_graph
from app.agent_pr.supervisor_agent.nodes import (
    after_wave1,
    compact_history,
    coordinator,
    hitl_commit,
    recall_memory,
    reply,
    route_coordinator,
    store_memory,
)
from app.agent_pr.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.nodes import approve_pending_write
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import PendingWrite
from app.agent_pr.supervisor_agent.state import (
    DbWindow,
    EvalWindow,
    NewsWindow,
    PriceWindow,
    SupervisorState,
    SynthWindow,
)
from app.agent_pr.synthesis_agent.graph import _build_graph as _synth_graph
from app.config import settings
from app.monitoring.tracing import trace_answer


# ── Cửa sổ: subgraph worker + lift tên field lên hợp đồng hub ─────────────────


@lru_cache(maxsize=1)
def _price_window():
    """symbol vào → craw subgraph → lift quote thành price."""

    def lift(state: PriceWindow) -> dict:
        return {"price": state["quote"]}

    graph = StateGraph(PriceWindow)
    graph.add_node("price_graph", _craw_graph())
    graph.add_node("lift_price", lift)
    graph.add_edge(START, "price_graph")
    graph.add_edge("price_graph", "lift_price")
    graph.add_edge("lift_price", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _news_window():
    """symbol vào → news subgraph → news (tên trùng hub, messages ở lại cửa sổ)."""

    def lift(state: NewsWindow) -> dict:
        return {"news": state["news"]}

    graph = StateGraph(NewsWindow)
    graph.add_node("news_graph", _news_graph())
    graph.add_node("lift_news", lift)
    graph.add_edge(START, "news_graph")
    graph.add_edge("news_graph", "lift_news")
    graph.add_edge("lift_news", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _eval_window():
    """price+news vào → eval subgraph → lift report thành eval."""

    def lift(state: EvalWindow) -> dict:
        # eval_turn trên hub: coordinator so với `turn` để không gọi eval lại.
        # `turn` trùng tên SupervisorState → LangGraph copy vào cửa sổ.
        return {"eval": state["report"], "eval_turn": state.get("turn") or ""}

    graph = StateGraph(EvalWindow)
    graph.add_node("eval_graph", _eval_graph())
    graph.add_node("lift_eval", lift)
    graph.add_edge(START, "eval_graph")
    graph.add_edge("eval_graph", "lift_eval")
    graph.add_edge("lift_eval", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _synth_window():
    """3 báo cáo + n_history → synth subgraph → lift result thành draft."""

    def lift(state: SynthWindow) -> dict:
        # synth_turn trên hub — cùng cơ chế eval_turn / `turn`.
        return {"draft": state["result"], "synth_turn": state.get("turn") or ""}

    graph = StateGraph(SynthWindow)
    graph.add_node("synth_graph", _synth_graph())
    graph.add_node("lift_synth", lift)
    graph.add_edge(START, "synth_graph")
    graph.add_edge("synth_graph", "lift_synth")
    graph.add_edge("lift_synth", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _db_window():
    """symbol vào → db subgraph → lift result thành db."""

    def lift(state: DbWindow) -> dict:
        mode = str(state.get("mode") or "read")
        turn = state.get("turn") or ""
        out = {"db": state["result"]}
        if mode == "write":
            out["db_write_turn"] = turn
        else:
            out["db_lookup_turn"] = turn
        return out

    graph = StateGraph(DbWindow)
    graph.add_node("db_graph", _db_graph())
    graph.add_node("lift_db", lift)
    graph.add_edge(START, "db_graph")
    graph.add_edge("db_graph", "lift_db")
    graph.add_edge("lift_db", END)
    return graph.compile()


# Short-term: state theo thread_id trên Postgres (sống qua restart process).
# ainvoke/astream cần AsyncPostgresSaver — PostgresSaver sync không có aget_tuple.
# Tạo pool trong coroutine (AsyncPostgresSaver lấy running loop lúc __init__).
_runtime_app = None


async def _runtime_graph():
    """Compile hub 1 lần / process, checkpointer async."""
    global _runtime_app
    if _runtime_app is None:
        pool = AsyncConnectionPool(
            conninfo=settings.checkpoint_postgres_uri,
            min_size=1,
            max_size=10,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=False,
        )
        await pool.open()
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        _runtime_app = _assemble(saver)
    return _runtime_app

# Nhãn UI — khớp tên node trên graph. Node không có trong map vẫn hiện (dùng tên kỹ thuật).
_STEP_LABELS: dict[str, str] = {
    "recall_memory": "Recall — đọc memory dài hạn",
    "compact_history": "Compact — nén hội thoại",
    "coordinator": "Coordinator — lập plan / giao việc",
    "price_agent": "PriceAgent — lấy giá",
    "news_agent": "NewsAgent — lấy tin CafeF",
    "db_agent": "DBAgent — đọc kho / soạn ghi",
    "hitl_commit": "HITL — duyệt rồi COMMIT vào DB",
    "after_wave1": "Fan-in — gom báo cáo đợt 1",
    "eval_agent": "EvalAgent — chấm tin vs giá",
    "synth_agent": "SynthesisAgent — viết câu trả lời",
    "reply": "Coordinator — trả lời user",
    "store_memory": "Store — ghi memory dài hạn",
}


def _is_hitl_pause(snap) -> bool:
    nxt = tuple(getattr(snap, "next", None) or ())
    return nxt == ("hitl_commit",)


def _pending_models(db) -> list[PendingWrite]:
    if db is None:
        return []
    if isinstance(db, DbOut):
        return list(db.pending_writes or [])
    rows = getattr(db, "pending_writes", None) or []
    out: list[PendingWrite] = []
    for row in rows:
        if isinstance(row, PendingWrite):
            out.append(row)
        elif isinstance(row, dict) and row.get("id") is not None:
            out.append(PendingWrite(**{k: row[k] for k in PendingWrite.model_fields if k in row}))
    return out


def _paused_output(snap, thread_id: str, user_id: str, question: str) -> Agent_Output:
    """Output tạm khi interrupt_before hitl_commit — synth đã xong, chưa COMMIT."""
    values = getattr(snap, "values", None) or {}
    pending = _pending_models(values.get("db"))
    symbol = str(values.get("symbol") or "")
    n = len(pending)
    draft = values.get("draft")
    answer = getattr(draft, "answer", "") if draft else ""
    if not answer:
        answer = f"{symbol}: đã soạn {n} lệnh ghi bài chưa có."
    answer = answer.rstrip() + f" Chờ duyệt HITL — {n} lệnh chưa COMMIT vào DB."
    db = values.get("db")
    if isinstance(db, DbOut):
        db = db.model_copy(update={"pending_writes": pending, "detail": f"chờ HITL — {n} lệnh"})
    else:
        db = DbOut(symbol=symbol, pending_writes=pending, detail=f"chờ HITL — {n} lệnh")
    return Agent_Output(
        symbol=symbol,
        question=question or str(values.get("question") or ""),
        answer=answer,
        price=values.get("price"),
        news=values.get("news"),
        eval=values.get("eval"),
        db=db,
        trace=list(values.get("trace") or []),
        plan=values.get("plan"),
        thread_id=thread_id,
        user_id=user_id,
    )


def _step_event(node: str, update: object) -> dict:
    """1 sự kiện UI cho 1 node vừa xong — hiện hết, không lọc."""
    
    def _step_detail(node: str, update: object) -> str:
        """Một dòng phụ — lấy từ trace hub nếu node vừa ghi, không dump cả state."""
        if not isinstance(update, dict):
            return ""
        trace = update.get("trace")
        if isinstance(trace, list) and trace:
            return str(trace[-1])
        wave = update.get("next_wave")
        if node == "coordinator" and wave:
            return f"đợt tiếp: {wave}"
        return ""
    
    return {
        "type": "step",
        "node": node,
        "label": _STEP_LABELS.get(node, node),
        "detail": _step_detail(node, update),
    }


def _invoke_args(inp: Agent_Input) -> tuple[str, str, str, dict, dict]:
    """Cùng input cho ainvoke và astream — UI stream không được lệch thread/turn."""
    symbol = (inp.symbol or "").strip()
    if symbol:
        from app.agent_pr.symbol import normalize_symbol

        normalize_symbol(symbol)
    question = (inp.question or "").strip()
    thread_id = (inp.thread_id or "").strip()
    if not thread_id:
        raise ValueError("thread_id bắt buộc — client phải gửi id phiên (giống /assistant).")
    user_id = (inp.user_id or "").strip()
    if not question and symbol:
        question = (
            f"Phân tích biến động giá và tin tức liên quan đến mã {symbol.upper()} hôm nay."
        )
    initial = {
        "symbol": symbol,
        "question": question,
        "turn": str(uuid.uuid4()),
        "user_id": user_id,
        "skip_hitl": bool(inp.skip_hitl),
        "trace": [],
    }
    config = {
        "recursion_limit": 28,
        "configurable": {"thread_id": thread_id},
    }
    return question, thread_id, user_id, initial, config


def _assemble(checkpointer):
    """Ráp hub + 5 worker. News không cần cửa sổ: field `news` đã trùng tên."""
    graph = StateGraph(SupervisorState)

    graph.add_node("recall_memory", recall_memory)
    graph.add_node("compact_history", compact_history)
    graph.add_node("coordinator", coordinator)
    graph.add_node("after_wave1", after_wave1)
    graph.add_node("reply", reply)
    graph.add_node("hitl_commit", hitl_commit)
    graph.add_node("store_memory", store_memory)

    graph.add_node("price_agent", _price_window())
    graph.add_node("news_agent", _news_window())
    graph.add_node("db_agent", _db_window())
    graph.add_node("eval_agent", _eval_window())
    graph.add_node("synth_agent", _synth_window())

    graph.add_edge(START, "recall_memory")
    graph.add_edge("recall_memory", "compact_history")
    graph.add_edge("compact_history", "coordinator")
    graph.add_conditional_edges(
        "coordinator",
        route_coordinator,
        [
            "price_agent",
            "news_agent",
            "db_agent",
            "eval_agent",
            "synth_agent",
            "hitl_commit",
            "reply",
        ],
    )

    # Đợt 1 hội tụ 1 node rồi mới về hub — xem after_wave1.
    graph.add_edge("price_agent", "after_wave1")
    graph.add_edge("news_agent", "after_wave1")
    graph.add_edge("db_agent", "after_wave1")
    graph.add_edge("after_wave1", "coordinator")

    graph.add_edge("eval_agent", "coordinator")
    graph.add_edge("synth_agent", "coordinator")
    graph.add_edge("hitl_commit", "coordinator")
    graph.add_edge("reply", "store_memory")
    graph.add_edge("store_memory", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["hitl_commit"])


def _build_graph():
    """CLI / PNG — cùng graph runtime (asyncio.run khi chưa có event loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_runtime_graph())
    raise RuntimeError("Trong event loop hãy await _runtime_graph()")


async def run_supervisor(inp: Agent_Input) -> Agent_Output:
    """Entry hub. recursion_limit: vòng coordinator → worker → coordinator.

    Short-term: `thread_id` (client bắt buộc gửi) + PostgresSaver.
    Long-term: `user_id` + `app.agent_pr.memory` (Qdrant `user_memory`).
    `turn` uuid mỗi HTTP — plan/eval/synth không lấy nhầm từ checkpoint lượt trước.

    Span cha `agent_pr_ask` sống ở ContextVar — không nhét vào state
    (checkpointer không serialize LangfuseSpan).
    """
    question, thread_id, user_id, initial, config = _invoke_args(inp)
    with trace_answer(
        "agent_pr_ask",
        question or (inp.symbol or "").strip(),
        metadata={"thread_id": thread_id, "user_id": user_id},
    ) as t:
        graph = await _runtime_graph()
        try:
            output = await graph.ainvoke(initial, config=config)
        except Exception as exc:
            if "Interrupt" not in type(exc).__name__:
                raise
            output = {}
        snap = await graph.aget_state(config)
        if isinstance(output, dict) and output.get("output") is not None:
            out = output["output"]
            out.thread_id = thread_id
            out.user_id = user_id
        elif _is_hitl_pause(snap):
            out = _paused_output(snap, thread_id, user_id, question)
        else:
            raise RuntimeError("Graph kết thúc nhưng chưa có câu trả lời.")
        t["output"] = {"answer": out.answer, "trace": out.trace}
        return out


async def last_supervisor_output(thread_id: str) -> Agent_Output | None:
    """Output lượt ask gần nhất trên thread — evaluate chấm đúng câu user đã thấy."""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    snap = await (await _runtime_graph()).aget_state(
        {"configurable": {"thread_id": tid}}
    )
    values = getattr(snap, "values", None) or {}
    out = values.get("output")
    if isinstance(out, Agent_Output):
        return out
    if _is_hitl_pause(snap):
        return _paused_output(snap, tid, str(values.get("user_id") or ""), str(values.get("question") or ""))
    return None


async def run_supervisor_stream(inp: Agent_Input) -> AsyncIterator[dict]:
    """Cùng graph với run_supervisor, nhưng yield từng node khi xong — UI hiện bước.

    LangGraph astream(updates): mỗi chunk = {tên_node: partial state}. Subgraph
    worker (price/news/db/eval/synth) là 1 bước, không bung normalize/fetch
    (đủ cho stepper; chi tiết vẫn nằm ở `trace` khi done).

    Yield:
      {"type": "step", "node", "label", "detail"}
      {"type": "done", "output": Agent_Output}
      {"type": "error", "message": str}  — rồi dừng
    """
    question, thread_id, user_id, initial, config = _invoke_args(inp)
    with trace_answer(
        "agent_pr_ask",
        question or (inp.symbol or "").strip(),
        metadata={"thread_id": thread_id, "user_id": user_id, "stream": True},
    ) as t:
        output: Agent_Output | None = None
        try:
            async for chunk in (await _runtime_graph()).astream(
                initial, config=config, stream_mode="updates"
            ):
                if not isinstance(chunk, dict):
                    continue
                for node, update in chunk.items():
                    if str(node).startswith("__"):
                        continue
                    yield _step_event(node, update)
                    if (
                        node == "reply"
                        and isinstance(update, dict)
                        and update.get("output") is not None
                    ):
                        output = update["output"]
        except Exception as exc:
            if "Interrupt" not in type(exc).__name__:
                yield {"type": "error", "message": str(exc)}
                return
        snap = await (await _runtime_graph()).aget_state(config)
        if output is None and _is_hitl_pause(snap):
            paused = _paused_output(snap, thread_id, user_id, question)
            t["output"] = {"answer": paused.answer, "hitl": True}
            yield {"type": "hitl", "output": paused}
            return
        if output is None:
            yield {"type": "error", "message": "Graph kết thúc nhưng chưa có câu trả lời."}
            return
        output.thread_id = thread_id
        output.user_id = user_id
        t["output"] = {"answer": output.answer, "trace": output.trace}
        yield {"type": "done", "output": output}


async def resume_supervisor(
    thread_id: str,
    *,
    approve: bool = True,
    pending_id: int | None = None,
    kind: str = "news",
    user_id: str = "",
) -> Agent_Output:
    """Tiếp graph sau interrupt_before=["hitl_commit"] — giống agent_m2 ainvoke(None)."""
    tid = (thread_id or "").strip()
    graph = await _runtime_graph()
    config = {"recursion_limit": 28, "configurable": {"thread_id": tid}}
    snap = await graph.aget_state(config)
    if not _is_hitl_pause(snap):
        raise RuntimeError("Không có HITL đang chờ trên thread này.")
    values = getattr(snap, "values", None) or {}
    pending = _pending_models(values.get("db"))
    question = str(values.get("question") or "")

    if pending_id is not None:
        approve_pending_write(int(pending_id), approve=approve, kind=kind or "news")
        remaining = [
            pw
            for pw in pending
            if not (int(pw.id) == int(pending_id) and (pw.kind or "news") == (kind or "news"))
        ]
        if remaining:
            paused = _paused_output(snap, tid, user_id, question)
            if paused.db:
                paused.db = paused.db.model_copy(update={"pending_writes": remaining})
            return paused

    elif not approve:
        db = values.get("db")
        for pw in pending:
            approve_pending_write(pw.id, approve=False, kind=pw.kind or "news")
        rejected = (
            db.model_copy(update={"pending_writes": [], "detail": "HITL: từ chối toàn bộ"})
            if isinstance(db, DbOut)
            else DbOut(symbol=str(values.get("symbol") or ""), detail="HITL: từ chối toàn bộ")
        )
        await graph.aupdate_state(
            config,
            {
                "db": rejected,
                "trace": list(values.get("trace") or []) + ["HITL: từ chối toàn bộ"],
            },
            as_node="hitl_commit",
        )

    try:
        result = await graph.ainvoke(None, config=config)
    except Exception as exc:
        if "Interrupt" not in type(exc).__name__:
            raise
        result = {}
    snap = await graph.aget_state(config)
    if isinstance(result, dict) and result.get("output") is not None:
        out = result["output"]
        out.thread_id = tid
        out.user_id = user_id
        return out
    if _is_hitl_pause(snap):
        return _paused_output(snap, tid, user_id, question)
    raise RuntimeError("Resume HITL xong nhưng chưa có câu trả lời.")


def save_graph_visualization(path: str = "images/supervisor_agent_graph.png") -> str:
    """Xuất PNG (mermaid.ink, cần mạng). Lỗi → ghi .mmd, dán https://mermaid.live.

    `xray=True`: bung subgraph worker (cửa sổ + normalize/fetch/parse…).
    Mặc định LangGraph `xray=False` — mỗi agent chỉ còn 1 hộp, đúng tấm PNG cũ.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    g = _build_graph().get_graph(xray=True)
    try:
        Path(path).write_bytes(g.draw_mermaid_png())
        return path
    except Exception:
        mmd = path.rsplit(".", 1)[0] + ".mmd"
        Path(mmd).write_text(g.draw_mermaid(), encoding="utf-8")
        return mmd


if __name__ == "__main__":
    # python -m app.agent_pr.supervisor_agent.graph
    print(save_graph_visualization())
