"""SynthesisAgent — chỉ ghép 4 báo cáo đã có sẵn thành câu trả lời, không tự
chấm lại bất cứ điều gì (đợt 2b, chạy sau cùng trong Sơ đồ 3d)."""

from __future__ import annotations

from vn_stock_swarm.query.agents.db_agent import DBReadResult
from vn_stock_swarm.query.agents.eval_agent import EvalReport, NewsSentiment
from vn_stock_swarm.query.agents.news_agent import NewsReport
from vn_stock_swarm.query.agents.price_agent import PriceReport
from vn_stock_swarm.query.agents.synthesis_agent import SynthesisAgent


def test_answer_mentions_price_direction_and_magnitude() -> None:
    """Câu trả lời phải nêu rõ chiều (tăng/giảm) và độ lớn % biến động."""
    price = PriceReport(
        symbol="HPG", price_age_seconds=100.0, pct_change=-4.2, used_cache=True, detail=""
    )
    news = NewsReport(symbol="HPG", articles=[], crawled_new=False, detail="")
    eval_report = EvalReport(symbol="HPG", sentiments=[], detail="")
    db_read = DBReadResult(symbol="HPG", price_history=[], saved_news=[], detail="")

    result = SynthesisAgent().run(price, news, eval_report, db_read)
    assert "giảm" in result.answer
    assert "4.2" in result.answer


def test_answer_flags_mismatch_between_price_and_news() -> None:
    """Khi EvalAgent báo lệch (giá và tin trái chiều), câu trả lời phải cảnh
    báo rõ ràng — không được im lặng bỏ qua mâu thuẫn."""
    price = PriceReport(
        symbol="HPG", price_age_seconds=100.0, pct_change=-4.2, used_cache=True, detail=""
    )
    news = NewsReport(
        symbol="HPG",
        articles=[{"title": "HPG báo lợi nhuận tăng trưởng", "url": "u", "ts": 0.0}],
        crawled_new=False,
        detail="",
    )
    eval_report = EvalReport(
        symbol="HPG",
        sentiments=[NewsSentiment.POSITIVE],
        positive_count=1,
        price_matches_news=False,
        detail="",
    )
    db_read = DBReadResult(symbol="HPG", price_history=[], saved_news=[], detail="")

    result = SynthesisAgent().run(price, news, eval_report, db_read)
    assert "KHÔNG khớp" in result.answer


def test_answer_handles_no_news_gracefully() -> None:
    """Không có tin nào tìm được vẫn phải trả lời được, không crash, không bịa tin."""
    price = PriceReport(
        symbol="HPG", price_age_seconds=100.0, pct_change=1.5, used_cache=True, detail=""
    )
    news = NewsReport(symbol="HPG", articles=[], crawled_new=False, detail="")
    eval_report = EvalReport(symbol="HPG", sentiments=[], detail="")
    db_read = DBReadResult(symbol="HPG", price_history=[], saved_news=[], detail="")

    result = SynthesisAgent().run(price, news, eval_report, db_read)
    assert "chưa tìm thấy tin" in result.answer
