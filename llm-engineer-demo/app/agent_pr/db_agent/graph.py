"""Graph DBAgent — ReAct đọc/soạn sqlite. COMMIT vẫn ở hub HITL."""

from __future__ import annotations

import json
from functools import lru_cache

from app.agent_pr.db_agent.nodes import approve_pending_write, parse
from app.agent_pr.db_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.state import DBState
from app.agent_pr.db_agent.tools import TOOLS
from app.agent_pr.react import compile_react, last_tool_json
from app.agent_pr.symbol import normalize_symbol
from app.monitoring.tracing import trace_answer

__all__ = ["approve_pending_write", "run_db"]

_SYSTEM = (
    "Bạn là DBAgent. Đọc kho sqlite hoặc soạn lệnh ghi (chưa COMMIT). "
    "Chỉ đọc → read_symbol_store. Có tin/giá ứng viên → stage_new_rows. "
    "Không tự COMMIT."
)


def _seed(state: DBState) -> dict:
    if state.get("messages"):
        return {}
    symbol = str(state.get("symbol") or "").strip() or "?"
    news = state.get("candidate_news") or []
    prices = state.get("candidate_prices") or []
    if news or prices:
        nj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in news],
            ensure_ascii=False,
        )
        pj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in prices],
            ensure_ascii=False,
        )
        text = (
            f"Soạn lệnh ghi mã {symbol}. news_json={nj} prices_json={pj}. "
            "Gọi stage_new_rows."
        )
    else:
        text = f"Đọc lịch sử DB mã {symbol}. Gọi read_symbol_store."
    return {"messages": [{"role": "user", "content": text}]}


def _query(state: DBState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: DBState) -> dict:
    raw = last_tool_json(state, {"read_symbol_store", "stage_new_rows"})
    if raw:
        return {"result": Agent_Output.model_validate_json(raw)}
    return parse(state)


def _offline(state: DBState) -> tuple[str, dict]:
    symbol = str(state.get("symbol") or "")
    news = state.get("candidate_news") or []
    prices = state.get("candidate_prices") or []
    if news or prices:
        nj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in news],
            ensure_ascii=False,
        )
        pj = json.dumps(
            [x.model_dump() if hasattr(x, "model_dump") else dict(x) for x in prices],
            ensure_ascii=False,
        )
        return "stage_new_rows", {"symbol": symbol, "news_json": nj, "prices_json": pj}
    return "read_symbol_store", {"symbol": symbol}


@lru_cache(maxsize=1)
def _build_graph():
    return compile_react(
        state_schema=DBState,
        catalog=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        seed=_seed,
        pack=_pack,
        offline_call=_offline,
    )


async def run_db(inp: Agent_Input) -> Agent_Output:
    symbol = normalize_symbol(inp.symbol)
    with trace_answer("agent_pr_db", symbol) as t:
        result = (
            await _build_graph().ainvoke(
                {
                    "symbol": symbol,
                    "candidate_news": inp.candidate_news,
                    "candidate_prices": inp.candidate_prices,
                    "_trace_span": t.get("_span"),
                }
            )
        )["result"]
        t["output"] = result.detail
        return result
