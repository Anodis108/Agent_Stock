"""Graph SynthesisAgent — ReAct ghép câu."""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.react import compile_react, last_tool_json
from app.agent_pr.synthesis_agent.nodes import compose
from app.agent_pr.synthesis_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState
from app.agent_pr.synthesis_agent.tools import TOOLS
from app.monitoring.tracing import trace_answer

_SYSTEM = (
    "Bạn là SynthesisAgent. Ghép câu tiếng Việt từ báo cáo có sẵn. "
    "Bắt buộc gọi compose_user_answer. Không bịa tin."
)


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
    if raw:
        return {"result": Agent_Output(answer=raw)}
    return compose(state)


@lru_cache(maxsize=1)
def _build_graph():
    return compile_react(
        state_schema=SynthState,
        catalog=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        seed=_seed,
        pack=_pack,
        offline_call=lambda s: (
            "compose_user_answer",
            {
                "price_json": s["price"].model_dump_json() if s.get("price") else "{}",
                "news_json": s["news"].model_dump_json() if s.get("news") else "{}",
                "eval_json": s["eval"].model_dump_json() if s.get("eval") else "{}",
                "n_history": int(s.get("n_history") or 0),
            },
        ),
    )


async def run_synthesis(inp: Agent_Input) -> Agent_Output:
    with trace_answer("agent_pr_synth", inp.price.symbol) as t:
        result = (
            await _build_graph().ainvoke(
                {
                    "price": inp.price,
                    "news": inp.news,
                    "eval": inp.eval,
                    "n_history": inp.n_history,
                    "_trace_span": t.get("_span"),
                }
            )
        )["result"]
        t["output"] = result.answer
        return result
