"""Tools StatAgent — đúng 3 tool (dưới ngưỡng 5 tool/agent theo tài liệu ý tưởng).

Đọc-only: không tool nào ghi DB. `run_sql_select` validate trong nodes.run_query
trước khi thực thi — chặn UPDATE/DELETE/DDL, giới hạn số dòng + thời gian chạy.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.stat_agent.nodes import SCHEMA_DESC, ensure_seed_data, run_query


@tool
def get_db_schema() -> str:
    """Xem schema bảng luot_ra_vao (ra/vào khu vực) trước khi sinh SQL."""
    return SCHEMA_DESC


@tool
def run_sql_select(sql: str) -> str:
    """Chạy 1 câu SQL SELECT read-only trên bảng luot_ra_vao, trả JSON kết quả."""
    ensure_seed_data()
    return run_query(sql).model_dump_json()


@tool
def list_khu_vuc() -> str:
    """Liệt kê tên các khu vực có trong dữ liệu — tránh agent đoán sai giá trị lọc."""
    ensure_seed_data()
    result = run_query("SELECT DISTINCT khu_vuc FROM luot_ra_vao ORDER BY khu_vuc")
    return result.model_dump_json()


TOOLS = [get_db_schema, run_sql_select, list_khu_vuc]
