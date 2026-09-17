"""EvalAgent — sinh Severity; ReAct có thể gọi read_price_history khi dữ liệu mập mờ.

Phase 8: mặc định dùng LLM qua Prompt Registry (`eval_severity`) +
`infra/llm.completion.chat`. `HeuristicEvalBrain` giữ cho unit test / inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import Severity, SeverityLevel
from src.portfolio_watch.domain.ports import PriceBar, PriceHistoryStore
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(slots=True)
class EvalAgentResult:
    severity: Severity
    history_calls: int = 0


class EvalAgentBrain(Protocol):
    def needs_history(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> bool:
        ...

    def build_severity(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> Severity:
        ...


class HeuristicEvalBrain:
    """Heuristic: đủ giá+|tin| → Severity ngay; thiếu/mập mờ → xin lịch sử."""

    clear_move_pct: float = 3.0

    def needs_history(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> bool:
        if history:
            return False
        if price.change_pct is None or price.error:
            return True
        # Có biến động rõ hoặc đã có tin liên quan → đủ
        if abs(price.change_pct) >= self.clear_move_pct:
            return False
        if news.items:
            return False
        return True

    def build_severity(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> Severity:
        evidence: list[str] = []
        change = price.change_pct

        if change is not None:
            evidence.append(f"change_pct={change:.2f}%")
        if price.latest_close is not None:
            evidence.append(f"latest_close={price.latest_close}")
        for item in (news.items or [])[:3]:
            evidence.append(f"news:{item.title}")

        level = SeverityLevel.LOW
        confidence = 0.55
        if change is not None:
            abs_chg = abs(change)
            if abs_chg >= 7:
                level = SeverityLevel.HIGH
                confidence = 0.9
            elif abs_chg >= 3:
                level = SeverityLevel.MEDIUM
                confidence = 0.8
            else:
                level = SeverityLevel.LOW
                confidence = 0.65
        if news.items:
            confidence = min(1.0, confidence + 0.05)
            if level == SeverityLevel.LOW:
                level = SeverityLevel.MEDIUM

        history_supports = _history_supports(change, history)
        if history:
            evidence.append(f"history_bars={len(history)}")
            if history_supports is False:
                confidence = min(confidence, 0.45)
                reasoning = (
                    "Dữ liệu ban đầu mập mờ; lịch sử giá không ủng hộ kết luận mạnh."
                )
            elif history_supports is True:
                confidence = min(1.0, max(confidence, 0.7))
                reasoning = "Đã bổ sung lịch sử giá; xu hướng khớp biến động hiện tại."
            else:
                reasoning = "Đã đọc lịch sử giá nhưng tín hiệu trung tính."
        else:
            reasoning = "Đủ tín hiệu giá/tin để đánh giá mức độ nghiêm trọng."

        if price.error:
            evidence.append(f"price_error:{price.error}")
            confidence = min(confidence, 0.4)

        # Đề xuất ngưỡng khi biến động lớn (Gate 2 downstream)
        proposed_thr: float | None = None
        if change is not None and abs(change) >= 7:
            proposed_thr = round(abs(change) * 0.5, 2)

        return Severity(
            level=level,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            proposed_threshold_pct=proposed_thr,
        )


def _history_supports(
    change_pct: float | None, history: list[PriceBar]
) -> bool | None:
    """True nếu xu hướng lịch sử cùng chiều với change; False nếu ngược; None nếu không đủ."""
    if not history or len(history) < 2 or change_pct is None:
        return None
    first = history[0].close
    last = history[-1].close
    if first == 0:
        return None
    hist_pct = (last - first) / first * 100.0
    if change_pct == 0 or hist_pct == 0:
        return None
    same_sign = (change_pct > 0 and hist_pct > 0) or (change_pct < 0 and hist_pct < 0)
    return same_sign


def _news_summary(news: NewsAgentResult) -> str:
    items = news.items or []
    if not items:
        return "(không có tin)"
    return "; ".join((i.title or "").strip() for i in items[:5] if (i.title or "").strip()) or "(không có tin)"


def _history_summary(history: list[PriceBar]) -> str:
    if not history:
        return "(chưa có lịch sử)"
    parts = []
    for bar in history[:8]:
        parts.append(f"{bar.date}:{bar.close}")
    more = f" (+{len(history) - 8} bars)" if len(history) > 8 else ""
    return "; ".join(parts) + more


def _parse_eval_payload(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    match = _JSON_OBJ_RE.search(text)
    payload = match.group(0) if match else text
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("EvalAgent LLM không trả JSON object")
    return data


def _severity_from_payload(data: dict[str, Any]) -> Severity:
    level_raw = str(data.get("level", "low")).strip().lower()
    level_map = {
        "low": SeverityLevel.LOW,
        "medium": SeverityLevel.MEDIUM,
        "med": SeverityLevel.MEDIUM,
        "high": SeverityLevel.HIGH,
    }
    level = level_map.get(level_raw, SeverityLevel.LOW)
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(data.get("reasoning", "")).strip() or "llm eval"
    evidence_raw = data.get("evidence") or []
    if isinstance(evidence_raw, list):
        evidence = [str(x) for x in evidence_raw]
    else:
        evidence = [str(evidence_raw)]

    proposed_thr = data.get("proposed_threshold_pct")
    if proposed_thr is not None:
        try:
            proposed_thr = float(proposed_thr)
        except (TypeError, ValueError):
            proposed_thr = None

    related = data.get("proposed_related_symbols") or []
    if not isinstance(related, list):
        related = []
    related_syms = [str(s).strip().upper() for s in related if str(s).strip()]

    return Severity(
        level=level,
        confidence=confidence,
        reasoning=reasoning,
        evidence=evidence,
        proposed_threshold_pct=proposed_thr,
        proposed_related_symbols=related_syms,
    )


class LlmEvalBrain:
    """LLM brain: Prompt Registry `eval_severity` + chat completion."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
        self._prompt_version = prompt_version
        # Cache kết quả lần gọi khi chưa có history (tránh double-call nếu đủ data)
        self._cached_empty_history: dict[str, Any] | None = None

    def _call_llm(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> dict[str, Any]:
        change = price.change_pct
        prompt_text = registry().render(
            "eval_severity",
            version=self._prompt_version,
            symbol=price.symbol or news.symbol or "",
            change_pct=f"{change:.4f}" if change is not None else "N/A",
            news_summary=_news_summary(news),
            history_summary=_history_summary(history),
        )
        raw = self._chat_fn(
            [{"role": "user", "content": prompt_text}],
            DETERMINISTIC,
        )
        return _parse_eval_payload(raw)

    def needs_history(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> bool:
        if history:
            return False
        data = self._call_llm(price, news, history)
        self._cached_empty_history = data
        return bool(data.get("needs_history"))

    def build_severity(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
    ) -> Severity:
        if history:
            data = self._call_llm(price, news, history)
        elif self._cached_empty_history is not None and not self._cached_empty_history.get(
            "needs_history"
        ):
            data = self._cached_empty_history
        else:
            data = self._call_llm(price, news, history)
        return _severity_from_payload(data)


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_EVAL_BRAIN_FACTORY: Callable[[], EvalAgentBrain] = LlmEvalBrain


def run_eval_agent(
    price: PriceAgentResult,
    news: NewsAgentResult,
    history_store: PriceHistoryStore,
    *,
    brain: EvalAgentBrain | None = None,
    history_days: int = 30,
) -> EvalAgentResult:
    evaluator = brain or _DEFAULT_EVAL_BRAIN_FACTORY()
    history: list[PriceBar] = []
    history_calls = 0
    symbol = (price.symbol or news.symbol or "").strip()

    if not symbol:
        return EvalAgentResult(
            severity=Severity(
                level=SeverityLevel.LOW,
                confidence=0.2,
                reasoning="symbol rỗng",
                evidence=[],
            ),
            history_calls=0,
        )

    try:
        requested = evaluator.needs_history(price, news, history)
        if requested:
            history_calls += 1
            try:
                history = list(
                    history_store.read_history(symbol, days=history_days) or []
                )
            except Exception as exc:  # noqa: BLE001
                severity = evaluator.build_severity(price, news, [])
                return EvalAgentResult(
                    severity=severity.model_copy(
                        update={
                            "confidence": min(severity.confidence, 0.35),
                            "reasoning": (
                                f"{severity.reasoning} Lỗi đọc lịch sử giá: {exc}"
                            ),
                            "evidence": [
                                *severity.evidence,
                                f"history_error:{exc}",
                            ],
                        }
                    ),
                    history_calls=history_calls,
                )

        severity = evaluator.build_severity(price, news, history)
        if requested and not history:
            severity = severity.model_copy(
                update={
                    "confidence": min(severity.confidence, 0.4),
                    "reasoning": (
                        f"{severity.reasoning} Không lấy được lịch sử giá bổ sung."
                    ),
                }
            )
        return EvalAgentResult(severity=severity, history_calls=history_calls)
    except Exception as exc:  # noqa: BLE001
        return EvalAgentResult(
            severity=Severity(
                level=SeverityLevel.LOW,
                confidence=0.2,
                reasoning=f"eval lỗi: {exc}",
                evidence=[],
            ),
            history_calls=history_calls,
        )
