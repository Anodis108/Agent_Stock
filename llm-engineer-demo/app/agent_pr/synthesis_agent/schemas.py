"""Hợp đồng synthesis — ĐỢT 2b Sơ đồ 3d.

Chỉ GHÉP báo cáo đã có. Không crawl, không chấm lại sentiment/khớp-giá.
DB chưa bắt buộc: `n_history=0` nếu hub chưa gọi db_agent.

Offline: template join (test). Online: `chat_parsed(StockAnswer)` grounded (Bài 5).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.eval_agent.schemas import Agent_Output as EvalOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Đủ giá + tin + eval. Lịch sử DB optional."""

    price: PriceOut
    news: NewsOut
    eval: EvalOut
    n_history: int = 0                    # số phiên DB đã đọc; 0 = chưa có db_agent


class Citation(BaseModel):
    """Bài 5 AnswerWithCitations — nguồn là báo cáo worker, không bịa."""

    source: str = Field(description="price | news | eval | db")
    quote: str = Field(description="Sự thật lấy từ báo cáo")


class StockAnswer(BaseModel):
    """Structured generation (Bài 1 parse + Bài 5 grounding)."""

    answer: str = Field(
        description="Câu tiếng Việt trả lời đúng câu hỏi; CHỈ dùng số liệu/tiêu đề trong báo cáo"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Độ tin cậy 0–1 dựa trên coverage báo cáo")
    citations: list[Citation] = Field(default_factory=list, description="Trích dẫn từ báo cáo đã có")


class Agent_Output(BaseModel):
    """Câu trả lời — hub copy `answer`; confidence/citations cho groundedness."""

    answer: str
    confidence: float = 0.0
    citations: list[Citation] = Field(default_factory=list)
