"""AnswerComposer — soạn câu trả lời hỏi-đáp + guardrail (không HITL)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.domain.agents.eval_agent import EvalAgentResult
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import SeverityLevel
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from src.portfolio_watch.domain.ports import MemoryStore

MODEL_LIGHT = "gpt-4o-mini"
MODEL_HEAVY = "gpt-4o"
MAX_DRAFT_ATTEMPTS = 3


def select_answer_model(eval_result: EvalAgentResult | None) -> str:
    if eval_result is None:
        return MODEL_LIGHT
    sev = eval_result.severity
    if sev.level == SeverityLevel.HIGH or sev.confidence >= 0.85:
        return MODEL_HEAVY
    return MODEL_LIGHT


class AnswerDraftBrain(Protocol):
    def compose(
        self,
        *,
        question: str,
        symbol: str | None,
        price: PriceAgentResult | None,
        news: NewsAgentResult | None,
        eval_result: EvalAgentResult | None,
        evidence: list[str],
        model: str,
        attempt: int,
        previous_violations: list[str],
    ) -> str:
        ...


@dataclass
class HeuristicAnswerDraftBrain:
    """Composer không LLM — chỉ dùng số liệu/tin có trong evidence."""

    def compose(
        self,
        *,
        question: str,
        symbol: str | None,
        price: PriceAgentResult | None,
        news: NewsAgentResult | None,
        eval_result: EvalAgentResult | None,
        evidence: list[str],
        model: str,
        attempt: int,
        previous_violations: list[str],
    ) -> str:
        sym = symbol or (price.symbol if price else None) or "N/A"
        parts = [f"Trả lời về {sym}:"]
        if price and price.change_pct is not None and price.latest_close is not None:
            parts.append(
                f"Giá đóng cửa {price.latest_close}, thay đổi {price.change_pct:.2f}%."
            )
        elif price and price.error:
            parts.append(f"Không lấy được giá: {price.error}.")
        if news and news.items:
            titles = "; ".join(i.title for i in news.items[:3])
            parts.append(f"Tin liên quan: {titles}.")
        if eval_result is not None:
            sev = eval_result.severity
            parts.append(
                f"Đánh giá: {sev.reasoning} "
                f"(mức {sev.level.value})."
            )
        if not evidence:
            parts.append("Chưa có đủ dữ liệu để kết luận chi tiết.")
        parts.append("Thông tin tham khảo, không phải lời khuyên đầu tư.")
        if attempt > 0 and previous_violations:
            parts.append(
                "Đã chỉnh lại để loại khuyến nghị mua/bán và số không có trong evidence."
            )
        return " ".join(parts)


@dataclass(slots=True)
class AnswerComposeResult:
    answer: str
    model: str
    draft_attempts: int
    guardrail_violations: list[str]
    evidence: list[str]
    hitl_used: bool = False  # nhánh hỏi-đáp không qua HITL


def build_evidence(
    price: PriceAgentResult | None,
    news: NewsAgentResult | None,
    eval_result: EvalAgentResult | None,
) -> list[str]:
    evidence: list[str] = []
    if price is not None:
        if price.change_pct is not None:
            evidence.append(f"change_pct={price.change_pct:.2f}%")
        if price.latest_close is not None:
            evidence.append(f"latest_close={price.latest_close}")
        if price.prev_close is not None:
            evidence.append(f"prev_close={price.prev_close}")
        if price.error:
            evidence.append(f"price_error:{price.error}")
    if news is not None:
        for item in (news.items or [])[:5]:
            evidence.append(f"news:{item.title}")
    if eval_result is not None:
        # Chỉ lấy evidence thật của Eval — không đưa reasoning vào blob
        # (tránh whitelist số bịa / lời khuyên nằm trong reasoning).
        evidence.extend(eval_result.severity.evidence)
        evidence.append(f"level:{eval_result.severity.level.value}")
    # dedupe giữ thứ tự
    seen: set[str] = set()
    out: list[str] = []
    for e in evidence:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def run_answer_composer(
    *,
    question: str,
    symbol: str | None,
    price: PriceAgentResult | None,
    news: NewsAgentResult | None,
    eval_result: EvalAgentResult | None,
    memory_store: MemoryStore | None = None,
    user_id: str = "default",
    brain: AnswerDraftBrain | None = None,
    max_attempts: int = MAX_DRAFT_ATTEMPTS,
) -> AnswerComposeResult:
    """Soạn câu trả lời + vòng rewrite khi guardrail fail. Không tạo HITL."""
    _ = memory_store, user_id  # preferences có thể dùng sau; MVP heuristic không cần
    evidence = build_evidence(price, news, eval_result)
    model = select_answer_model(eval_result)
    draft_brain = brain or HeuristicAnswerDraftBrain()
    violations: list[str] = []
    answer = ""
    attempts = 0

    for attempt in range(max(max_attempts, 1)):
        attempts = attempt + 1
        try:
            answer = draft_brain.compose(
                question=question,
                symbol=symbol,
                price=price,
                news=news,
                eval_result=eval_result,
                evidence=evidence,
                model=model,
                attempt=attempt,
                previous_violations=list(violations),
            )
        except Exception as exc:  # noqa: BLE001
            answer = (
                f"Không soạn được câu trả lời ({exc}). "
                f"Evidence: {'; '.join(evidence) if evidence else 'không có'}."
            )
        check = check_output("", answer, evidence)
        if check.ok:
            return AnswerComposeResult(
                answer=answer,
                model=model,
                draft_attempts=attempts,
                guardrail_violations=[],
                evidence=evidence,
                hitl_used=False,
            )
        violations = list(check.violations)

    # Fallback: chỉ nêu evidence, tránh lời khuyên
    safe = (
        "Tóm tắt dữ liệu: "
        + ("; ".join(evidence) if evidence else "không có evidence.")
        + " Thông tin tham khảo, không phải lời khuyên đầu tư."
    )
    final_check = check_output("", safe, evidence)
    if not final_check.ok:
        safe = "Không thể trả lời an toàn với evidence hiện có."
        final_check = check_output("", safe, evidence)
    return AnswerComposeResult(
        answer=safe,
        model=model,
        draft_attempts=attempts,
        guardrail_violations=[] if final_check.ok else list(final_check.violations),
        evidence=evidence,
        hitl_used=False,
    )
