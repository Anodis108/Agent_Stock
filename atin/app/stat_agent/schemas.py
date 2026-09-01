"""Hợp đồng vào/ra stat_agent — Text-to-SQL đọc-only trên bảng ra/vào khu vực."""

from __future__ import annotations

from pydantic import BaseModel


class Agent_Input(BaseModel):
    question: str


class QueryResult(BaseModel):
    sql: str = ""
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    error: str = ""


class Agent_Output(BaseModel):
    question: str
    answer: str
    query: QueryResult | None = None
    detail: str = ""
