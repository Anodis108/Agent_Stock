"""Graph Hierarchical Supervisor — cùng mẫu agent_m2 hierarchical.py.

    START → guardrail_input → rewrite → recall → compact → supervisor ─┬─(price_agent)→ [PriceAgent]   ─┐
                                            ├─(news_agent) → [NewsAgent]    ─┤
                                            ├─(db_agent)   → [DBAgent read] ─┼→ collect → supervisor → ...
                                            ├─(eval_agent) → [EvalAgent]    ─┤
                                            ├─(db_write)   → db_write       ─┘
                                            └─(done) → final_answer → (hitl_commit?) → reply
                                                       → guardrail_output → store → END

Khác agent_m2: HITL chỉ trước `hitl_commit` (ghi DB thật) — `interrupt_before`.
Short-term: `thread_id` + SqliteSaver (data/agent_pr.sqlite3). Long-term: `user_id` + Qdrant.
`turn` uuid mỗi HTTP — notes/eval/db_write không lấy nhầm checkpoint lượt trước.

Supervisor gọi LLM MỖI vòng (khác coordinator cũ chỉ lập plan 1 lần/turn) —
đơn giản hơn nhưng tốn thêm 1 lời gọi LLM mỗi worker. Đổi lấy: không còn máy
trạng thái `_coordinate` nhiều nhánh, đúng tinh thần agent_m2 Bài 6.

LangGraph chỉ copy field trùng tên. Pack worker ghi `price`/`news`/`eval`/`db`
— không node lift. `rows`/`messages` ở lại subgraph.

Vẽ: `python -m app.agent_pr.supervisor_agent.graph`
"""

from __future__ import annotations

import sqlite3
import uuid
from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agent_pr.guardrails import (
    guardrail_input,
    guardrail_output,
    route_after_guardrail,
    sanitize_stock_answer,
)
from app.agent_pr.craw_agent.graph import price_agent
from app.agent_pr.db_agent.graph import db_agent
from app.agent_pr.eval_agent.graph import eval_agent
from app.agent_pr.news_agent.graph import news_agent
from app.agent_pr.supervisor_agent.nodes import (
    _WORKER_DOMAINS,
    _make_collect_node,
    compact_history,
    db_write,
    final_answer_node,
    hitl_commit,
    recall_memory,
    reply,
    rewrite_question,
    route_after_final_answer,
    route_supervisor,
    should_compact_route,
    store_memory,
    supervisor_node,
)
from app.agent_pr.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.nodes import approve_pending_write
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.db_agent.schemas import PendingWrite
from app.agent_pr.supervisor_agent.state import SupervisorState
from app.monitoring.tracing import trace_answer

# SqliteSaver — cùng file data/agent_pr.sqlite3 với db_agent, bền qua restart/
# reload (khác MemorySaver RAM trước đây). check_same_thread=False vì FastAPI
# gọi từ threadpool (uvicorn chạy sync endpoint trong thread khác request).
_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "agent_pr.sqlite3"
_checkpointer = SqliteSaver(sqlite3.connect(str(_DB_PATH), check_same_thread=False))

_COLLECT_DOMAINS = ["price_agent", "news_agent", "db_agent", "eval_agent"]


def _hitl_waiting(snap) -> bool:
    """Graph dừng *trước* hitl_commit — chờ /pr/approve."""
    return tuple(getattr(snap, "next", None) or ()) == ("hitl_commit",)


def _pending(db) -> list[PendingWrite]:
    """Chuẩn hoá `db.pending_writes` (có thể là dict thô sau checkpoint deserialize) về list[PendingWrite]."""
    rows = list(getattr(db, "pending_writes", None) or []) if db else []
    out: list[PendingWrite] = []
    for r in rows:
        if isinstance(r, PendingWrite):
            out.append(r)
        elif isinstance(r, dict) and r.get("id") is not None:
            out.append(PendingWrite.model_validate(r))
    return out


