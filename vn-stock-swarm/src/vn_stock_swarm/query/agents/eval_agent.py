"""EvalAgent — agent MỚI trong Sơ đồ 3d, tách hẳn khỏi NewsAgent.

Đây chính là điểm khác biệt cốt lõi giữa Sơ đồ 3d và bản Hierarchical trước
đó: NewsAgent (news_agent.py) chỉ tìm tin, KHÔNG được phép tự phán tin đó tốt
hay xấu — việc đó dồn hết vào 1 chuyên gia riêng. EvalAgent không crawl,
không ghi DB; nó chỉ nhận `PriceReport` + `NewsReport` mà hub đã gói sẵn (chạy
ở ĐỢT 2a, sau khi cả Price lẫn News đã báo cáo xong) rồi:

  1. Chấm sentiment TỪNG tin bằng khớp từ khoá 3 lớp (tiêu cực/tích cực/trung
     lập) — heuristic đơn giản cho mục đích demo, không phải mô hình NLP thật.
  2. Đánh giá "đủ bằng chứng" — có ít nhất 1 tin, trong cửa sổ thời gian gần.
  3. Đối chiếu chiều giá (tăng/giảm/đi ngang) với sentiment đa số của các tin
     — "khớp" khi cùng chiều (giá giảm + đa số tin tiêu cực, hoặc ngược lại),
     "lệch" khi trái chiều nhau (đáng ngờ, cần nói rõ cho user).

Danh sách từ khoá lấy trực tiếp từ ví dụ trong Sơ đồ 3d (swarm-handoff-map_6.html,
mục "Sơ đồ 3d — Mermaid chi tiết") — không phải danh sách tự nghĩ ra, để khớp
đúng ví dụ HPG−4.2% + 2 tin tiêu cực đã minh hoạ trong sơ đồ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from vn_stock_swarm.query.agents.news_agent import NewsReport
from vn_stock_swarm.query.agents.price_agent import PriceReport

# Từ khoá tiêu cực/tích cực lấy đúng theo ví dụ trong Sơ đồ 3d — không đầy đủ,
# chỉ đủ minh hoạ ý tưởng "khớp từ khoá 3 lớp" cho mục đích demo. Tin không
# khớp từ khoá nào cả 2 nhóm coi là trung lập (không rõ hướng giá), không phải lỗi.
_NEGATIVE_KEYWORDS = ("xả hàng", "bán ròng", "giảm sàn", "cắt lỗ")
_POSITIVE_KEYWORDS = ("tăng trưởng", "lợi nhuận", "khuyến nghị mua")


class NewsSentiment(str, Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"
    NEUTRAL = "neutral"


@dataclass
class EvalReport:
    """Báo cáo EvalAgent gửi về hub — SynthesisAgent (đợt 2b) dựa vào đây để
    viết câu trả lời, KHÔNG tự chấm lại sentiment."""

    symbol: str
    # cùng thứ tự với NewsReport.articles
    sentiments: list[NewsSentiment] = field(default_factory=list)
    negative_count: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    has_enough_evidence: bool = False
    # None = không đủ dữ liệu để đối chiếu (thiếu giá hoặc tin)
    price_matches_news: bool | None = None
    detail: str = ""


class EvalAgent:
    """Chấm sentiment + đủ-bằng-chứng + khớp-giá-tin — xem docstring module."""

    def run(self, price: PriceReport, news: NewsReport) -> EvalReport:
        sentiments = [_classify(article.get("title", "")) for article in news.articles]
        negative_count = sentiments.count(NewsSentiment.NEGATIVE)
        positive_count = sentiments.count(NewsSentiment.POSITIVE)
        neutral_count = sentiments.count(NewsSentiment.NEUTRAL)

        has_enough_evidence = len(news.articles) > 0
        price_matches_news = _price_matches_news(
            price.pct_change, negative_count, positive_count
        )

        if price_matches_news is True:
            match_label = "có"
        elif price_matches_news is False:
            match_label = "không"
        else:
            match_label = "chưa rõ"
        detail = (
            f"{negative_count} tiêu cực · {positive_count} tích cực · {neutral_count} trung lập"
            f" — đủ chứng: {'có' if has_enough_evidence else 'không'}"
            f" — khớp giá: {match_label}"
        )

        return EvalReport(
            symbol=price.symbol,
            sentiments=sentiments,
            negative_count=negative_count,
            positive_count=positive_count,
            neutral_count=neutral_count,
            has_enough_evidence=has_enough_evidence,
            price_matches_news=price_matches_news,
            detail=detail,
        )


def _classify(title: object) -> NewsSentiment:
    text = str(title).lower()
    is_negative = any(keyword in text for keyword in _NEGATIVE_KEYWORDS)
    is_positive = any(keyword in text for keyword in _POSITIVE_KEYWORDS)
    # 1 tin khớp cả 2 nhóm từ khoá (hiếm, nhưng có thể) được coi là trung lập
    # thay vì đoán liều — an toàn hơn là báo sai chiều.
    if is_negative and not is_positive:
        return NewsSentiment.NEGATIVE
    if is_positive and not is_negative:
        return NewsSentiment.POSITIVE
    return NewsSentiment.NEUTRAL


def _price_matches_news(
    pct_change: float | None, negative_count: int, positive_count: int
) -> bool | None:
    """None khi thiếu dữ liệu để đối chiếu (chưa có % giá, hoặc không có tin
    thiên hướng rõ ràng nào) — SynthesisAgent cần biết phân biệt "chưa rõ" với
    "lệch", 2 điều này không nên gộp chung.
    """
    if pct_change is None or (negative_count == 0 and positive_count == 0):
        return None
    price_fell = pct_change < 0
    news_leans_negative = negative_count > positive_count
    news_leans_positive = positive_count > negative_count
    if price_fell and news_leans_negative:
        return True
    if not price_fell and news_leans_positive:
        return True
    if news_leans_negative or news_leans_positive:
        return False
    return None  # tin chia đều 2 phía, không có thiên hướng rõ để đối chiếu
