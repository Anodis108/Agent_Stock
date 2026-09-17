"""EvalAgent — sinh Severity; ReAct có thể gọi read_price_history khi dữ liệu mập mờ."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import Severity, SeverityLevel
from src.portfolio_watch.domain.ports import PriceBar, PriceHistoryStore


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


def run_eval_agent(
    price: PriceAgentResult,
    news: NewsAgentResult,
    history_store: PriceHistoryStore,
    *,
    brain: EvalAgentBrain | None = None,
    history_days: int = 30,
) -> EvalAgentResult:
    evaluator = brain or HeuristicEvalBrain()
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
