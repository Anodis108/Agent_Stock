"""RobotsCache phải tôn trọng robots.txt đúng chuẩn (im lặng = cho phép) và
cache theo origin để không tải lại nhiều lần."""

from __future__ import annotations

import httpx

from vn_stock_swarm.robots import RobotsCache

ROBOTS_TXT = "User-agent: *\nDisallow: /private/\n"


def _client(text: str, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=text)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_disallowed_path_is_blocked() -> None:
    """Path nằm trong Disallow phải bị chặn."""
    async with _client(ROBOTS_TXT) as client:
        cache = RobotsCache(client, user_agent="TestBot")
        allowed = await cache.is_allowed("https://example.com/private/page", "https://example.com")
        assert allowed is False


async def test_allowed_path_passes() -> None:
    """Path không nằm trong Disallow phải được cho qua."""
    async with _client(ROBOTS_TXT) as client:
        cache = RobotsCache(client, user_agent="TestBot")
        allowed = await cache.is_allowed("https://example.com/public/page", "https://example.com")
        assert allowed is True


async def test_missing_robots_txt_allows_everything() -> None:
    """Không tải được robots.txt (404) → coi như "cho phép tất cả", đúng
    chuẩn robots exclusion (im lặng nghĩa là không có giới hạn nào)."""
    async with _client("", status_code=404) as client:
        cache = RobotsCache(client, user_agent="TestBot")
        allowed = await cache.is_allowed("https://example.com/anything", "https://example.com")
        assert allowed is True


async def test_robots_txt_is_fetched_once_per_origin() -> None:
    """Cache phải hoạt động — gọi is_allowed nhiều lần trên cùng origin chỉ
    được tải robots.txt đúng 1 lần."""
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, text=ROBOTS_TXT)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cache = RobotsCache(client, user_agent="TestBot")
        await cache.is_allowed("https://example.com/a", "https://example.com")
        await cache.is_allowed("https://example.com/b", "https://example.com")
        assert calls["count"] == 1
