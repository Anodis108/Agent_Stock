"""Fetch qua trình duyệt headless (Playwright) — dành riêng cho RenderAgent."""

from __future__ import annotations

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.logging_config import get_logger

logger = get_logger(component="render_fetcher")

# Thời gian chờ mạng "im lặng" sau khi điều hướng xong trước khi đọc DOM — đủ
# để lần fetch dữ liệu đầu tiên của 1 bảng giá SPA kịp về, nhưng không treo
# crawl vô hạn trên những trang cứ poll liên tục không ngừng.
_NETWORK_IDLE_TIMEOUT_MS = 15_000


async def fetch_rendered_page(
    url: str, user_agent: str, timeout_seconds: float
) -> RawResponse | None:
    """Fetch ``url`` qua 1 tab Chromium headless, trả về HTML đã render đầy đủ
    dưới dạng RawResponse.

    Playwright được import trễ (bên trong hàm) thay vì lúc load module: chỉ
    RenderAgent cần tới nó, và browser binary của nó là một gói cài đặt nặng,
    không bắt buộc (xem Dockerfile.render) — phần còn lại của swarm phải tiếp
    tục chạy được, kể cả khi chỉ import module này mà package chưa cài.
    """
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error(
            "playwright_not_installed",
            hint="RenderAgent cần package 'playwright' và browser binary "
            "(chạy: pip install playwright && playwright install chromium)",
        )
        return None

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=user_agent)
                response = await page.goto(
                    url, timeout=timeout_seconds * 1000, wait_until="domcontentloaded"
                )
                try:
                    await page.wait_for_load_state(
                        "networkidle", timeout=_NETWORK_IDLE_TIMEOUT_MS
                    )
                except PlaywrightError:
                    pass  # trang cứ poll mãi (thường gặp ở bảng giá) — dùng tạm những gì có

                html = await page.content()
                status_code = response.status if response else 200
                content_type = "text/html"
                body = html.encode("utf-8")
                return RawResponse(
                    url=page.url,
                    status_code=status_code,
                    content_type=content_type,
                    body=body,
                    text=html,
                )
            finally:
                await browser.close()
    except PlaywrightError as exc:
        logger.warning("render_fetch_failed", url=url, error=str(exc))
        return None
