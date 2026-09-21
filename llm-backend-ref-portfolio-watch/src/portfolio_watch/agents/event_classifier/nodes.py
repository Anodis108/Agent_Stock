"""Event classifier nodes — phân loại bình thường / bất thường từ giá + tin.

Theo agents.md đây là bước lọc rẻ. Phase 8: mặc định dùng LLM qua
Prompt Registry (`event_classification`) + `infra/llm.completion.chat`.
`HeuristicEventClassifier` giữ cho unit test / fallback inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from src.portfolio_watch.agents.event_classifier.schemas import EventClassifierBrain
from src.portfolio_watch.agents.news_agent import NewsAgentResult
from src.portfolio_watch.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import EventRoute, RoutingDecision
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

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
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


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


def _parse_llm_route(raw: str) -> RoutingDecision:
    text = (raw or "").strip()
    match = _JSON_OBJ_RE.search(text)
    payload = match.group(0) if match else text
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("LLM classifier không trả JSON object")
    route_raw = str(data.get("route", "")).strip().lower()
    reason = str(data.get("reason", "")).strip() or "llm classify"
    if "bất thường" in route_raw or route_raw in {"abnormal", "anomaly"}:
        return RoutingDecision(route=EventRoute.ABNORMAL, reason=reason)
    if "bình thường" in route_raw or route_raw in {"normal", "ok"}:
        return RoutingDecision(route=EventRoute.NORMAL, reason=reason)
    raise ValueError(f"route không hợp lệ từ LLM: {route_raw!r}")


class LlmEventClassifier:
    """LLM brain: Prompt Registry `event_classification` + chat completion."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
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
        raw = self._chat_fn(
            [{"role": "user", "content": prompt_text}],
            DETERMINISTIC,
        )
        return _parse_llm_route(raw)


# Production mặc định = LLM; unit/integration test có thể monkeypatch factory này
# sang HeuristicEventClassifier (xem tests/conftest.py).
_DEFAULT_BRAIN_FACTORY: Callable[[], EventClassifierBrain] = LlmEventClassifier


from src.portfolio_watch.infra.monitoring.tracing import agent_step

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
        with agent_step(turn, "event_classifier", "classify"):
            return classifier.classify(price, news, threshold_pct)
    except Exception as exc:  # noqa: BLE001 — lọc rẻ: lỗi → không escalate Eval
        return RoutingDecision(
            route=EventRoute.NORMAL,
            reason=f"classifier lỗi, bỏ qua escalate: {exc}",
        )
