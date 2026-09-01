"""Graph SynthesisAgent — ReAct ghép câu từ báo cáo đã có. Không crawl, không chấm.

    START → seed → agent ⇄ tools → pack → END

`compose` ở nodes.py. Pack ghi `draft` + `synth_turn` — hub đọc draft ở reply.
"""

from __future__ import annotations

from functools import lru_cache, partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.react import agent_node, last_tool_json, should_continue
from app.agent_pr.synthesis_agent.nodes import compose
from app.agent_pr.synthesis_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState
from app.agent_pr.synthesis_agent.tools import TOOLS
from app.monitoring.tracing import current_span, trace_step

_SYSTEM = """Bạn là SynthesisAgent — ghép câu tiếng Việt từ báo cáo ĐÃ CÓ. Không crawl, không chấm lại.

Quy tắc:
- Bắt buộc gọi compose_user_answer với JSON giá/tin/eval trong tin nhắn. Thiếu field thì để trống, không bịa.
- Chỉ dựa trên báo cáo; không thêm tin/số không có trong input (giống trợ lý pháp lý: grounded).
- Thiếu dữ liệu thì nói thiếu, không bịa. Ngắn gọn, tiếng Việt.
- format_pct_phrase / describe_synth_job không thay compose_user_answer.
- Xong tool thì dừng."""


def _seed(state: SynthState) -> dict:
    if state.get("messages"):
        return {}
    price, news, ev = state.get("price"), state.get("news"), state.get("eval")
    n = int(state.get("n_history") or 0)
    body = (
        "Ghép câu trả lời.\n"
        f"price_json={price.model_dump_json() if price else '{}'}\n"
        f"news_json={news.model_dump_json() if news else '{}'}\n"
        f"eval_json={ev.model_dump_json() if ev else '{}'}\n"
        f"n_history={n}"
    )
    return {"messages": [{"role": "user", "content": body}]}


def _query(state: SynthState) -> str:
    p = state.get("price")
    return getattr(p, "symbol", "") or "ghép câu trả lời"


def _pack(state: SynthState) -> dict:
    raw = last_tool_json(state, {"compose_user_answer"})
    result = Agent_Output(answer=raw) if raw else compose(state)["result"]
    return {"draft": result, "synth_turn": state.get("turn") or ""}


@lru_cache(maxsize=1)
def _build_graph():
    def offline(state: SynthState):
        return "compose_user_answer", {
            "price_json": state["price"].model_dump_json() if state.get("price") else "{}",
            "news_json": state["news"].model_dump_json() if state.get("news") else "{}",
            "eval_json": state["eval"].model_dump_json() if state.get("eval") else "{}",
            "n_history": int(state.get("n_history") or 0),
        }

    graph = StateGraph(SynthState)
    graph.add_node("seed", _seed)
    graph.add_node(
        "agent",
        partial(
            agent_node,
            catalog=TOOLS,
            system_prompt=_SYSTEM,
            query_fn=_query,
            offline_call=offline,
        ),
    )
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("pack", _pack)
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "pack": "pack"})
    graph.add_edge("tools", "agent")
    graph.add_edge("pack", END)
    return graph.compile()


def run_synthesis(inp: Agent_Input) -> Agent_Output:
    with trace_step(None, "agent_pr_synth", input=inp.price.symbol) as t:
        result = _build_graph().invoke(
            {
                "price": inp.price,
                "news": inp.news,
                "eval": inp.eval,
                "n_history": inp.n_history,
                "_trace_span": current_span(),
            }
        )["draft"]
        t["output"] = result.answer
        return result
