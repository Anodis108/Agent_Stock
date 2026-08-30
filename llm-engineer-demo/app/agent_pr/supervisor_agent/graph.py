"""Graph Hierarchical Coordinator — hub + 5 worker subgraph (Sơ đồ 3 / 3d).

    START → coordinator ─┬─ Send → [price_agent] ─┐
                         ├─ Send → [news_agent]  ─┼→ after_wave1 → coordinator
                         └─ Send → [db_agent]    ─┘
                         ├─ eval_agent  → coordinator
                         ├─ synth_agent → coordinator
                         └─ reply → END

Khác bản cũ (normalize→gather→evaluate→assemble): đó là Sequential — worker
chỉ là hàm Python trong 1 node, vẽ ra một đường thẳng. Hierarchical = worker
là SUBGRAPH, mọi mũi tên đi qua hub, không có cạnh ngang giữa Price/News/DB.

Nhúng `_build_graph()` của từng agent — không gọi `run_crawl()` trong hub.
Cửa sổ (PriceWindow / …) đổi tên field (`quote`→`price`) vì LangGraph chỉ
khớp field trùng tên (bài học hierarchical.py).

Chưa LLM chọn worker. Chưa HITL trong graph (approve_pending_write ngoài).

Vẽ sơ đồ (từ llm-engineer-demo):
    python -m app.agent_pr.supervisor_agent.graph
→ images/supervisor_agent_graph.png (hoặc .mmd nếu mermaid.ink lỗi).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agent_pr.craw_agent.graph import _build_graph as _craw_graph
from app.agent_pr.db_agent.graph import _build_graph as _db_graph
from app.agent_pr.eval_agent.graph import _build_graph as _eval_graph
from app.agent_pr.news_agent.graph import _build_graph as _news_graph
from app.agent_pr.supervisor_agent.nodes import after_wave1, coordinator, reply, route_coordinator
from app.agent_pr.supervisor_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.supervisor_agent.state import (
    DbWindow,
    EvalWindow,
    PriceWindow,
    SupervisorState,
    SynthWindow,
)
from app.agent_pr.synthesis_agent.graph import _build_graph as _synth_graph
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
def _eval_window():
    """price+news vào → eval subgraph → lift report thành eval."""

    def lift(state: EvalWindow) -> dict:
        return {"eval": state["report"]}

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
        return {"draft": state["result"]}

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
        return {"db": state["result"]}

    graph = StateGraph(DbWindow)
    graph.add_node("db_graph", _db_graph())
    graph.add_node("lift_db", lift)
    graph.add_edge(START, "db_graph")
    graph.add_edge("db_graph", "lift_db")
    graph.add_edge("lift_db", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _build_graph():
    """Ráp hub + 5 worker. News không cần cửa sổ: field `news` đã trùng tên."""
    graph = StateGraph(SupervisorState)

    graph.add_node("coordinator", coordinator)
    graph.add_node("after_wave1", after_wave1)
    graph.add_node("reply", reply)

    graph.add_node("price_agent", _price_window())
    graph.add_node("news_agent", _news_graph())
    graph.add_node("db_agent", _db_window())
    graph.add_node("eval_agent", _eval_window())
    graph.add_node("synth_agent", _synth_window())

    graph.add_edge(START, "coordinator")
    graph.add_conditional_edges(
        "coordinator",
        route_coordinator,
        ["price_agent", "news_agent", "db_agent", "eval_agent", "synth_agent", "reply"],
    )

    # Đợt 1 hội tụ 1 node rồi mới về hub — xem after_wave1.
    graph.add_edge("price_agent", "after_wave1")
    graph.add_edge("news_agent", "after_wave1")
    graph.add_edge("db_agent", "after_wave1")
    graph.add_edge("after_wave1", "coordinator")

    graph.add_edge("eval_agent", "coordinator")
    graph.add_edge("synth_agent", "coordinator")
    graph.add_edge("reply", END)

    return graph.compile()


async def run_supervisor(inp: Agent_Input) -> Agent_Output:
    """Entry hub. recursion_limit: vòng coordinator → worker → coordinator.

    Giống run_agent: span cha `agent_pr_ask` + `_trace_span` vào state. Từng
    node gọi trace_step (cây coordinator / craw_* / news_* / db_* / eval /
    synth / reply). Send đợt 1 phải copy span vào payload — nhánh chỉ thấy
    Send, không thấy SupervisorState. No-op nếu MONITORING_ENABLED=false.
    """
    with trace_answer("agent_pr_ask", inp.symbol) as t:
        output: Agent_Output = (
            await _build_graph().ainvoke(
                {"symbol": inp.symbol, "trace": [], "_trace_span": t.get("_span")},
                config={"recursion_limit": 15},
            )
        )["output"]
        t["output"] = {"answer": output.answer, "trace": output.trace}
        return output


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
