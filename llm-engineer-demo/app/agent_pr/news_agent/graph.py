"""Graph NewsAgent — ReAct chọn tool CafeF."""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.news_agent.state import NewsState
from app.agent_pr.news_agent.tools import TOOLS
from app.agent_pr.react import compile_react, last_tool_json
from app.agent_pr.symbol import normalize_symbol
from app.monitoring.tracing import trace_answer

_SYSTEM = (
    "Bạn là NewsAgent. Lấy tin thô CafeF, không chấm tốt/xấu. "
    "Bắt buộc gọi fetch_cafef_news. Không bịa tiêu đề."
)


def _seed(state: NewsState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    return {"messages": [{"role": "user", "content": f"Lấy tin CafeF mã {symbol}."}]}


def _query(state: NewsState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: NewsState) -> dict:
    raw = last_tool_json(state, {"fetch_cafef_news"})
    if raw:
        return {"news": Agent_Output.model_validate_json(raw)}
    symbol = str(state.get("symbol") or "")
    return {"news": Agent_Output(symbol=symbol, articles=[])}


@lru_cache(maxsize=1)
def _build_graph():
    return compile_react(
        state_schema=NewsState,
        catalog=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        seed=_seed,
        pack=_pack,
        offline_call=lambda s: (
            "fetch_cafef_news",
            {"symbol": str(s.get("symbol") or "")},
        ),
    )


async def run_news(inp: Agent_Input) -> Agent_Output:
    symbol = normalize_symbol(inp.symbol)
    with trace_answer("agent_pr_news", symbol) as t:
        news = (
            await _build_graph().ainvoke(
                {"symbol": symbol, "_trace_span": t.get("_span")}
            )
        )["news"]
        t["output"] = {"n_articles": len(news.articles)}
        return news
