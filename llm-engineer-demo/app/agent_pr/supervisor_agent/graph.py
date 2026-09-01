"""Graph Hierarchical Coordinator — Sơ đồ 3: hub giao việc, 5 worker cùng cấp.

    START → guardrail_input → rewrite → recall → compact → coordinator ─┬─ db_lookup (đọc sqlite)
                                            ├─ gather: price / news (DB thiếu)
                                            ├─ eval_agent
                                            ├─ synth_agent
                                            ├─ db_write (soạn pending, chưa COMMIT)
                                            ├─ hitl_commit  ← interrupt_before
                                            └─ reply → guardrail_output → store → END

Khác agent_m2 (1 ReAct + ToolNode HITL trước *mọi* tool):
  - Worker là subgraph ReAct riêng (`_build_graph` từng agent). Hub không crawl.
  - Coordinator chọn worker bằng tool `need_*` (bind_tools + retrieval) rồi
    `Send` subgraph — tool chỉ đánh dấu intent, không lấy giá/tin.
  - HITL chỉ trước `hitl_commit` (ghi DB). Resume: `invoke(None)` giống
    `resume_conversation` agent_m2.
  - Short-term: `thread_id` + MemorySaver (RAM, giống agent_m2 — debug).
    Long-term: `user_id` + Qdrant `user_memory` (recall/store).
  - `turn` uuid mỗi HTTP — plan/eval/synth/db_*_turn không lấy nhầm checkpoint
    lượt trước.

LangGraph chỉ copy field trùng tên. Pack worker ghi `price`/`news`/`eval`/
`draft`/`db` — không node lift. `rows`/`messages` ở lại subgraph.

Observability: một `trace_answer` / HTTP (`agent_pr_ask` hoặc resume).
Span cha nằm trên `SupervisorState._trace_span`; Send/subgraph copy field
trùng tên — worker `trace_step` lồng dưới cây đó. Evaluate on-demand.

Vẽ: `python -m app.agent_pr.supervisor_agent.graph`
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent_pr.guardrails import guardrail_input, guardrail_output, sanitize_stock_answer
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
    rewrite_question,
    route_coordinator,
    should_compact_route,
    store_memory,
)
from app.agent_pr.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.nodes import approve_pending_write
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import PendingWrite
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.agent_pr.synthesis_agent.graph import _build_graph as _synth_graph
from app.monitoring.tracing import trace_answer

# MemorySaver — RAM, mất khi restart. Đủ debug; production đổi PostgresSaver.
_checkpointer = MemorySaver()


def _hitl_waiting(snap) -> bool:
    """Graph dừng *trước* hitl_commit — chờ /pr/approve."""
    return tuple(getattr(snap, "next", None) or ()) == ("hitl_commit",)


def _pending(db) -> list[PendingWrite]:
    rows = list(getattr(db, "pending_writes", None) or []) if db else []
    out: list[PendingWrite] = []
    for r in rows:
        if isinstance(r, PendingWrite):
            out.append(r)
        elif isinstance(r, dict) and r.get("id") is not None:
            out.append(PendingWrite.model_validate(r))
    return out


def _hitl_output(snap, thread_id: str, user_id: str, question: str) -> Agent_Output:
    """Output tạm khi interrupt: synth đã xong, chưa COMMIT."""
    v = getattr(snap, "values", None) or {}
    pending = _pending(v.get("db"))
    symbol = str(v.get("symbol") or "")
    n = len(pending)
    draft = v.get("draft")
    answer = (getattr(draft, "answer", None) or f"{symbol}: đã soạn {n} lệnh ghi bài chưa có.").rstrip()
    answer += f" Chờ duyệt HITL — {n} lệnh chưa COMMIT vào DB."
    db = v.get("db")
    detail = f"chờ HITL — {n} lệnh"
    db = (
        db.model_copy(update={"pending_writes": pending, "detail": detail})
        if isinstance(db, DbOut)
        else DbOut(symbol=symbol, pending_writes=pending, detail=detail)
    )
    answer = sanitize_stock_answer(answer, v).answer
    return Agent_Output(
        symbol=symbol,
        question=question or str(v.get("question") or ""),
        answer=answer,
        price=v.get("price"),
        news=v.get("news"),
        eval=v.get("eval"),
        db=db,
        trace=list(v.get("trace") or []),
        plan=v.get("plan"),
        thread_id=thread_id,
        user_id=user_id,
    )


def _config(thread_id: str) -> dict:
    return {"recursion_limit": 28, "configurable": {"thread_id": thread_id}}


@lru_cache(maxsize=1)
def _build_graph():
    """Hub + 5 subgraph. HITL chỉ trước hitl_commit — worker không interrupt."""
    graph = StateGraph(SupervisorState)

    graph.add_node("guardrail_input", guardrail_input)
    graph.add_node("rewrite_question", rewrite_question)
    graph.add_node("guardrail_output", guardrail_output)
    graph.add_node("recall_memory", recall_memory)
    graph.add_node("compact_history", compact_history)
    graph.add_node("coordinator", coordinator)
    graph.add_node("after_wave1", after_wave1)
    graph.add_node("reply", reply)
    graph.add_node("hitl_commit", hitl_commit)
    graph.add_node("store_memory", store_memory)

    graph.add_node("price_agent", _craw_graph())
    graph.add_node("news_agent", _news_graph())
    graph.add_node("db_agent", _db_graph())
    graph.add_node("eval_agent", _eval_graph())
    graph.add_node("synth_agent", _synth_graph())

    graph.add_edge(START, "guardrail_input")
    graph.add_edge("guardrail_input", "rewrite_question")
    graph.add_edge("rewrite_question", "recall_memory")
    # Compact chủ động >40% window (nguyên tắc 40–60%) — dưới ngưỡng bỏ qua node.
    graph.add_conditional_edges(
        "recall_memory",
        should_compact_route,
        {"compact_history": "compact_history", "coordinator": "coordinator"},
    )
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
    graph.add_edge("reply", "guardrail_output")
    graph.add_edge("guardrail_output", "store_memory")
    graph.add_edge("store_memory", END)

    return graph.compile(checkpointer=_checkpointer, interrupt_before=["hitl_commit"])


def _invoke(graph, payload, config) -> dict:
    try:
        return graph.invoke(payload, config=config)
    except Exception as exc:
        if "Interrupt" in type(exc).__name__:
            return {}
        raise


def _finish(graph, config, thread_id: str, user_id: str, question: str, result) -> Agent_Output:
    snap = graph.get_state(config)
    out = result.get("output") if isinstance(result, dict) else None
    if out is not None:
        out.thread_id = thread_id
        out.user_id = user_id
        return out
    if _hitl_waiting(snap):
        return _hitl_output(snap, thread_id, user_id, question)
    v = getattr(snap, "values", None) or {}
    return Agent_Output(
        symbol=str(v.get("symbol") or ""),
        question=question or str(v.get("question") or ""),
        answer="Lỗi: graph kết thúc nhưng chưa có câu trả lời. Thử hỏi lại.",
        price=v.get("price"),
        news=v.get("news"),
        eval=v.get("eval"),
        db=v.get("db"),
        trace=list(v.get("trace") or []),
        plan=v.get("plan"),
        thread_id=thread_id,
        user_id=user_id,
    )


def run_supervisor(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip()
    question = (inp.question or "").strip()
    thread_id = (inp.thread_id or "").strip()
    user_id = (inp.user_id or "").strip()
    if not thread_id:
        raise ValueError("thread_id bắt buộc — client phải gửi id phiên (giống /assistant).")
    if not question and symbol:
        question = f"Phân tích biến động giá và tin tức liên quan đến mã {symbol.upper()} hôm nay."
    initial = {
        "symbol": symbol,
        "question": question,
        "turn": str(uuid.uuid4()),
        "user_id": user_id,
        "skip_hitl": bool(inp.skip_hitl),
        "trace": [],
    }
    config = _config(thread_id)
    with trace_answer(
        "agent_pr_ask",
        question or symbol,
        metadata={"thread_id": thread_id, "user_id": user_id},
    ) as t:
        initial["_trace_span"] = t.get("_span")
        graph = _build_graph()
        out = _finish(graph, config, thread_id, user_id, question, _invoke(graph, initial, config))
        t["output"] = {"answer": out.answer, "trace": out.trace}
        return out


def last_supervisor_output(thread_id: str) -> Agent_Output | None:
    tid = (thread_id or "").strip()
    if not tid:
        return None
    snap = _build_graph().get_state({"configurable": {"thread_id": tid}})
    values = getattr(snap, "values", None) or {}
    out = values.get("output")
    if isinstance(out, Agent_Output):
        return out
    if _hitl_waiting(snap):
        return _hitl_output(snap, tid, str(values.get("user_id") or ""), str(values.get("question") or ""))
    return None


def resume_supervisor(
    thread_id: str,
    *,
    approve: bool = True,
    pending_id: int | None = None,
    kind: str = "news",
    user_id: str = "",
) -> Agent_Output:
    tid = (thread_id or "").strip()
    graph = _build_graph()
    config = _config(tid)
    snap = graph.get_state(config)
    if not _hitl_waiting(snap):
        raise RuntimeError("Không có HITL đang chờ trên thread này.")
    values = getattr(snap, "values", None) or {}
    pending = _pending(values.get("db"))
    question = str(values.get("question") or "")

    if pending_id is not None:
        approve_pending_write(int(pending_id), approve=approve, kind=kind or "news")
        remaining = [
            pw
            for pw in pending
            if not (int(pw.id) == int(pending_id) and (pw.kind or "news") == (kind or "news"))
        ]
        if remaining:
            paused = _hitl_output(snap, tid, user_id, question)
            if paused.db:
                paused.db = paused.db.model_copy(update={"pending_writes": remaining})
            return paused

    with trace_answer(
        "agent_pr_ask", question, metadata={"thread_id": tid, "user_id": user_id, "resume": True}
    ) as t:
        patch: dict = {"_trace_span": t.get("_span")}
        as_node = None
        if pending_id is None and not approve:
            db = values.get("db")
            for pw in pending:
                approve_pending_write(pw.id, approve=False, kind=pw.kind or "news")
            rejected = (
                db.model_copy(update={"pending_writes": [], "detail": "HITL: từ chối toàn bộ"})
                if isinstance(db, DbOut)
                else DbOut(symbol=str(values.get("symbol") or ""), detail="HITL: từ chối toàn bộ")
            )
            patch.update({"db": rejected, "trace": list(values.get("trace") or []) + ["HITL: từ chối toàn bộ"]})
            as_node = "hitl_commit"
        graph.update_state(config, patch, **({"as_node": as_node} if as_node else {}))
        out = _finish(graph, config, tid, user_id, question, _invoke(graph, None, config))
        t["output"] = {"answer": out.answer, "trace": out.trace}
        return out


def save_graph_visualization(path: str = "images/supervisor_agent_graph.png") -> str:
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
    print(save_graph_visualization())
