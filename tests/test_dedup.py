"""claim_url phải nguyên tử: đúng 1 agent claim thành công cho mỗi URL, dù
nhiều agent (cùng loại hay khác loại) cùng nhìn thấy URL đó."""

from __future__ import annotations

from vn_stock_swarm.dedup import claim_url


async def test_claim_url_first_time_succeeds(redis) -> None:
    """Lần claim đầu tiên của 1 URL phải thành công — agent gọi nên tiến hành crawl."""
    assert await claim_url(redis, "https://cafef.vn") is True


async def test_claim_url_second_time_fails(redis) -> None:
    """Claim lần 2 trên CÙNG URL phải thất bại — đây là cơ chế chống trùng lặp crawl."""
    await claim_url(redis, "https://cafef.vn")
    assert await claim_url(redis, "https://cafef.vn") is False


async def test_claim_url_different_urls_both_succeed(redis) -> None:
    """URL khác nhau không tranh chấp — mỗi URL có bộ đếm claim riêng."""
    assert await claim_url(redis, "https://cafef.vn") is True
    assert await claim_url(redis, "https://vietstock.vn") is True
