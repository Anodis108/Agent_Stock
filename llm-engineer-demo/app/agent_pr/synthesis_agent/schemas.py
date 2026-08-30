"""Hợp đồng synthesis — ĐỢT 2b Sơ đồ 3d.

Chỉ GHÉP báo cáo đã có. Không crawl, không chấm lại sentiment/khớp-giá.
DB chưa bắt buộc: `n_history=0` nếu hub chưa gọi db_agent.

`answer` là tiếng Việt có cấu trúc — hub gửi user, synthesis không tự nói.
Chưa LLM (plan.md): template join, giống swarm SynthesisAgent.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Đủ giá + tin + eval. Lịch sử DB optional."""

    price: PriceOut
    news: NewsOut
    eval: EvalOut
    n_history: int = 0                    # số phiên DB đã đọc; 0 = chưa có db_agent


class Agent_Output(BaseModel):
    """Một câu trả lời — hub copy vào Supervisor.answer."""

    answer: str
