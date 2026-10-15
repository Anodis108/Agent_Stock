"""Greeting Fast-Path — Nhận diện câu chào hỏi và phản hồi tức thì (TTFT < 1s).

Mục tiêu:
1. Phản hồi tức thì cho các câu chào hỏi giao tiếp thông thường (xin chào, hello, hi, bạn là ai...).
2. Bỏ qua toàn bộ các worker LLM / Price / News, tiết kiệm chi phí và đạt TTFT < 1s.
3. Phân biệt chính xác giữa:
   - Câu chào hỏi thuần túy (Pure Greeting) -> Fast-path tức thì.
   - Câu chào hỏi kèm ý định tra cứu cổ phiếu ("Chào bạn, giá FPT bao nhiêu?") -> Chuyển về pipeline phân tích.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Các mẫu từ khóa chào hỏi và giao tiếp mở đầu
_GREETING_PATTERNS = (
    "xin chào", "xin chao",
    "chào bạn", "chao ban",
    "chào bot", "chao bot",
    "chào em", "chao em",
    "chào anh", "chao anh",
    "chào chị", "chao chi",
    "chào trợ lý", "chao tro ly",
    "chào buổi sáng", "chao buoi sang",
    "chào buổi chiều", "chao buoi chieu",
    "chào buổi tối", "chao buoi toi",
    "chào ngày mới", "chao ngay moi",
    "bạn là ai", "ban la ai",
    "bạn có thể làm gì", "ban co the lam gi",
    "bạn có thể giúp gì", "ban co the giup gi",
    "bạn giúp được gì", "ban giup duoc gi",
    "trợ lý có tính năng gì", "tro ly co tinh nang gi",
    "bạn có tính năng gì", "ban co tinh nang gi",
    "hướng dẫn sử dụng", "huong dan su dung",
    "giới thiệu bản thân", "gioi thieu ban than",
    "giới thiệu về bạn", "gioi thieu ve ban",
    "hello", "hi bot", "hey bot", "good morning", "good afternoon",
)

_GREETING_REGEXES = (
    re.compile(r"^(?:xin\s+)?chào(?:\s+(?:bạn|bot|em|anh|chị|trợ\s*lý|mọi\s*người))?[\s!\?\.]*$", re.IGNORECASE),
    re.compile(r"^(?:hello|hi|hey|halo|alo)[\s!\?\.]*$", re.IGNORECASE),
    re.compile(r"^(?:bạn\s+là\s+ai|ban\s+la\s+ai)[\s!\?\.]*$", re.IGNORECASE),
    re.compile(r"^(?:bạn|ban)\s+(?:có\s+thể|co\s+the|giúp\s+được|giup\s+duoc)\s+(?:làm|lam|giúp|giup)\s+(?:gì|gi)(?:\s+(?:cho\s+tôi|cho\s+toi))?[\s!\?\.]*$", re.IGNORECASE),
    re.compile(r"^(?:trợ\s*lý|tro\s*ly|bạn|ban)\s+(?:có|co)\s+(?:tính\s*năng|tinh\s*nang|chức\s*năng|chuc\s*nang)\s+(?:gì|gi)[\s!\?\.]*$", re.IGNORECASE),
)

_TICKER_PATTERN = re.compile(r"\b([A-Z]{3,5})\b")
_STOCK_INTENT_KEYWORDS = (
    "giá", "gia", "thị giá", "thi gia", "tin tức", "tin tuc",
    "chỉ báo", "chi bao", "biểu đồ", "bieu do", "danh mục", "danh muc",
    "lãi lỗ", "lai lo", "so sánh", "so sanh", "cổ phiếu", "co phieu",
    "thị trường", "thi truong", "mua", "bán", "ban",
)

DEFAULT_GREETING_RESPONSE = (
    "Xin chào! Tôi là trợ lý chứng khoán VN Stock Swarm. "
    "Tôi có thể hỗ trợ bạn tra cứu thị giá, tin tức doanh nghiệp, chỉ báo kỹ thuật RSI/SMA, "
    "vẽ biểu đồ nến và theo dõi danh mục đầu tư đa tài khoản."
)


@dataclass(slots=True)
class FastpathGreetingResult:
    """Kết quả xử lý greeting fast-path."""
    is_greeting: bool
    is_pure_greeting: bool
    answer: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)


def is_greeting(text: str) -> bool:
    """Kiểm tra câu hỏi có chứa cụm từ chào hỏi hay không."""
    raw = (text or "").strip()
    if not raw:
        return False
    lowered = raw.lower()
    return any(p in lowered for p in _GREETING_PATTERNS) or any(rgx.search(raw) for rgx in _GREETING_REGEXES)


def is_pure_greeting(text: str) -> bool:
    """Kiểm tra câu hỏi có phải là câu chào hỏi thuần túy (không kèm hỏi mã chứng khoán)."""
    raw = (text or "").strip()
    if not is_greeting(raw):
        return False
    lowered = raw.lower()
    has_ticker = bool(_TICKER_PATTERN.findall(raw))
    has_intent = any(k in lowered for k in _STOCK_INTENT_KEYWORDS)
    return not (has_ticker and has_intent)


def get_greeting_fastpath_answer() -> str:
    """Trả về câu phản hồi chào hỏi mặc định tức thì."""
    return DEFAULT_GREETING_RESPONSE


class GreetingFastpath:
    """Fast-path engine cho câu hỏi giao tiếp mở đầu."""

    @staticmethod
    def evaluate(question: str) -> FastpathGreetingResult:
        """Đánh giá câu hỏi và trả về kết quả FastpathGreetingResult."""
        raw = (question or "").strip()
        matched = is_greeting(raw)
        pure = is_pure_greeting(raw) if matched else False

        if pure:
            steps = [
                {"id": "1", "name": "greeting_fastpath", "status": "done", "detail": "Fast-path greeting triggered (TTFT < 1s)"},
                {"id": "2", "name": "answer_composer", "status": "done", "detail": "Default greeting response returned"},
            ]
            return FastpathGreetingResult(
                is_greeting=True,
                is_pure_greeting=True,
                answer=get_greeting_fastpath_answer(),
                steps=steps,
            )

        return FastpathGreetingResult(
            is_greeting=matched,
            is_pure_greeting=False,
            answer=None,
            steps=[],
        )

    @staticmethod
    def is_greeting(text: str) -> bool:
        return is_greeting(text)

    @staticmethod
    def is_pure_greeting(text: str) -> bool:
        return is_pure_greeting(text)
