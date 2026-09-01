"""Hợp đồng vào/ra Hierarchical Coordinator (Sơ đồ 3 / 3d).

Hub không crawl / không chấm / không ghi DB: parse câu (LLM), chọn worker,
thu báo cáo, trả user. Worker không nói với nhau.

`question` là câu user; `symbol` gợi ý mã (có thể trống — LLM tách từ câu).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

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


class RewrittenQuery(BaseModel):
    """Bài 1 structured output — rewrite không parse free-text."""

    query: str = Field(description="Một câu đã viết lại, tiếng Việt, giữ mã CP nếu có")
    symbol: str = Field(default="", description="Mã CP nếu nhận ra (HPG); để trống nếu không chắc")

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return (v or "").strip().upper()


class MemoryFact(BaseModel):
    """Trích 1 sự thật dài hạn — schema ép, không regex 'NONE'."""

    worth_saving: bool = Field(description="True nếu đáng nhớ xuyên phiên")
    fact: str = Field(default="", description="Một câu; rỗng nếu không đáng nhớ")


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
    # Cost & Token Tracking (Bài 8 Phần 1, Bài 13 Phần 3) — cộng dồn mọi lời gọi
    # LLM trong turn này. None nếu turn rỗng hoặc chưa gọi LLM nào (cache hit).
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
