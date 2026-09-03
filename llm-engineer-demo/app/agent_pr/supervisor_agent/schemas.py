"""Hợp đồng vào/ra Hierarchical Coordinator (bản supervisor/notes, cùng mẫu agent_m2 hierarchical.py).

Hub không crawl / không chấm / không ghi DB: parse câu (LLM rewrite), routing
(LLM chọn worker sau mỗi vòng), thu notes, gọi LLM tổng hợp câu trả lời cuối.
Worker không nói với nhau.

`question` là câu user; `symbol` gợi ý mã (có thể trống — rewrite tách từ câu).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Ít nhất một trong symbol / question. Supervisor LLM định tuyến từng vòng.

    `symbols`: nhiều mã (vd so sánh HPG vs FPT). `symbol` giữ lại cho tương
    thích HTTP cũ — nếu chỉ gửi `symbol`, tự nâng thành `symbols=[symbol]`.
    """

    symbol: str = ""                  # mã đơn (tương thích HTTP cũ) — nâng thành symbols nếu symbols rỗng
    symbols: list[str] = Field(default_factory=list, description="Nhiều mã (vd so sánh); ưu tiên hơn symbol")
    question: str = ""                # câu hỏi user; rỗng + có symbol thì run_supervisor tự soạn câu mặc định
    thread_id: str = Field(min_length=1, description="Short-term: id phiên. Client bắt buộc gửi.")
    user_id: str = ""                 # long-term: trống → không recall/store
    skip_hitl: bool = False           # True: pytest — không interrupt_before hitl_commit

    @model_validator(mode="after")
    def _fill_symbols(self) -> "Agent_Input":
        if not self.symbols and self.symbol.strip():
            self.symbols = [self.symbol.strip().upper()]
        return self


class RewrittenQuery(BaseModel):
    """Bài 1 structured output — rewrite không parse free-text.

    `symbols`: TẤT CẢ mã nhận ra trong câu hỏi (so sánh/liệt kê nhiều mã thì
    liệt kê đủ, không chỉ lấy 1)."""

    query: str = Field(description="Một câu đã viết lại, tiếng Việt, giữ mã CP nếu có")
    symbols: list[str] = Field(default_factory=list, description="Tất cả mã CP nhận ra, vd [HPG, FPT]; rỗng nếu không chắc")

    @field_validator("symbols")
    @classmethod
    def _clean_symbols(cls, v: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for s in v:
            s = (s or "").strip().upper()
            if s and s not in seen:
                seen[s] = None
        return list(seen)


class MemoryFact(BaseModel):
    """Trích 1 sự thật dài hạn — schema ép, không regex 'NONE'."""

    worth_saving: bool = Field(description="True nếu đáng nhớ xuyên phiên")
    fact: str = Field(default="", description="Một câu; rỗng nếu không đáng nhớ")


class RoutingDecision(BaseModel):
    """Quyết định supervisor mỗi vòng — cùng mẫu agent_m2 `_RoutingDecision`."""

    next_agent: str = Field(
        description="Một trong: price_agent, news_agent, db_agent, db_write, eval_agent, done"
    )
    symbol: str = Field(
        default="", description="Mã CP bước này áp dụng — bắt buộc nếu next_agent là 1 trong 4 worker"
    )
    reasoning: str = Field(description="Lý do ngắn gọn cho quyết định")


class FinalAnswer(BaseModel):
    """Structured output cho final_answer_node — kèm usage qua chat_parsed_with_usage."""

    answer: str = Field(description="Câu trả lời cuối cho user, tiếng Việt, ngắn gọn")


class Agent_Output(BaseModel):
    """Trả user + báo cáo worker đã chạy (None = hub chưa giao agent đó).

    `price`/`news`/`eval`/`db` là field LEGACY — luôn phản ánh `symbols[0]`
    (mã đầu tiên), giữ tương thích client/test cũ. Multi-symbol thật đọc
    `*_by_symbol` (key = mã CP)."""

    symbol: str                           # symbols[0] — mã đại diện cho field legacy price/news/eval/db
    symbols: list[str] = []               # TẤT CẢ mã đã xử lý trong turn
    question: str = ""                    # câu user gốc (chưa rewrite) — reply/final_answer đọc
    answer: str                           # câu trả lời cuối, final_answer_node tổng hợp từ notes
    price: PriceOut | None = None         # legacy — luôn = price_by_symbol[symbols[0]]
    news: NewsOut | None = None           # legacy — luôn = news_by_symbol[symbols[0]]
    eval: EvalOut | None = None           # legacy — luôn = eval_by_symbol[symbols[0]]
    db: DbOut | None = None               # legacy — luôn = db_by_symbol[symbols[0]]
    price_by_symbol: dict[str, PriceOut] = {}  # reply ghi từ SupervisorState["price"]
    news_by_symbol: dict[str, NewsOut] = {}    # reply ghi từ SupervisorState["news"]
    eval_by_symbol: dict[str, EvalOut] = {}    # reply ghi từ SupervisorState["eval"]
    db_by_symbol: dict[str, DbOut] = {}        # reply ghi từ SupervisorState["db"]; HITL cũng cập nhật ở đây
    trace: list[str] = []                 # log các bước supervisor/collect/reply đã chạy trong turn
    thread_id: str = ""                   # gắn lại sau khi graph chạy xong — client dùng để resume/poll
    user_id: str = ""                     # gắn lại sau khi graph chạy xong — rỗng nếu turn không có long-term
    # Cost & Token Tracking (Bài 8 Phần 1, Bài 13 Phần 3) — cộng dồn mọi lời gọi
    # LLM trong turn này. None nếu turn rỗng hoặc chưa gọi LLM nào.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
