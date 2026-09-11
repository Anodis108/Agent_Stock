"""Hợp đồng vào/ra eval_agent — HTTP / test / Synthesis đọc đúng type này.

Agent_Input: hub đã có Price (craw_agent) + News (news_agent). Eval KHÔNG
crawl, KHÔNG ghi DB — chỉ chấm. Đừng đưa symbol trần vào đây rồi tự gọi
vnstock/CafeF (lẫn trách nhiệm với 2 agent kia).

Agent_Output: sentiment từng tin + đủ chứng + khớp chiều giá. Synthesis
(slice sau) ghép câu, không chấm lại.

Từ khoá 3 lớp = fallback offline. Online: `chat_parsed(HeadlineBatch)` (Bài 1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Đầu vào graph — gói sẵn quote + tin thô từ 2 worker."""

    price: PriceOut                       # last / pct_change từ craw_agent
    news: NewsOut                         # articles title/url từ news_agent


class ScoredItem(BaseModel):
    """Một tin đã chấm — cùng thứ tự articles của NewsOut."""

    title: str                            # chép nguyên từ NewsItem.title, không sửa
    url: str = ""                         # chép nguyên từ NewsItem.url
    summary: str = ""                     # chép nguyên từ NewsItem.summary (SubTitle CafeF)
    sentiment: Literal["negative", "positive", "neutral"] = "neutral"  # _sentiment (fallback) hoặc LLM (HeadlineBatch) gán


class HeadlineBatch(BaseModel):
    """Bài 1 ProductReview — chấm cả lô tiêu đề, không parse free-text."""

    items: list[ScoredItem] = Field(description="Đúng thứ tự tiêu đề đã gửi, không thêm/bớt")


class Agent_Output(BaseModel):
    """Đầu ra graph — báo cáo eval, chưa phải câu trả lời user."""

    symbol: str                           # mã đã chuẩn hoá, lấy từ PriceOut.symbol
    items: list[ScoredItem] = []          # score ghi; assemble đưa vào đây
    negative_count: int = 0               # đếm items có sentiment=negative
    positive_count: int = 0               # đếm items có sentiment=positive
    neutral_count: int = 0                # đếm items có sentiment=neutral
    has_enough_evidence: bool = False     # True nếu có ≥ 1 tin
    price_matches_news: bool | None = None  # None = chưa rõ (thiếu % hoặc tin trung lập hết)
    detail: str = ""                      # 1 dòng: đếm + đủ chứng + khớp giá
    tool_trace: list[dict] = []           # chuỗi tool-call thật (Bài 5 trajectory eval) — xem react.extract_tool_trace
