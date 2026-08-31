"""Graph PriceAgent — ReAct: LLM chọn tool (vnstock), ToolNode chạy.

    START → seed → agent ⇄ tools → pack → END

Logic fetch/parse vẫn nodes.py. HITL không ở đây.
"""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.craw_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.craw_agent.state import CrawlState
from app.agent_pr.craw_agent.tools import TOOLS
from app.agent_pr.react import compile_react, last_tool_json
from app.agent_pr.symbol import normalize_symbol
from app.monitoring.tracing import trace_answer

_SYSTEM = (
    "Bạn là PriceAgent. Nhiệm vụ: lấy giá mã niêm yết VN. "
    "Bắt buộc gọi fetch_latest_close với mã đã chuẩn hoá. "
    "Không bịa số. Xong tool thì dừng, không hỏi lại user."
)


def _seed(state: CrawlState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    return {"messages": [{"role": "user", "content": f"Lấy giá đóng cửa mã {symbol}."}]}


def _query(state: CrawlState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: CrawlState) -> dict:
    raw = last_tool_json(state, {"fetch_latest_close"})
    if raw:
        return {"quote": Agent_Output.model_validate_json(raw)}
    symbol = str(state.get("symbol") or "")
    return {"quote": Agent_Output(symbol=symbol, last=0, source="vnstock (không lấy được)")}


@lru_cache(maxsize=1)
def _build_graph():
    return compile_react(
        state_schema=CrawlState,
        catalog=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        seed=_seed,
        pack=_pack,
        offline_call=lambda s: (
            "fetch_latest_close",
            {"symbol": str(s.get("symbol") or "")},
        ),
    )


async def run_crawl(inp: Agent_Input) -> Agent_Output:
    """Chạy ReAct, trả quote. Mã sai → ValueError trước LLM (giống guardrail cũ)."""
    symbol = normalize_symbol(inp.symbol)
    with trace_answer("agent_pr_price", symbol) as t:
        quote = (
            await _build_graph().ainvoke(
                {"symbol": symbol, "_trace_span": t.get("_span")}
            )
        )["quote"]
        t["output"] = {"last": quote.last, "pct_change": quote.pct_change}
        return quote
