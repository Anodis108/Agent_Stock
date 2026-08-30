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

from langgraph.graph import END, START, StateGraph

from app.agent_pr.db_agent.nodes import approve_pending_write, normalize, parse, read, stage_writes
from app.agent_pr.db_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.state import DBState

__all__ = ["approve_pending_write", "run_db"]


def _graph():
    """Compile graph. Slice này gọi ít — không cache; read/stage_writes luôn hit sqlite."""
    g = StateGraph(DBState)
    g.add_node("normalize", normalize)
    g.add_node("read", read)
    g.add_node("stage_writes", stage_writes)
    g.add_node("parse", parse)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "read")
    g.add_edge("read", "stage_writes")
    g.add_edge("stage_writes", "parse")
    g.add_edge("parse", END)
    return g.compile()


async def run_db(inp: Agent_Input) -> Agent_Output:
    """Chạy graph, trả Agent_Output. ainvoke vì route FastAPI là async.

    Lấy `["result"]` sau ainvoke — parse luôn ghi field này; thiếu = bug graph.
    """
    return (
        await _graph().ainvoke({"symbol": inp.symbol, "candidate_news": inp.candidate_news})
    )["result"]
