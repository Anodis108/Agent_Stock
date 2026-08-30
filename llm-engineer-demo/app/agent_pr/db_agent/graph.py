"""Graph db_agent — LangGraph chỉ ráp control flow.

Luồng (tuyến tính, giống craw_agent/news_agent — chưa conditional / Send):
    START → normalize → read → stage_writes → parse → END

So với craw_agent/news_agent: 4 node thay vì 3 — read (ĐỌC, tự động) và
stage_writes (SOẠN lệnh ghi, cũng tự động) tách riêng vì khác nguồn dữ liệu
(bảng `prices`/`news` vs bảng `news_pending`), dù cả hai đều không cần người.

HITL (duyệt lệnh ghi) CHỦ Ý không nằm trong graph này — `approve_pending_write`
là 1 hàm thường, gọi sau khi người quyết định (giống POST /approve tách khỏi
graph 2-đợt bên vn-stock-swarm/src/query/api.py). Nhét việc "chờ người" vào
1 StateGraph tuyến tính không interrupt sẽ hoặc chặn event loop hoặc phải giả
lập start/resume — không đáng cho slice demo này.

Entry `run_db` nhận Agent_Input, trả Agent_Output — không trả cả state.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent_pr.db_agent.nodes import approve_pending_write, normalize, parse, read, stage_writes
from app.agent_pr.db_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.state import DBState
from app.monitoring.tracing import trace_answer

__all__ = ["approve_pending_write", "run_db"]


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(DBState)
    graph.add_node("normalize", normalize)
    graph.add_node("read", read)
    graph.add_node("stage_writes", stage_writes)
    graph.add_node("parse", parse)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "read")
    graph.add_edge("read", "stage_writes")
    graph.add_edge("stage_writes", "parse")
    graph.add_edge("parse", END)
    return graph.compile()


async def run_db(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["result"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph.
    """
    with trace_answer("agent_pr_db", inp.symbol) as t:
        result = (
            await _build_graph().ainvoke(
                {
                    "symbol": inp.symbol,
                    "candidate_news": inp.candidate_news,
                    "_trace_span": t.get("_span"),
                }
            )
        )["result"]
        t["output"] = result.detail
        return result
