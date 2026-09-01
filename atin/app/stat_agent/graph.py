"""Graph StatAgent — ReAct Text-to-SQL đọc-only.

    START → seed → agent ⇄ tools → pack → END

Agent đọc schema (get_db_schema) trước khi sinh SQL — đúng khuyến nghị tài
liệu ý tưởng ("cho Agent đọc Schema trước khi thực hiện, hạn chế số lần loop").
"""

from __future__ import annotations

from functools import lru_cache

from app.react import build_react_subgraph, fresh_user, last_tool_json, parse_tool_output
from app.stat_agent.schemas import Agent_Input, Agent_Output, QueryResult
from app.stat_agent.state import StatState
from app.stat_agent.tools import TOOLS

__all__ = ["run_stat"]

_SYSTEM = """Bạn là StatAgent — trả lời câu hỏi thống kê lượt ra/vào khu vực bằng SQL.

Quy tắc:
- LUÔN gọi get_db_schema trước khi sinh SQL nếu chưa biết schema.
- Không chắc giá trị khu_vuc → gọi list_khu_vuc trước khi lọc WHERE khu_vuc = ...
- Sinh đúng MỘT câu SELECT phù hợp câu hỏi rồi gọi run_sql_select.
- Chỉ SELECT — không insert/update/delete. Không bịa số liệu ngoài kết quả SQL.
- Có kết quả rồi thì dừng, không lặp lại tool đã đủ dữ liệu."""


def _seed(state: StatState) -> dict:
    question = str(state.get("question") or "").strip()
    return fresh_user(f"Câu hỏi: {question}")


def _offline(state: StatState) -> tuple[str, dict]:
    # Không API key / pytest: đi thẳng qua tool đọc schema — không gọi OpenAI.
    return "get_db_schema", {}


def _pack(state: StatState) -> dict:
    question = str(state.get("question") or "")
    raw = last_tool_json(state, {"run_sql_select"})
    query = parse_tool_output(raw, QueryResult)
    if query is None or query.error:
        result = Agent_Output(
            question=question,
            answer=query.error if query and query.error else "Chưa truy vấn được dữ liệu.",
            query=query,
            detail="lỗi truy vấn" if query and query.error else "chưa có kết quả SQL",
        )
        return {"result": result, "stat": result}

    answer = f"Kết quả: {query.row_count} dòng khớp truy vấn."
    if query.row_count == 1 and len(query.columns) == 1:
        answer = f"Kết quả: {query.rows[0][0]}"
    result = Agent_Output(question=question, answer=answer, query=query, detail=f"SQL: {query.sql}")
    return {"result": result, "stat": result}


@lru_cache(maxsize=1)
def _build_graph():
    graph = build_react_subgraph(
        StatState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        offline_call=_offline,
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def stat_agent(state: dict) -> dict:
    """Node hub — chạy subgraph seed→agent→tools→pack."""
    return _build_graph().invoke(state)


def run_stat(inp: Agent_Input) -> Agent_Output:
    question = (inp.question or "").strip()
    return _build_graph().invoke({"question": question})["stat"]
