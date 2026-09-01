"""Graph PriceAgent — ReAct lấy giá (vnstock). HITL không ở đây.

    START → seed → agent ⇄ tools → pack → END

IO thật vẫn `nodes.normalize/fetch/parse`; tool chỉ bọc để LLM chọn.
`pack` ghi `price` (tên field hub) — không lift `quote`.
`run_crawl` dùng cho GET /pr/price. Hub gọi qua node `price_agent` (không phải
`_build_graph()` thẳng) — wrapper mở span AGENT "price_agent" trước khi chạy
subgraph, để craw_fetch/craw_parse/llm.bind_tools lồng đúng dưới nó trên
Langfuse (xem monitoring/tracing.py: agent_span, step_parent).
"""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.craw_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.craw_agent.state import CrawlState
from app.agent_pr.craw_agent.tools import TOOLS
from app.agent_pr.react import build_react_subgraph, fresh_user, last_tool_json, parse_tool_output
from app.monitoring.tracing import agent_span, trace_step

_SYSTEM = """Bạn là PriceAgent — CHỈ lấy giá mã niêm yết VN (vnstock KBS). Không lấy tin, không chấm, không ghi DB.

Quy tắc:
- Bắt buộc gọi fetch_latest_close đúng một lần với mã đã chuẩn hoá (HPG, không hpg).
- Không bịa số. last=0 nghĩa là không lấy được — nói vậy, đừng bịa.
- describe_price_source chỉ khi user hỏi nguồn; không thay fetch.
- Xong tool thì dừng, không hỏi lại user."""


def _seed(state: CrawlState) -> dict:
    symbol = str(state.get("symbol") or "").strip() or "?"
    return fresh_user(f"Lấy giá đóng cửa mã {symbol}.")


def _query(state: CrawlState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: CrawlState) -> dict:
    raw = last_tool_json(state, {"fetch_latest_close"})
    quote = parse_tool_output(raw, Agent_Output) or Agent_Output(
        symbol=str(state.get("symbol") or ""),
        last=0,
        source=raw or str(state.get("error") or "vnstock (không lấy được)"),
    )
    return {"price": quote}


def _offline(state: CrawlState):
    return "fetch_latest_close", {"symbol": str(state.get("symbol") or "")}


@lru_cache(maxsize=1)
def _build_graph():
    graph = build_react_subgraph(
        CrawlState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        offline_call=_offline,
        agent_name="price_agent",
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def price_agent(state: CrawlState) -> dict:
    """Node hub — mở span AGENT "price_agent" rồi chạy subgraph seed→agent→tools→pack.

    Node con (normalize/fetch/parse, xem nodes.py) tự tìm span này qua
    step_parent(state, "price_agent") — không cần truyền tay.
    """
    symbol = str(state.get("symbol") or "")
    with agent_span(str(state.get("turn") or ""), "price_agent", input=symbol) as t:
        out = _build_graph().invoke(state)
        quote = out.get("price")
        if quote is not None:
            t["output"] = {"last": quote.last, "pct_change": quote.pct_change}
        return out


def run_crawl(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_price", input=symbol) as t:
        quote = _build_graph().invoke({"symbol": symbol})["price"]
        t["output"] = {"last": quote.last, "pct_change": quote.pct_change}
        return quote
