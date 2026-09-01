"""Graph NewsAgent — ReAct lấy tin CafeF thô. Không chấm tốt/xấu (đó là Eval).

    START → seed → agent ⇄ tools → pack → END

Pack ghi `news` (đã trùng tên hub). HITL không ở đây.
"""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.news_agent.state import NewsState
from app.agent_pr.news_agent.tools import TOOLS
from app.agent_pr.react import build_react_subgraph, fresh_user, last_tool_json, parse_tool_output
from app.monitoring.tracing import agent_span, trace_step

_SYSTEM = """Bạn là NewsAgent — CHỈ lấy tin thô CafeF. Không chấm tốt/xấu (Eval), không lấy giá, không ghi DB.

Quy tắc:
- Bắt buộc gọi fetch_cafef_news đúng một lần với mã đã chuẩn hoá.
- Không bịa tiêu đề / URL. Không tin thì articles rỗng — không bịa bài.
- describe_news_source chỉ khi hỏi nguồn; không thay fetch.
- Xong tool thì dừng."""


def _seed(state: NewsState) -> dict:
    symbol = str(state.get("symbol") or "").strip() or "?"
    return fresh_user(f"Lấy tin CafeF mã {symbol}.")


def _query(state: NewsState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: NewsState) -> dict:
    raw = last_tool_json(state, {"fetch_cafef_news"})
    news = parse_tool_output(raw, Agent_Output) or Agent_Output(
        symbol=str(state.get("symbol") or ""),
        articles=[],
        source=raw or str(state.get("error") or "cafef"),
    )
    return {"news": news}


def _offline(state: NewsState):
    return "fetch_cafef_news", {"symbol": str(state.get("symbol") or "")}


@lru_cache(maxsize=1)
def _build_graph():
    graph = build_react_subgraph(
        NewsState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        offline_call=_offline,
        agent_name="news_agent",
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def news_agent(state: NewsState) -> dict:
    """Node hub — mở span AGENT "news_agent" rồi chạy subgraph seed→agent→tools→pack."""
    symbol = str(state.get("symbol") or "")
    with agent_span(str(state.get("turn") or ""), "news_agent", input=symbol) as t:
        out = _build_graph().invoke(state)
        news = out.get("news")
        if news is not None:
            t["output"] = {"n_articles": len(news.articles)}
        return out


def run_news(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_news", input=symbol) as t:
        news = _build_graph().invoke({"symbol": symbol})["news"]
        t["output"] = {"n_articles": len(news.articles)}
        return news
