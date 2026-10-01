"""Event classifier nodes — phân loại bình thường / bất thường từ giá + tin.

Theo agents.md đây là bước lọc rẻ. Phase 6+: mặc định dùng LLM qua
Prompt Registry (`event_classification`) + structured output.
`HeuristicEventClassifier` giữ cho unit test / fallback inject.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.agents.event_classifier.schemas import (
    ClassifierOutput,
    EventClassifierBrain,
)
from backend.agents.news_agent import NewsAgentResult
from backend.agents.price_agent import PriceAgentResult
from backend.domain.entities import EventRoute, RoutingDecision
from backend.infra.llm.params import DETERMINISTIC
from backend.infra.llm.prompt_registry import registry
from backend.infra.llm.structured import call_llm_structured

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


def _news_titles_blob(news: NewsAgentResult) -> str:
    items = news.items or []
    if not items:
        return "(không có tin)"
    parts = []
    for item in items[:10]:
        title = (item.title or "").strip()
        snippet = (item.snippet or "").strip()
        parts.append(f"{title} — {snippet}" if snippet else title)
    return "; ".join(p for p in parts if p) or "(không có tin)"


class LlmEventClassifier:
    """LLM brain: Prompt Registry `event_classification` + structured output."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        chat_parsed_fn: Callable[..., Any] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn
        self._chat_parsed_fn = chat_parsed_fn
        self._prompt_version = prompt_version

    def classify(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        threshold_pct: float,
    ) -> RoutingDecision:
        thr = threshold_pct if threshold_pct > 0 else 3.0
        change = price.change_pct
        prompt_text = registry().render(
            "event_classification",
            version=self._prompt_version,
            symbol=price.symbol or "",
            latest_close=(
                f"{price.latest_close}" if price.latest_close is not None else "N/A"
            ),
            change_pct=f"{change:.4f}" if change is not None else "N/A",
            threshold_pct=f"{thr}",
            news_titles=_news_titles_blob(news),
        )
        messages = [{"role": "user", "content": prompt_text}]
        try:
            output = call_llm_structured(
                messages,
                ClassifierOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
            return output.to_routing_decision()
        except Exception:
            # inner schema guard: fallback to heuristic classifier safely
            return HeuristicEventClassifier().classify(price, news, threshold_pct)


# Production mặc định = LLM; unit/integration test có thể monkeypatch factory này
# sang HeuristicEventClassifier (xem tests/conftest.py).
_DEFAULT_BRAIN_FACTORY: Callable[[], EventClassifierBrain] = LlmEventClassifier


from backend.infra.monitoring.tracing import agent_step

def classify_event(
    price: PriceAgentResult,
    news: NewsAgentResult,
    *,
    threshold_pct: float = 3.0,
    brain: EventClassifierBrain | None = None,
    turn: str = "",
) -> RoutingDecision:
    classifier = brain or _DEFAULT_BRAIN_FACTORY()
    try:
        with agent_step(
            turn,
            "event_classifier",
            "classify",
            input={
                "symbol": price.symbol,
                "change_pct": price.change_pct,
                "threshold_pct": threshold_pct,
            },
        ) as box:
            decision = classifier.classify(price, news, threshold_pct)
            box["output"] = {
                "route": str(getattr(decision.route, "value", decision.route)),
                "reason": decision.reason,
            }
            return decision
    except Exception as exc:  # noqa: BLE001 — lọc rẻ: lỗi → không escalate Eval
        return RoutingDecision(
            route=EventRoute.NORMAL,
            reason=f"classifier lỗi, bỏ qua escalate: {exc}",
        )
