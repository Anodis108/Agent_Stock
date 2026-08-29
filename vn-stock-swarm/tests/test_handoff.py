"""decide_handoff là định tuyến SAU-fetch (nét liền cam, Sơ đồ 1) — quyết định
dựa trên tín hiệu THẬT của response, không phải hình dạng URL."""

from __future__ import annotations

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.handoff import (
    HandoffReason,
    decide_handoff,
    is_stealth_domain,
    mark_domain_for_stealth,
    record_block,
    reset_block_counter,
)


def _response(
    content_type: str = "text/html",
    text: str = "<html><body><h1>Real content here, long enough</h1></body></html>",
    body: bytes | None = None,
    status_code: int = 200,
) -> RawResponse:
    return RawResponse(
        url="https://cafef.vn/page",
        status_code=status_code,
        content_type=content_type,
        body=body if body is not None else text.encode("utf-8"),
        text=text,
    )


def test_transport_failure_never_hands_off() -> None:
    """Lỗi tầng transport (response=None) không phải tín hiệu nội dung —
    không có gì để handoff, chỉ đơn giản là request thất bại."""
    assert decide_handoff(None, "scout", consecutive_blocks=0, block_threshold=3) is None


def test_normal_html_from_scout_does_not_hand_off() -> None:
    """HTML bình thường đúng như ScoutAgent kỳ vọng — không handoff."""
    decision = decide_handoff(_response(), "scout", consecutive_blocks=0, block_threshold=3)
    assert decision is None


def test_pdf_content_type_from_scout_hands_off_to_document() -> None:
    """ScoutAgent gặp Content-Type PDF ngoài dự đoán → handoff sang DocumentAgent."""
    decision = decide_handoff(
        _response(content_type="application/pdf", body=b"%PDF-1.4"),
        "scout",
        consecutive_blocks=0,
        block_threshold=3,
    )
    assert decision is not None
    assert decision.target_agent_type == "document"
    assert decision.reason == HandoffReason.CONTENT_TYPE_MISMATCH_PDF


def test_json_content_type_from_scout_hands_off_to_api() -> None:
    """ScoutAgent gặp Content-Type JSON ngoài dự đoán → handoff sang ApiAgent."""
    decision = decide_handoff(
        _response(content_type="application/json", text="{}"),
        "scout",
        consecutive_blocks=0,
        block_threshold=3,
    )
    assert decision is not None
    assert decision.target_agent_type == "api"
    assert decision.reason == HandoffReason.CONTENT_TYPE_MISMATCH_JSON


def test_empty_spa_shell_hands_off_to_render() -> None:
    """Body gần rỗng kèm dấu hiệu shell SPA (id="root") → handoff sang RenderAgent."""
    spa_html = '<html><body><div id="root"></div></body></html>'
    decision = decide_handoff(
        _response(text=spa_html), "scout", consecutive_blocks=0, block_threshold=3
    )
    assert decision is not None
    assert decision.target_agent_type == "render"
    assert decision.reason == HandoffReason.SPA_EMPTY_BODY


def test_short_but_non_spa_html_does_not_hand_off_to_render() -> None:
    """Body ngắn nhưng KHÔNG có dấu hiệu shell SPA thì không được handoff nhầm."""
    decision = decide_handoff(
        _response(text="<html><body>Short but not an SPA shell</body></html>"),
        "scout",
        consecutive_blocks=0,
        block_threshold=3,
    )
    assert decision is None


def test_repeated_403_hands_off_to_stealth_with_whole_domain() -> None:
    """Chặn liên tiếp đạt ngưỡng → handoff sang StealthAgent, và chuyển giao
    CẢ DOMAIN (không chỉ 1 URL) vì site đã chặn 1 request nhiều khả năng cũng
    chặn request tiếp theo từ cùng fingerprint."""
    decision = decide_handoff(
        _response(status_code=403), "scout", consecutive_blocks=3, block_threshold=3
    )
    assert decision is not None
    assert decision.target_agent_type == "stealth"
    assert decision.reason == HandoffReason.BLOCKED_REPEATEDLY
    assert decision.handoff_whole_domain is True


def test_403_below_threshold_does_not_hand_off_yet() -> None:
    """Chưa đạt ngưỡng chặn liên tiếp thì chưa handoff — tránh phản ứng quá
    sớm với 1 lần chặn đơn lẻ (có thể chỉ là tình cờ)."""
    decision = decide_handoff(
        _response(status_code=403), "scout", consecutive_blocks=1, block_threshold=3
    )
    assert decision is None


def test_document_agent_never_hands_off_further() -> None:
    """DocumentAgent đã là "đúng người xử lý" rồi — không handoff tiếp dù gặp lại tín hiệu PDF."""
    decision = decide_handoff(
        _response(content_type="application/pdf", body=b"%PDF-1.4"),
        "document",
        consecutive_blocks=0,
        block_threshold=3,
    )
    assert decision is None


def test_api_agent_never_hands_off_further() -> None:
    """ApiAgent tương tự — đã đúng chuyên môn thì không handoff tiếp."""
    decision = decide_handoff(
        _response(content_type="application/json", text="{}"),
        "api",
        consecutive_blocks=0,
        block_threshold=3,
    )
    assert decision is None


# --- Helper dùng Redis ------------------------------------------------------------


async def test_mark_and_check_stealth_domain(redis) -> None:
    """Domain phải được đánh dấu/tra cứu đúng — dùng để nhớ domain nào cần
    StealthAgent xử lý ở những lần crawl sau."""
    assert await is_stealth_domain(redis, "blocked.vn") is False
    await mark_domain_for_stealth(redis, "blocked.vn")
    assert await is_stealth_domain(redis, "blocked.vn") is True


async def test_record_block_increments_and_reset_clears(redis) -> None:
    """Bộ đếm chặn liên tiếp phải tăng dần rồi reset về 0 khi domain phản hồi
    bình thường trở lại — đúng ngữ nghĩa "liên tiếp", không phải tổng cộng."""
    assert await record_block(redis, "blocked.vn") == 1
    assert await record_block(redis, "blocked.vn") == 2
    await reset_block_counter(redis, "blocked.vn")
    assert await record_block(redis, "blocked.vn") == 1
