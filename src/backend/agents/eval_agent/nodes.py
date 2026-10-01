"""EvalAgent — sinh Severity; ReAct có thể gọi read_price_history khi dữ liệu mập mờ.

Phase 6+: mặc định dùng LLM qua Prompt Registry (`eval_severity`) +
structured output. `HeuristicEvalBrain` giữ cho unit test / inject.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from backend.agents.eval_agent.schemas import EvalSeverityOutput
from backend.agents.eval_agent.tools import read_price_history
from backend.agents.news_agent import NewsAgentResult
from backend.agents.price_agent import PriceAgentResult
from backend.domain.entities import Severity, SeverityLevel
from backend.domain.indicators import (
    IndicatorSummary,
    analyze_technical_indicators,
)
from backend.domain.ports import PriceBar, PriceHistoryStore
from backend.infra.llm.params import DETERMINISTIC
from backend.infra.llm.prompt_registry import registry
from backend.infra.llm.structured import call_llm_structured


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
        indicators: IndicatorSummary | None = None,
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
        indicators: IndicatorSummary | None = None,
    ) -> Severity:
        evidence: list[str] = []
        change = price.change_pct

        if change is not None:
            evidence.append(f"change_pct={change:.2f}%")
        if price.latest_close is not None:
            evidence.append(f"latest_close={price.latest_close}")
        for item in (news.items or [])[:3]:
            evidence.append(f"news:{item.title}")

        if indicators is not None:
            if indicators.rsi is not None:
                evidence.append(f"rsi={indicators.rsi}")
            if indicators.sma_20 is not None:
                evidence.append(f"sma20={indicators.sma_20}")
            if indicators.sma_50 is not None:
                evidence.append(f"sma50={indicators.sma_50}")
            if indicators.ma_cross != "none":
                evidence.append(f"ma_cross:{indicators.ma_cross}")

        # Phase 3c: không so sánh % khi thiếu evidence giá
        if change is None or price.error:
            if price.error:
                evidence.append(f"price_error:{price.error}")
            else:
                evidence.append("price_evidence:missing_change_pct")
            return Severity(
                level=SeverityLevel.LOW,
                confidence=0.3,
                reasoning=(
                    "Thiếu evidence giá (% thay đổi) — không so sánh biến động "
                    "cho đến khi có giá phiên hiện tại và phiên trước."
                ),
                evidence=evidence,
                proposed_threshold_pct=None,
            )

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
            elif abs_chg < 0.5 and not news.items:
                level = SeverityLevel.NONE
                confidence = 0.7
            else:
                level = SeverityLevel.LOW
                confidence = 0.65
        if news.items:
            confidence = min(1.0, confidence + 0.05)
            if level in (SeverityLevel.NONE, SeverityLevel.LOW):
                level = SeverityLevel.MEDIUM

        # Nâng cao đánh giá rủi ro định lượng qua chỉ báo kỹ thuật (Phase 3)
        tech_note = ""
        if indicators is not None:
            if indicators.rsi is not None:
                if indicators.rsi >= 70.0:
                    tech_note += f" Cảnh báo: RSI={indicators.rsi:.1f} vùng quá mua (rủi ro điều chỉnh kỹ thuật)."
                    if change is not None and change >= 3.0:
                        level = SeverityLevel.HIGH
                        confidence = min(1.0, confidence + 0.1)
                    elif level in (SeverityLevel.NONE, SeverityLevel.LOW):
                        level = SeverityLevel.MEDIUM
                elif indicators.rsi <= 30.0:
                    tech_note += f" Cảnh báo: RSI={indicators.rsi:.1f} vùng quá bán (xuất hiện áp lực bán tháo/quá đà)."
                    if level in (SeverityLevel.NONE, SeverityLevel.LOW):
                        level = SeverityLevel.MEDIUM
            if indicators.ma_cross == "golden_cross":
                tech_note += " Xuất hiện tín hiệu Golden Cross (SMA20 cắt lên SMA50)."
            elif indicators.ma_cross == "death_cross":
                tech_note += " Xuất hiện tín hiệu Death Cross (SMA20 cắt xuống SMA50)."
                if level != SeverityLevel.HIGH:
                    level = SeverityLevel.MEDIUM

        history_supports = _history_supports(change, history)
        if level == SeverityLevel.NONE and not tech_note:
            reasoning = "Giá cổ phiếu biến động không đáng kể và không có tin tức hay rủi ro bất thường."
        elif history:
            evidence.append(f"history_bars={len(history)}")
            if history_supports is False:
                confidence = min(confidence, 0.45)
                reasoning = (
                    "Dữ liệu ban đầu mập mờ; lịch sử giá không ủng hộ kết luận mạnh." + tech_note
                )
            elif history_supports is True:
                confidence = min(1.0, max(confidence, 0.7))
                reasoning = "Đã bổ sung lịch sử giá; xu hướng khớp biến động hiện tại." + tech_note
            else:
                reasoning = "Đã đọc lịch sử giá nhưng tín hiệu trung tính." + tech_note
        else:
            reasoning = "Đủ tín hiệu giá/tin để đánh giá mức độ nghiêm trọng." + tech_note

        # Đề xuất ngưỡng khi biến động lớn (Gate 2 downstream)
        proposed_thr: float | None = None
        if change is not None and abs(change) >= 7:
            proposed_thr = round(abs(change) * 0.5, 2)

        return Severity(
            level=level,
            confidence=confidence,
            reasoning=reasoning.strip(),
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


class LlmEvalBrain:
    """LLM brain: Prompt Registry `eval_severity` + structured output."""

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
        # Cache kết quả lần gọi khi chưa có history (tránh double-call nếu đủ data)
        self._cached_empty_history: EvalSeverityOutput | None = None

    def _call_llm(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
        indicators: IndicatorSummary | None = None,
    ) -> EvalSeverityOutput:
        change = price.change_pct
        tech_summary = (
            indicators.format_summary()
            if indicators is not None
            else "(chưa có chỉ báo kỹ thuật)"
        )
        prompt_text = registry().render(
            "eval_severity",
            version=self._prompt_version,
            symbol=price.symbol or news.symbol or "",
            change_pct=f"{change:.4f}" if change is not None else "N/A",
            news_summary=_news_summary(news),
            history_summary=_history_summary(history),
            technical_summary=tech_summary,
        )
        messages = [{"role": "user", "content": prompt_text}]
        try:
            return call_llm_structured(
                messages,
                EvalSeverityOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
        except Exception:
            # inner schema fallback: heuristic
            heur = HeuristicEvalBrain()
            sev = heur.build_severity(price, news, history, indicators=indicators)
            return EvalSeverityOutput(
                needs_history=heur.needs_history(price, news, history),
                level=sev.level.value,
                confidence=sev.confidence,
                reasoning=sev.reasoning,
                evidence=sev.evidence,
                proposed_threshold_pct=sev.proposed_threshold_pct,
                proposed_related_symbols=sev.proposed_related_symbols,
            )

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
        return bool(data.needs_history)

    def build_severity(
        self,
        price: PriceAgentResult,
        news: NewsAgentResult,
        history: list[PriceBar],
        indicators: IndicatorSummary | None = None,
    ) -> Severity:
        if history:
            data = self._call_llm(price, news, history, indicators=indicators)
        elif self._cached_empty_history is not None and not self._cached_empty_history.needs_history:
            data = self._cached_empty_history
        else:
            data = self._call_llm(price, news, history, indicators=indicators)
        return data.to_severity()


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_EVAL_BRAIN_FACTORY: Callable[[], EvalAgentBrain] = LlmEvalBrain


from backend.infra.monitoring.tracing import agent_step

def run_eval_agent(
    price: PriceAgentResult,
    news: NewsAgentResult,
    history_store: PriceHistoryStore,
    *,
    brain: EvalAgentBrain | None = None,
    history_days: int = 30,
    turn: str = "",
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
                with agent_step(
                    turn,
                    "eval_agent",
                    "read_price_history",
                    input={"symbol": symbol, "days": history_days},
                ) as box:
                    history = read_price_history(history_store, symbol, days=history_days)
                    box["output"] = {"records": len(history)}
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

        closes = [b.close for b in history if getattr(b, "close", None) is not None]
        indicators = analyze_technical_indicators(closes) if closes else None

        with agent_step(
            turn,
            "eval_agent",
            "build_severity",
            input={"symbol": symbol, "has_history": bool(history)},
        ) as box:
            severity = evaluator.build_severity(price, news, history, indicators=indicators)
            box["output"] = {
                "level": str(getattr(severity.level, "value", severity.level)),
                "confidence": severity.confidence,
            }
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
