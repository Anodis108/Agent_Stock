"""Hợp đồng vào/ra Hierarchical Coordinator (Sơ đồ 3 / 3d).

Hub không crawl / không chấm / không ghi DB: giao việc, thu báo cáo, trả user.
`answer` do SynthesisAgent; hub chỉ copy vào output.

Agent_Input chỉ symbol (parse câu tiếng Việt thêm sau). Output gói báo cáo
worker để test/HTTP thấy đủ — user đọc `answer` + `trace`.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Câu hỏi rút gọn: chỉ mã. Parse câu tiếng Việt thêm sau."""

    symbol: str                           # thô, vd. "hpg" — coordinator upper


class Agent_Output(BaseModel):
    """Trả user + đủ báo cáo worker (trace các lượt giao / nhận việc)."""

    symbol: str
    answer: str                           # 1 dòng — copy từ Synthesis, hub nói với user
    price: PriceOut
    news: NewsOut
    eval: EvalOut
    db: DbOut | None = None               # đợt 1: lịch sử + pending (HITL ngoài graph)
    trace: list[str] = []
