"""Hợp đồng vào/ra eval_agent — HTTP / test / Synthesis đọc đúng type này.

Agent_Input: hub đã có Price (craw_agent) + News (news_agent). Eval KHÔNG
crawl, KHÔNG ghi DB — chỉ chấm. Đừng đưa symbol trần vào đây rồi tự gọi
vnstock/CafeF (lẫn trách nhiệm với 2 agent kia).

Agent_Output: sentiment từng tin + đủ chứng + khớp chiều giá. Synthesis
(slice sau) ghép câu, không chấm lại.

Từ khoá 3 lớp lấy đúng Sơ đồ 3d (swarm eval_agent.py), không bịa thêm —
heuristic demo, chưa LLM.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut


class Agent_Input(BaseModel):
    """Đầu vào graph — gói sẵn quote + tin thô từ 2 worker."""

    price: PriceOut                       # last / pct_change từ craw_agent
    news: NewsOut                         # articles title/url từ news_agent


class ScoredItem(BaseModel):
    """Một tin đã chấm — cùng thứ tự articles của NewsOut."""

    title: str
    url: str = ""
    sentiment: str                        # negative | positive | neutral


class Agent_Output(BaseModel):
    """Đầu ra graph — báo cáo eval, chưa phải câu trả lời user."""

    symbol: str
    items: list[ScoredItem] = []          # score ghi; assemble đưa vào đây
    negative_count: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    has_enough_evidence: bool = False     # True nếu có ≥ 1 tin
    price_matches_news: bool | None = None  # None = chưa rõ (thiếu % hoặc tin trung lập hết)
    detail: str = ""                      # 1 dòng: đếm + đủ chứng + khớp giá
