"""Hợp đồng vào/ra Hierarchical Coordinator (Sơ đồ 3 / 3d).

Hub không crawl / không chấm / không ghi DB: parse câu (LLM), chọn worker,
thu báo cáo, trả user. Worker không nói với nhau.

`question` là câu user; `symbol` gợi ý mã (có thể trống — LLM tách từ câu).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Ít nhất một trong symbol / question. Coordinator LLM chốt mã + plan."""

    symbol: str = ""
    question: str = ""
    thread_id: str = Field(min_length=1, description="Short-term: id phiên. Client bắt buộc gửi.")
    user_id: str = ""                 # long-term: trống → không recall/store
    skip_hitl: bool = False           # True: pytest — không interrupt_before hitl_commit


class AgentPlan(BaseModel):
    """Quyết định hub — LLM chọn worker nào chạy. Eval cần giá+tin."""

    symbol: str = Field(description="Mã CP niêm yết VN, vd. HPG, VNM, MWG")
    use_price: bool = Field(description="Cần giá / % biến động")
    use_news: bool = Field(description="Cần tin tức")
    use_db: bool = Field(description="Cần lịch sử trong DB")
    use_eval: bool = Field(description="Cần chấm tin vs giá — chỉ true nếu có giá VÀ tin")
    use_synth: bool = Field(description="Cần ghép câu trả lời có cấu trúc")
    reasoning: str = Field(description="Lý do ngắn các cờ true/false")


class Agent_Output(BaseModel):
    """Trả user + báo cáo worker đã chạy (None = hub không giao agent đó)."""

    symbol: str
    question: str = ""
    answer: str
    price: PriceOut | None = None
    news: NewsOut | None = None
    eval: EvalOut | None = None
    db: DbOut | None = None
    trace: list[str] = []
    plan: AgentPlan | None = None
    thread_id: str = ""
    user_id: str = ""