def _hitl_output(snap, thread_id: str, user_id: str, question: str) -> Agent_Output:
    """Output tạm khi interrupt: final_answer đã xong, chưa COMMIT."""
    v = getattr(snap, "values", None) or {}
    pending = _pending(v.get("db"))
    symbol = str(v.get("symbol") or "")
    n = len(pending)
    answer = (str(v.get("final_answer") or "") or f"{symbol}: đã soạn {n} lệnh ghi bài chưa có.").rstrip()
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
        thread_id=thread_id,
        user_id=user_id,
    )


@lru_cache(maxsize=1)
def _build_graph():
    """Hub + 4 worker + db_write. HITL chỉ trước hitl_commit — worker không interrupt."""
    graph = StateGraph(SupervisorState)

    graph.add_node("guardrail_input", guardrail_input)
    graph.add_node("rewrite_question", rewrite_question)
    graph.add_node("guardrail_output", guardrail_output)
    graph.add_node("recall_memory", recall_memory)
    graph.add_node("compact_history", compact_history)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("final_answer", final_answer_node)
    graph.add_node("db_write", db_write)
    graph.add_node("hitl_commit", hitl_commit)
    graph.add_node("reply", reply)
    graph.add_node("store_memory", store_memory)

    graph.add_node("price_agent", price_agent)
    graph.add_node("news_agent", news_agent)
    graph.add_node("db_agent", db_agent)
    graph.add_node("eval_agent", eval_agent)

    graph.add_edge(START, "guardrail_input")
    # out_of_scope=True (câu ngoài phạm vi cổ phiếu VN) → thẳng guardrail_output,
    # bỏ qua rewrite/recall/supervisor — không tốn crawl/LLM cho câu chắc chắn từ chối.
    graph.add_conditional_edges(
        "guardrail_input",
        route_after_guardrail,
        {"rewrite_question": "rewrite_question", "guardrail_output": "guardrail_output"},
    )
    graph.add_edge("rewrite_question", "recall_memory")
    # Compact chủ động >40% window (nguyên tắc 40–60%) — dưới ngưỡng bỏ qua node.
    graph.add_conditional_edges(
        "recall_memory",
        should_compact_route,
        {"compact_history": "compact_history", "supervisor": "supervisor"},
    )
    graph.add_edge("compact_history", "supervisor")

    routing_map = {"final_answer": "final_answer"}
    for domain in _COLLECT_DOMAINS:
        collect_name = f"{domain}_collect"
        graph.add_node(collect_name, _make_collect_node(domain))
        graph.add_edge(domain, collect_name)
        graph.add_edge(collect_name, "supervisor")  # quay lại supervisor sau khi worker xong
        routing_map[domain] = domain
    routing_map["db_write"] = "db_write"
    graph.add_edge("db_write", "supervisor")

    graph.add_conditional_edges("supervisor", route_supervisor, routing_map)

    # done → tổng hợp câu trả lời → còn pending ghi DB thì HITL trước, không thì trả thẳng.
    graph.add_conditional_edges(
        "final_answer",
        route_after_final_answer,
        {"hitl_commit": "hitl_commit", "reply": "reply"},
    )
    graph.add_edge("hitl_commit", "reply")
    graph.add_edge("reply", "guardrail_output")
    graph.add_edge("guardrail_output", "store_memory")
    graph.add_edge("store_memory", END)

    return graph.compile(checkpointer=_checkpointer, interrupt_before=["hitl_commit"])


def _finish(graph, config, thread_id: str, user_id: str, question: str, result) -> Agent_Output:
    """Chuẩn hoá kết quả `graph.invoke(...)` thành Agent_Output — 3 trường hợp:

    1. `result["output"]` đã có (reply đã chạy xong) → gắn thread_id/user_id, trả thẳng.
    2. Graph dừng ở interrupt (HITL đang chờ) → `_hitl_output` (câu trả lời tạm).
    3. Còn lại (không nên xảy ra) → câu lỗi generic kèm state hiện có, tránh 500.
    """
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
        thread_id=thread_id,
        user_id=user_id,
    )


