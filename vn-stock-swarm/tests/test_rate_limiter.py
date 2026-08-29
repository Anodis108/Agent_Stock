"""DomainRateLimiter phải giới hạn tốc độ THEO DOMAIN, phân tán qua Redis,
và hỗ trợ pace_multiplier cho StealthAgent."""

from __future__ import annotations

import time

from vn_stock_swarm.rate_limiter import DomainRateLimiter


async def test_first_call_does_not_block(redis) -> None:
    """Request đầu tiên trên 1 domain phải trả về ngay — chưa có gì để chờ."""
    limiter = DomainRateLimiter(redis, max_requests_per_second=10)
    start = time.monotonic()
    await limiter.wait("cafef.vn")
    assert time.monotonic() - start < 0.5


async def test_second_call_is_delayed(redis) -> None:
    """Request thứ 2 trên CÙNG domain, ngay sau request đầu, phải bị trì hoãn
    đủ khoảng cách tối thiểu (~200ms với 5 req/s)."""
    limiter = DomainRateLimiter(redis, max_requests_per_second=5)  # khoảng cách ~200ms
    await limiter.wait("cafef.vn")
    start = time.monotonic()
    await limiter.wait("cafef.vn")
    assert time.monotonic() - start >= 0.15


async def test_different_domains_do_not_block_each_other(redis) -> None:
    """Rate limit là theo TỪNG domain — domain A đầy hạn mức không ảnh hưởng domain B."""
    limiter = DomainRateLimiter(redis, max_requests_per_second=1)
    await limiter.wait("cafef.vn")
    start = time.monotonic()
    await limiter.wait("vietstock.vn")
    assert time.monotonic() - start < 0.2


async def test_zero_rps_disables_limiting(redis) -> None:
    """max_requests_per_second=0 là cách tắt limiter hoàn toàn (dùng cho test/dev)."""
    limiter = DomainRateLimiter(redis, max_requests_per_second=0)
    start = time.monotonic()
    await limiter.wait("cafef.vn")
    await limiter.wait("cafef.vn")
    assert time.monotonic() - start < 0.1


async def test_pace_multiplier_stretches_interval(redis) -> None:
    """StealthAgent truyền pace_multiplier > 1 để cố tình crawl chậm hẳn lại,
    bớt giống bot trên các domain từng chặn swarm."""
    fast = DomainRateLimiter(redis, max_requests_per_second=5, pace_multiplier=1.0)
    await fast.wait("fast.example.com")
    start = time.monotonic()
    await fast.wait("fast.example.com")
    fast_elapsed = time.monotonic() - start

    slow = DomainRateLimiter(redis, max_requests_per_second=5, pace_multiplier=5.0)
    await slow.wait("slow.example.com")
    start = time.monotonic()
    await slow.wait("slow.example.com")
    slow_elapsed = time.monotonic() - start

    assert slow_elapsed > fast_elapsed
