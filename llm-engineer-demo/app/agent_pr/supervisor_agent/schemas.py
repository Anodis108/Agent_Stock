"""Hợp đồng vào/ra Hierarchical Coordinator (bản supervisor/notes, cùng mẫu agent_m2 hierarchical.py).

Hub không crawl / không chấm / không ghi DB: parse câu (LLM rewrite), routing
(LLM chọn worker sau mỗi vòng), thu notes, gọi LLM tổng hợp câu trả lời cuối.
Worker không nói với nhau.

`question` là câu user; `symbol` gợi ý mã (có thể trống — rewrite tách từ câu).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Ít nhất một trong symbol / question. Supervisor LLM định tuyến từng vòng."""

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


class RoutingDecision(BaseModel):
    """Quyết định supervisor mỗi vòng — cùng mẫu agent_m2 `_RoutingDecision`."""

    next_agent: str = Field(
        description="Một trong: price_agent, news_agent, db_agent, db_write, eval_agent, done"
    )
    reasoning: str = Field(description="Lý do ngắn gọn cho quyết định")


class FinalAnswer(BaseModel):
    """Structured output cho final_answer_node — kèm usage qua chat_parsed_with_usage."""

    answer: str = Field(description="Câu trả lời cuối cho user, tiếng Việt, ngắn gọn")


class Agent_Output(BaseModel):
    """Trả user + báo cáo worker đã chạy (None = hub chưa giao agent đó)."""

    symbol: str
    question: str = ""
    answer: str
    price: PriceOut | None = None
    news: NewsOut | None = None
    eval: EvalOut | None = None
    db: DbOut | None = None
    trace: list[str] = []
    thread_id: str = ""
    user_id: str = ""
    # Cost & Token Tracking (Bài 8 Phần 1, Bài 13 Phần 3) — cộng dồn mọi lời gọi
    # LLM trong turn này. None nếu turn rỗng hoặc chưa gọi LLM nào.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
