"""EvalAgent là agent MỚI của Sơ đồ 3d — chấm sentiment 3 lớp theo từ khoá,
đủ-bằng-chứng, và đối chiếu chiều giá với thiên hướng tin tức."""

from __future__ import annotations

from query.agents.eval_agent import EvalAgent, NewsSentiment
from query.agents.news_agent import NewsReport
from query.agents.price_agent import PriceReport


def _price(pct_change: float | None) -> PriceReport:
    return PriceReport(
        symbol="HPG", price_age_seconds=100.0, pct_change=pct_change, used_cache=True, detail=""
    )


def _news(*titles: str) -> NewsReport:
    articles = [
        {"title": t, "url": f"https://cafef.vn/{i}", "ts": 0.0} for i, t in enumerate(titles)
    ]
    return NewsReport(symbol="HPG", articles=articles, crawled_new=False, detail="")


def test_negative_keywords_classify_as_negative() -> None:
    """Từ khoá tiêu cực đúng theo ví dụ Sơ đồ 3d ("xả hàng", "giảm sàn") phải
    được chấm là tin tiêu cực."""
    report = EvalAgent().run(
        _price(-4.2), _news("Khối ngoại xả hàng HPG", "HPG giảm sàn phiên sáng")
    )
    assert report.sentiments == [NewsSentiment.NEGATIVE, NewsSentiment.NEGATIVE]
    assert report.negative_count == 2


def test_positive_keywords_classify_as_positive() -> None:
    report = EvalAgent().run(_price(3.0), _news("HPG báo lợi nhuận tăng trưởng mạnh"))
    assert report.sentiments == [NewsSentiment.POSITIVE]
    assert report.positive_count == 1


def test_no_keyword_match_classifies_as_neutral() -> None:
    """Tin không khớp từ khoá nào cả 2 nhóm là trung lập — không phải lỗi,
    chỉ là "không rõ hướng giá" (vd tin họp ĐHĐCĐ)."""
    report = EvalAgent().run(_price(0.0), _news("HPG họp ĐHĐCĐ tuần sau"))
    assert report.sentiments == [NewsSentiment.NEUTRAL]
    assert report.neutral_count == 1


def test_no_articles_means_not_enough_evidence() -> None:
    """Không có tin nào → has_enough_evidence phải là False."""
    report = EvalAgent().run(_price(-1.0), _news())
    assert report.has_enough_evidence is False


def test_price_falling_with_negative_news_matches() -> None:
    """Giá giảm + tin đa số tiêu cực → khớp (True) — đúng ví dụ HPG−4.2%
    trong Sơ đồ 3d."""
    report = EvalAgent().run(
        _price(-4.2), _news("Khối ngoại xả hàng HPG", "HPG giảm sàn phiên sáng")
    )
    assert report.price_matches_news is True


def test_price_falling_with_positive_news_does_not_match() -> None:
    """Giá giảm nhưng tin lại thiên tích cực → lệch (False) — cần cảnh báo
    mâu thuẫn cho user, không được im lặng bỏ qua."""
    report = EvalAgent().run(_price(-4.2), _news("HPG báo lợi nhuận tăng trưởng mạnh"))
    assert report.price_matches_news is False


def test_missing_price_change_means_unknown_match() -> None:
    """Chưa tính được % giá thì không đủ dữ liệu để đối chiếu — phải là None
    (chưa rõ), KHÔNG được nhầm với False (lệch)."""
    report = EvalAgent().run(_price(None), _news("Khối ngoại xả hàng HPG"))
    assert report.price_matches_news is None
