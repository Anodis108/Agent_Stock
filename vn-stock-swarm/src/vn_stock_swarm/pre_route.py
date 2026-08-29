"""Định tuyến TRƯỚC KHI FETCH — nhánh nét đứt màu cam trong Sơ đồ 1.

Chỉ đoán loại agent phù hợp dựa trên HÌNH DẠNG url (đuôi file, path) — không
hề tải trang. handoff.py mới là nơi sửa lại quyết định này SAU khi có tín hiệu
thật từ response (Content-Type, body rỗng kiểu SPA, bị chặn lặp lại...).
"""

from __future__ import annotations

from urllib.parse import urlparse

from vn_stock_swarm.urls import registered_domain

AGENT_TYPES = ("scout", "render", "document", "api", "stealth")


def guess_agent_type(url: str, render_domains: list[str] | None = None) -> str:
    """Đoán agent nào nên nhận ``url`` trước khi fetch.

    Thứ tự kiểm tra có ý nghĩa: đuôi file document/api được kiểm tra trước vì
    không mập mờ; whitelist render-domain là một "lối tắt" cho các site đã
    biết trước là JS nặng, để RenderAgent không phải chờ ScoutAgent phát hiện
    ra shell SPA rỗng rồi mới handoff; còn lại mặc định vào ScoutAgent.
    """
    path = urlparse(url).path.lower()

    if path.endswith(".pdf"):
        return "document"

    if "/api/" in path or path.endswith(".json"):
        return "api"

    if render_domains:
        domain = registered_domain(url)
        if domain in render_domains:
            return "render"

    return "scout"


def stream_name(agent_type: str) -> str:
    return f"url:discovered:{agent_type}"
