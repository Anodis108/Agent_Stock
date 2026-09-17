"""Supervisor + RewriteQuestion — nhánh hỏi-đáp (routing agent cần gọi)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.domain.entities import RoutingDecision

_MA_SYMBOL_RE = re.compile(r"(?:mã|ma)\s+([A-Za-z]{3})\b", re.IGNORECASE)
_TICKER_RE = re.compile(r"\b([A-Z]{3})\b")
_TICKER_STOPWORDS = frozenset(
    {
        "THE",
        "AND",
        "FOR",
        "ARE",
        "BUT",
        "NOT",
        "YOU",
        "ALL",
        "SAO",
        "NAY",
        "ROI",
        "THE",
        "CUA",
        "NHE",
        "VAY",
        "THE",
    }
)
_REF_PREV_RE = re.compile(
    r"(mã đó|ma do|còn mã|con ma|mã vừa|ma vua|cùng mã|cung ma)",
    re.IGNORECASE,
)
_EXPLAIN_HINTS = (
    "tại sao",
    "tai sao",
    "vì sao",
    "vi sao",
    "giải thích",
    "giai thich",
    "so sánh",
    "so sanh",
    "nguyên nhân",
    "nguyen nhan",
    "lý do",
    "ly do",
    "why",
)
_NEWS_PHRASES = (
    "tin tức",
    "tin tuc",
    "bài báo",
    "bai bao",
    "cafef",
    "news",
)
_FOLLOWUP_RE = re.compile(
    r"(giá|gia|giảm|giam|tăng|tang|thế nào|the nao|ra sao|sao rồi|sao roi)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class RewrittenQuestion:
    original: str
    rewritten: str
    symbol: str | None
    intent: str  # price_lookup | news_lookup | explain


class RewriteBrain(Protocol):
    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        ...


class SupervisorBrain(Protocol):
    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        ...


def _extract_symbol(text: str) -> str | None:
    if not text:
        return None
    ma = _MA_SYMBOL_RE.search(text)
    if ma:
        return ma.group(1).strip().upper()
    for match in _TICKER_RE.finditer(text):
        sym = match.group(1)
        if sym not in _TICKER_STOPWORDS:
            return sym
    return None


def _symbol_from_conversation(conversation: list[dict]) -> str | None:
    for turn in reversed(conversation or []):
        content = str(turn.get("content") or "")
        sym = _extract_symbol(content)
        if sym:
            return sym
    return None


def _has_news_intent(lower: str) -> bool:
    """Tránh false positive: 'thông tin' chứa 'tin' nhưng không phải hỏi tin tức."""
    cleaned = (
        lower.replace("thông tin", " ").replace("thong tin", " ")
    )
    if any(h in cleaned for h in _NEWS_PHRASES):
        return True
    return re.search(r"\btin\b", cleaned) is not None


def _needs_memory_symbol(question: str, symbol: str | None) -> bool:
    if symbol is not None:
        return False
    if _REF_PREV_RE.search(question):
        return True
    # Câu follow-up ngắn không có ticker → lấy symbol từ hội thoại
    return bool(_FOLLOWUP_RE.search(question)) and len(question.strip()) < 80


class HeuristicRewriteBrain:
    """Chuẩn hoá câu hỏi + suy ra symbol (kể cả tham chiếu 'mã đó')."""

    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        q = (question or "").strip()
        symbol = _extract_symbol(q)
        if _needs_memory_symbol(q, symbol):
            symbol = _symbol_from_conversation(conversation)

        intent = "price_lookup"
        lower = q.lower()
        if any(h in lower for h in _EXPLAIN_HINTS):
            intent = "explain"
        elif _has_news_intent(lower):
            intent = "news_lookup"

        if symbol:
            rewritten = f"[{symbol}] {q}" if symbol.upper() not in q.upper() else q
        else:
            rewritten = q
        return RewrittenQuestion(
            original=q,
            rewritten=rewritten,
            symbol=symbol,
            intent=intent,
        )


class HeuristicSupervisorBrain:
    """Routing heuristic: price-only / +news / +eval theo intent."""

    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        intent = rewritten.intent or "price_lookup"
        if intent == "explain":
            agents = ["price", "news", "eval"]
            reason = "câu hỏi cần giải thích/so sánh → price+news+eval"
        elif intent == "news_lookup":
            agents = ["price", "news"]
            reason = "câu hỏi về tin → price+news"
        else:
            agents = ["price"]
            reason = "tra cứu giá → chỉ PriceAgent"
        return RoutingDecision(
            route=intent,
            reason=reason,
            agents_to_call=agents,
        )


def rewrite_question(
    question: str,
    conversation: list[dict],
    *,
    brain: RewriteBrain | None = None,
) -> RewrittenQuestion:
    rewriter = brain or HeuristicRewriteBrain()
    try:
        return rewriter.rewrite(question, conversation)
    except Exception:  # noqa: BLE001
        return RewrittenQuestion(
            original=(question or "").strip(),
            rewritten=(question or "").strip(),
            symbol=_extract_symbol(question or ""),
            intent="price_lookup",
        )


def route_question(
    rewritten: RewrittenQuestion,
    *,
    brain: SupervisorBrain | None = None,
) -> RoutingDecision:
    supervisor = brain or HeuristicSupervisorBrain()
    try:
        return supervisor.route(rewritten)
    except Exception as exc:  # noqa: BLE001
        return RoutingDecision(
            route="price_lookup",
            reason=f"supervisor lỗi, fallback price: {exc}",
            agents_to_call=["price"],
        )
