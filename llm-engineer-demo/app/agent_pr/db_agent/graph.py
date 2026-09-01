"""Graph DBAgent — ReAct đọc sqlite / soạn pending. COMMIT ở hub HITL.

    START → seed → agent ⇄ tools → pack → END

Đọc: `read_symbol_store`. Có ứng viên crawl: `stage_new_rows` (chưa ghi bảng
chính). Pack ghi `db` + `db_lookup_turn` / `db_write_turn` theo `mode`.
"""

from __future__ import annotations

import json
from functools import lru_cache

from app.agent_pr.db_agent.nodes import approve_pending_write, parse
from app.agent_pr.db_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.db_agent.state import DBState
from app.agent_pr.db_agent.tools import TOOLS

from app.agent_pr.react import build_react_subgraph, fresh_user, last_tool_json, parse_tool_output
from app.monitoring.tracing import agent_span, trace_step

__all__ = ["approve_pending_write", "run_db"]

_SYSTEM = """Bạn là DBAgent — đọc sqlite hoặc soạn lệnh ghi. Không crawl, không COMMIT.

Quy tắc:
- Chỉ đọc (không có tin/giá ứng viên) → read_symbol_store đúng một lần.
- Có news_json/prices_json ứng viên → stage_new_rows đúng một lần. Chưa COMMIT — hub HITL mới ghi bảng chính.
- Không tự COMMIT. Không bịa hàng. Không gọi cả hai tool nếu seed đã chỉ một việc.
- describe_db_hitl chỉ khi hỏi vì sao cần duyệt; không thay đọc/soạn.
- Xong tool thì dừng."""


def _seed(state: DBState) -> dict:
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
    return fresh_user(text)


def _query(state: DBState) -> str:
    return str(state.get("symbol") or "")


def _pack(state: DBState) -> dict:
    raw = last_tool_json(state, {"read_symbol_store", "stage_new_rows"})
    result = parse_tool_output(raw, Agent_Output) or parse(state)["result"]
    turn = state.get("turn") or ""  # Send từ hub; thiếu field `turn` trên DBState thì pack ghi rỗng → loop lookup
    key = "db_write_turn" if str(state.get("mode") or "read") == "write" else "db_lookup_turn"
    return {"db": result, key: turn}


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
    graph = build_react_subgraph(
        DBState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=_query,
        offline_call=_offline,
        agent_name="db_agent",
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def db_agent(state: DBState) -> dict:
    """Node hub — mở span AGENT "db_agent" rồi chạy subgraph seed→agent→tools→pack."""
    symbol = str(state.get("symbol") or "")
    with agent_span(str(state.get("turn") or ""), "db_agent", input=symbol) as t:
        out = _build_graph().invoke(state)
        result = out.get("db")
        if result is not None:
            t["output"] = result.detail
        return out


def run_db(inp: Agent_Input) -> Agent_Output:
    symbol = (inp.symbol or "").strip().upper()
    with trace_step(None, "agent_pr_db", input=symbol) as t:
        result = _build_graph().invoke(
            {
                "symbol": symbol,
                "candidate_news": inp.candidate_news,
                "candidate_prices": inp.candidate_prices,
            }
        )["db"]
        t["output"] = result.detail
        return result
