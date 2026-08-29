"""Định tuyến SAU KHI FETCH — nhánh nét liền màu cam trong Sơ đồ 1.

Đây là điều làm swarm THẬT SỰ dị chủng (heterogeneous), khác một partitioned
worker pool chỉ gồm các bản sao giống hệt nhau: mỗi agent, sau khi tự tay fetch
xong 1 trang, có thể ĐỔI Ý về việc ai nên xử lý nó — dựa trên bằng chứng thật
(status code, Content-Type, hình dạng body), không chỉ dựa trên việc mình có sở
hữu domain đó hay không.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from redis.asyncio import Redis

from vn_stock_swarm.fetcher import RawResponse

STEALTH_DOMAINS_KEY = "stealth:domains"

# Các mảnh Content-Type mà bước đoán trước-fetch không có cách nào biết trước
# — chỉ lộ ra khi đã có response ở tầng byte trong tay, đây là lý do kiểm tra
# này chạy SAU fetch_page(), khác với pre_route.guess_agent_type.
_PDF_CONTENT_TYPES = ("application/pdf",)
_JSON_CONTENT_HINTS = ("json",)

# 1 body gần như rỗng dù đã render là dấu hiệu điển hình của shell SPA cần
# trình duyệt thật (RenderAgent) thay vì 1 lần GET thuần.
_SPA_TEXT_LENGTH_THRESHOLD = 200
_SPA_SHELL_MARKERS = ('id="root"', 'id="app"', "id='root'", "id='app'")


class HandoffReason(str, Enum):
    CONTENT_TYPE_MISMATCH_PDF = "content_type_mismatch_pdf"
    CONTENT_TYPE_MISMATCH_JSON = "content_type_mismatch_json"
    SPA_EMPTY_BODY = "spa_empty_body"
    BLOCKED_REPEATEDLY = "blocked_repeatedly"


@dataclass(frozen=True)
class HandoffDecision:
    target_agent_type: str
    reason: HandoffReason
    handoff_whole_domain: bool = False


def _looks_like_spa_shell(response: RawResponse) -> bool:
    if "html" not in response.content_type:
        return False
    visible_text_len = len(response.text.strip())
    if visible_text_len >= _SPA_TEXT_LENGTH_THRESHOLD:
        return False
    return any(marker in response.text for marker in _SPA_SHELL_MARKERS)


def decide_handoff(
    response: RawResponse | None,
    source_agent_type: str,
    consecutive_blocks: int,
    block_threshold: int,
) -> HandoffDecision | None:
    """Quyết định ``source_agent_type`` có nên chuyển giao URL này cho 1 agent
    chuyên biệt hơn hay không, dựa trên tín hiệu thật sau-fetch (nét liền cam
    trong Sơ đồ 1) chứ không phải phỏng đoán hình dạng URL của pre_route.py.

    Trả về None nghĩa là agent đang fetch cứ tự xử lý response luôn. Trên
    thực tế chỉ ScoutAgent mới hay handoff theo tín hiệu content-type/SPA (nó
    là cửa vào mặc định mà mọi loại khác đều "rơi qua"), nhưng hàm này không
    biết/không quan tâm loại agent cụ thể nào gọi nó, nên bất kỳ agent nào
    cũng gọi được.
    """
    if response is None:
        return None  # lỗi tầng transport — không phải tín hiệu nội dung, không có gì để handoff

    if response.status_code in (403, 429) and consecutive_blocks >= block_threshold:
        return HandoffDecision(
            target_agent_type="stealth",
            reason=HandoffReason.BLOCKED_REPEATEDLY,
            handoff_whole_domain=True,
        )

    if source_agent_type == "document" or source_agent_type == "api":
        return None  # đã đúng người xử lý rồi, không handoff tiếp nữa

    if response.content_type in _PDF_CONTENT_TYPES or response.body[:5] == b"%PDF-":
        if source_agent_type != "document":
            return HandoffDecision(
                target_agent_type="document", reason=HandoffReason.CONTENT_TYPE_MISMATCH_PDF
            )

    if any(hint in response.content_type for hint in _JSON_CONTENT_HINTS):
        if source_agent_type != "api":
            return HandoffDecision(
                target_agent_type="api", reason=HandoffReason.CONTENT_TYPE_MISMATCH_JSON
            )

    if source_agent_type in ("scout", "stealth") and _looks_like_spa_shell(response):
        return HandoffDecision(target_agent_type="render", reason=HandoffReason.SPA_EMPTY_BODY)

    return None


async def mark_domain_for_stealth(redis: Redis, domain: str) -> None:
    await redis.sadd(STEALTH_DOMAINS_KEY, domain)  # type: ignore[misc]


async def is_stealth_domain(redis: Redis, domain: str) -> bool:
    return bool(await redis.sismember(STEALTH_DOMAINS_KEY, domain))  # type: ignore[misc]


def block_counter_key(domain: str) -> str:
    return f"blocks:{domain}"


async def record_block(redis: Redis, domain: str, ttl_seconds: int = 300) -> int:
    """Tăng bộ đếm "chặn liên tiếp" của ``domain`` và trả về giá trị mới.

    Dùng TTL thay vì bộ đếm thuần để 1 chuỗi bị chặn từ nhiều giờ trước không
    còn tính vào "liên tiếp" nếu domain đó gần đây đã phản hồi bình thường trở lại.
    """
    key = block_counter_key(domain)
    count = await redis.incr(key)
    await redis.expire(key, ttl_seconds)
    return int(count)


async def reset_block_counter(redis: Redis, domain: str) -> None:
    await redis.delete(block_counter_key(domain))
