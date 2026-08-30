"""Hợp đồng vào/ra supervisor — hub Hierarchical (Sơ đồ 3d, rút gọn).

Hub không crawl / không chấm: gọi craw_agent + news_agent (đợt 1, song song),
rồi eval (2a) + synthesis (2b). Chưa DB / HITL. `answer` do synthesis_agent.

Agent_Input chỉ symbol (giống craw/news). Output gói 3 báo cáo để test/HTTP
thấy đủ, không phải user đọc raw JSON mãi.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Câu hỏi rút gọn: chỉ mã. Parse câu tiếng Việt thêm sau."""

    symbol: str                           # thô, vd. "hpg" — normalize upper


class Agent_Output(BaseModel):
    """Trả user + đủ báo cáo worker (trace tối giản)."""

    symbol: str
    answer: str                           # 1 dòng cho user
    price: PriceOut
    news: NewsOut
    eval: EvalOut
    trace: list[str] = []                 # đợt 1 / đợt 2 — chưa LangFuse
