"""Graph EvalAgent — ReAct chấm tin vs giá (keyword Sơ đồ 3d). Không gọi mạng.

    START → seed → agent ⇄ tools → pack → END

`score` ở nodes.py; tool bọc JSON. Pack ghi `eval` + `eval_turn` (hub so
với `turn` để không chấm lại cùng lượt HTTP).
"""

from __future__ import annotations

from functools import lru_cache, partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.eval_agent.state import EvalState
from app.agent_pr.eval_agent.tools import TOOLS
from app.agent_pr.react import agent_node, last_tool_json, parse_tool_output, should_continue
from app.monitoring.tracing import current_span, trace_step

_SYSTEM = """Bạn là EvalAgent — CHỈ chấm tin vs chiều giá bằng tool. Không crawl, không ghép câu user.

Quy tắc:
- Bắt buộc gọi score_price_vs_news với đúng JSON giá và tin trong tin nhắn (không sửa số).
- Không bịa sentiment. Từ khoá hẹp: không khớp → neutral / chưa rõ, không đoán.
- classify_headline / list_eval_keywords không thay score_price_vs_news.
- Xong tool thì dừng."""


def _seed(state: EvalState) -> dict:
    if state.get("messages"):
        return {}
    price, news = state.get("price"), state.get("news")
    body = (
        "Chấm khớp giá vs tin.\n"
        f"price_json={price.model_dump_json() if price else '{}'}\n"
        f"news_json={news.model_dump_json() if news else '{}'}"
    )
    return {"messages": [{"role": "user", "content": body}]}


def _query(state: EvalState) -> str:
    p = state.get("price")
    return getattr(p, "symbol", "") or "chấm tin vs giá"


def _pack(state: EvalState) -> dict:
    raw = last_tool_json(state, {"score_price_vs_news"})
    from app.agent_pr.eval_agent.nodes import score

    report = parse_tool_output(raw, Agent_Output) or score(state)["report"]
    return {"eval": report, "eval_turn": state.get("turn") or ""}


@lru_cache(maxsize=1)
def _build_graph():
    def offline(state: EvalState):
        return "score_price_vs_news", {
            "price_json": state["price"].model_dump_json() if state.get("price") else "{}",
            "news_json": state["news"].model_dump_json() if state.get("news") else "{}",
        }

    graph = StateGraph(EvalState)
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


def run_eval(inp: Agent_Input) -> Agent_Output:
    with trace_step(None, "agent_pr_eval", input=inp.price.symbol) as t:
        report = _build_graph().invoke(
            {
                "price": inp.price,
                "news": inp.news,
                "_trace_span": current_span(),
            }
        )["eval"]
        t["output"] = report.detail
        return report