def run_supervisor(inp: Agent_Input) -> Agent_Output:
    """Điểm vào HTTP `/pr/ask` — validate input, tạo `turn` mới, chạy graph tới khi
    xong hoặc dừng ở HITL. `thread_id` bắt buộc (session giống `/assistant`);
    thiếu `question` nhưng có `symbol` thì tự soạn câu hỏi mặc định.
    """
    symbol = (inp.symbol or "").strip()
    question = (inp.question or "").strip()
    thread_id = (inp.thread_id or "").strip()
    user_id = (inp.user_id or "").strip()
    if not thread_id:
        raise ValueError("thread_id bắt buộc — client phải gửi id phiên (giống /assistant).")
    if not question and symbol:
        question = f"Phân tích biến động giá và tin tức liên quan đến mã {symbol.upper()} hôm nay."
    turn = str(uuid.uuid4())
    initial = {
        "symbol": symbol,
        "question": question,
        "turn": turn,
        "user_id": user_id,
        "skip_hitl": bool(inp.skip_hitl),
        "notes": {},
        "trace": [],
    }
    config = {"recursion_limit": 40, "configurable": {"thread_id": thread_id}}
    with trace_answer(
        "agent_pr_ask",
        question or symbol,
        metadata={"thread_id": thread_id, "user_id": user_id, "turn": turn},
    ) as t:
        graph = _build_graph()
        out = _finish(graph, config, thread_id, user_id, question, graph.invoke(input=initial, config=config))
        t["output"] = {"answer": out.answer, "trace": out.trace}
        return out


def last_supervisor_output(thread_id: str) -> Agent_Output | None:
    """Đọc lại kết quả lượt gần nhất của `thread_id` không cần invoke graph — dùng
    khi client refresh/poll trạng thái. None nếu thread trống hoặc chưa có output."""
    if not thread_id:
        return None
    snap = _build_graph().get_state({"configurable": {"thread_id": thread_id}})
    values = getattr(snap, "values", None) or {}
    out = values.get("output")
    if isinstance(out, Agent_Output):
        return out
    if _hitl_waiting(snap):
        return _hitl_output(snap, thread_id, str(values.get("user_id") or ""), str(values.get("question") or ""))
    return None


def resume_supervisor(
    thread_id: str,
    *,
    approve: bool = True,
    pending_id: int | None = None,
    kind: str = "news",
    user_id: str = "",
) -> Agent_Output:
    """Điểm vào HTTP `/pr/approve` — duyệt/từ chối lệnh ghi đang chờ HITL rồi resume graph.

    `pending_id` cho: chỉ quyết định 1 lệnh trong danh sách đang chờ — nếu còn
    lệnh khác chưa quyết, TRẢ VỀ NGAY (không resume graph), giữ nguyên trạng
    thái tạm dừng để client tiếp tục duyệt từng lệnh một.

    `pending_id=None`: quyết định cho TOÀN BỘ lô đang chờ. `approve=True` để
    graph tự chạy `hitl_commit` (node thật, COMMIT từng lệnh). `approve=False`
    reject thẳng tại đây rồi `graph.update_state(..., as_node="hitl_commit")`
    để giả lập hitl_commit đã chạy (tránh phải chạy node thật chỉ để reject).
    """
    graph = _build_graph()
    config = {"recursion_limit": 40, "configurable": {"thread_id": thread_id}}
    snap = graph.get_state(config)
    if not _hitl_waiting(snap):
        raise RuntimeError("Không có HITL đang chờ trên thread này.")
    values = getattr(snap, "values", None) or {}
    pending = _pending(values.get("db"))
    question = str(values.get("question") or "")
    turn = str(values.get("turn") or "")

    if pending_id is not None:
        approve_pending_write(int(pending_id), approve=approve, kind=kind or "news")
        remaining = [
            pw
            for pw in pending
            if not (int(pw.id) == int(pending_id) and (pw.kind or "news") == (kind or "news"))
        ]
        if remaining:
            paused = _hitl_output(snap, thread_id, user_id, question)
            if paused.db:
                paused.db = paused.db.model_copy(update={"pending_writes": remaining})
            return paused

    with trace_answer(
        "agent_pr_ask",
        question,
        metadata={"thread_id": thread_id, "user_id": user_id, "resume": True, "turn": turn},
    ) as t:
        patch: dict = {}
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
        if patch or as_node:
            graph.update_state(config, patch, **({"as_node": as_node} if as_node else {}))
        out = _finish(graph, config, thread_id, user_id, question, graph.invoke(input=None, config=config))
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
