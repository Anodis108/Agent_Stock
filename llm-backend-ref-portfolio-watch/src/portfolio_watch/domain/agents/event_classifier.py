"""Event Classifier — phân loại bình thường / bất thường từ giá + tin.

Theo agents.md đây là bước lọc rẻ; LLM có thể inject qua `EventClassifierBrain`.
Heuristic mặc định đủ cho unit test / MVP filter.
"""

from __future__ import annotations

from typing import Protocol

from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import EventRoute, RoutingDecision

# Tránh hint quá ngắn/mơ hồ (vd. "âm" khớp trong "đảm bảo")
_NEGATIVE_HINTS = (
    "giảm mạnh",
    "giảm sâu",
    "sụt giảm",
    "sụt",
    "lao dốc",
    "bán tháo",
    "thua lỗ",
    "báo lỗ",
    "bị phạt",
    "phạt hành chính",
    "điều tra",
    "khủng hoảng",
    "cắt lỗ",
    "delist",
    "scandal",
    "fraud",
    "plunge",
    "crash",
    "bị kiện",
    "lỗ quý",
    "giảm",
    "phạt",
    "lỗ",
)

_NEGATION_PREFIXES = ("không ", "chưa ", "chẳng ")


def _blob_has_negative(blob: str, hints: tuple[str, ...]) -> bool:
    text = blob.lower()
    # Ưu tiên hint dài hơn trước để khớp cụ thể hơn
    ordered = sorted(hints, key=len, reverse=True)
    for hint in ordered:
        start = 0
        while True:
            i = text.find(hint, start)
            if i < 0:
                break
            prefix = text[max(0, i - 8) : i]
            if any(prefix.endswith(p) for p in _NEGATION_PREFIXES):
                start = i + 1
                continue
            return True
    return False


class EventClassifierBrain(Protocol):
    def classify(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        threshold_pct: float,
    ) -> RoutingDecision:
        ...


class HeuristicEventClassifier:
    """Rule-based: |%| vượt ngưỡng HOẶC tin tiêu cực rõ → bất thường."""

    negative_hints: tuple[str, ...] = _NEGATIVE_HINTS

    def classify(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        threshold_pct: float,
    ) -> RoutingDecision:
        reasons: list[str] = []
        thr = threshold_pct if threshold_pct > 0 else 3.0

        change = price.change_pct
        if change is not None and abs(change) >= thr:
            reasons.append(
                f"|change_pct|={abs(change):.2f}% >= ngưỡng {thr}%"
            )

        neg_titles: list[str] = []
        for item in news.items or []:
            blob = f"{item.title} {item.snippet}"
            if _blob_has_negative(blob, self.negative_hints):
                neg_titles.append(item.title)
        if neg_titles:
            reasons.append("tin tiêu cực: " + "; ".join(neg_titles[:3]))

        if reasons:
            return RoutingDecision(
                route=EventRoute.ABNORMAL,
                reason="; ".join(reasons),
            )
        return RoutingDecision(
            route=EventRoute.NORMAL,
            reason="biến động nhỏ và không có tin bất thường rõ",
        )


def classify_event(
    price: PriceAgentResult,
    news: NewsAgentResult,
    *,
    threshold_pct: float = 3.0,
    brain: EventClassifierBrain | None = None,
) -> RoutingDecision:
    classifier = brain or HeuristicEventClassifier()
    try:
        return classifier.classify(price, news, threshold_pct)
    except Exception as exc:  # noqa: BLE001 — lọc rẻ: lỗi → không escalate Eval
        return RoutingDecision(
            route=EventRoute.NORMAL,
            reason=f"classifier lỗi, bỏ qua escalate: {exc}",
        )
