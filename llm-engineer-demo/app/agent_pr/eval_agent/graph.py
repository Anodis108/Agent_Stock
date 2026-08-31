"""Graph EvalAgent — ReAct: LLM chọn tool chấm keyword."""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.eval_agent.state import EvalState
from app.agent_pr.eval_agent.tools import TOOLS
from app.agent_pr.react import compile_react, last_tool_json
from app.monitoring.tracing import trace_answer

_SYSTEM = (
    "Bạn là EvalAgent. Chấm tin vs giá bằng tool, không bịa sentiment. "
    "Bắt buộc gọi score_price_vs_news với JSON giá và tin đã có trong tin nhắn."
)


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
    if raw:
        return {"report": Agent_Output.model_validate_json(raw)}
    from app.agent_pr.eval_agent.nodes import score

    return score(state)


@lru_cache(maxsize=1)
def _build_graph():
    return compile_react(
        state_schema=EvalState,
        catalog=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        seed=_seed,
        pack=_pack,
        offline_call=lambda s: (
            "score_price_vs_news",
            {
                "price_json": s["price"].model_dump_json() if s.get("price") else "{}",
                "news_json": s["news"].model_dump_json() if s.get("news") else "{}",
            },
        ),
    )


async def run_eval(inp: Agent_Input) -> Agent_Output:
    with trace_answer("agent_pr_eval", inp.price.symbol) as t:
        report = (
            await _build_graph().ainvoke(
                {"price": inp.price, "news": inp.news, "_trace_span": t.get("_span")}
            )
        )["report"]
        t["output"] = report.detail
        return report
