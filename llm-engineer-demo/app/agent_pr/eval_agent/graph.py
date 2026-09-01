"""Graph EvalAgent — ReAct chấm tin vs giá (keyword Sơ đồ 3d). Không gọi mạng.

    START → seed → agent ⇄ tools → pack → END

`score` ở nodes.py; tool bọc JSON. Pack ghi `eval` + `eval_turn` (hub so
với `turn` để không chấm lại cùng lượt HTTP).
"""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.eval_agent.state import EvalState
from app.agent_pr.eval_agent.tools import TOOLS
from app.agent_pr.react import build_react_subgraph, fresh_user, last_tool_json, parse_tool_output
from app.monitoring.tracing import agent_span, trace_step

_SYSTEM = """Bạn là EvalAgent — CHỈ chấm tin vs chiều giá bằng tool. Không crawl, không ghép câu user.

Quy tắc:
- Bắt buộc gọi score_price_vs_news với đúng JSON giá và tin trong tin nhắn (không sửa số).
- Không bịa sentiment. Từ khoá hẹp: không khớp → neutral / chưa rõ, không đoán.
- classify_headline / list_eval_keywords không thay score_price_vs_news.
- Xong tool thì dừng."""


@lru_cache(maxsize=1)
def _build_graph():
    def _seed(state: EvalState) -> dict:
        price, news = state.get("price"), state.get("news")
        body = (
            "Chấm khớp giá vs tin.\n"
            f"price_json={price.model_dump_json() if price else '{}'}\n"
            f"news_json={news.model_dump_json() if news else '{}'}"
        )
        return fresh_user(body)

    def _pack(state: EvalState) -> dict:
        raw = last_tool_json(state, {"score_price_vs_news"})
        from app.agent_pr.eval_agent.nodes import score

        report = parse_tool_output(raw, Agent_Output) or score(state)["report"]
        return {"eval": report, "eval_turn": state.get("turn") or ""}

    graph = build_react_subgraph(
        EvalState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=lambda state: getattr(state.get("price"), "symbol", "") or "chấm tin vs giá",
        agent_name="eval_agent",
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def eval_agent(state: EvalState) -> dict:
    """Node hub — mở span AGENT "eval_agent" rồi chạy subgraph seed→agent→tools→pack."""
    symbol = str(getattr(state.get("price"), "symbol", "") or "")
    with agent_span(str(state.get("turn") or ""), "eval_agent", input=symbol) as t:
        out = _build_graph().invoke(state)
        report = out.get("eval")
        if report is not None:
            t["output"] = report.detail
        return out


def run_eval(inp: Agent_Input) -> Agent_Output:
    """Điểm vào HTTP `/pr/eval` — chạy EvalAgent độc lập (không qua hub)."""
    with trace_step(None, "agent_pr_eval", input=inp.price.symbol) as t:
        report = _build_graph().invoke(
            {
                "price": inp.price,
                "news": inp.news,
            }
        )["eval"]
        t["output"] = report.detail
        return report
