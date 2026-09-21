"""AnswerComposer — soạn câu trả lời hỏi-đáp + guardrail (không HITL).

Phase 8: mặc định dùng LLM qua Prompt Registry (`answer_compose`) +
`infra/llm.completion.chat`. `HeuristicAnswerDraftBrain` giữ cho test / inject.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.agents.eval_agent import EvalAgentResult
from src.portfolio_watch.agents.news_agent import NewsAgentResult
from src.portfolio_watch.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import SeverityLevel
from src.portfolio_watch.domain.guardrails.output_checks import (
    check_output,
    check_rewrite_grounding,
    has_evidence_grounding,
    rewrite_keep_grounding,
)
from src.portfolio_watch.domain.ports import MemoryStore
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

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
        prices: list[PriceAgentResult] | None = None,
        news_list: list[NewsAgentResult] | None = None,
    ) -> str:
        ...


def _price_summary(
    price: PriceAgentResult | None,
    prices: list[PriceAgentResult] | None = None,
) -> str:
    if prices:
        parts = []
        for p in prices:
            one = _price_summary(p)
            parts.append(f"{p.symbol}: {one}")
        return " | ".join(parts) if parts else "(không có)"
    if price is None:
        return "(không có)"
    parts = []
    if price.latest_close is not None:
        parts.append(f"latest_close={price.latest_close}")
    if price.change_pct is not None:
        parts.append(f"change_pct={price.change_pct:.2f}%")
    if price.error:
        parts.append(f"error={price.error}")
    return "; ".join(parts) if parts else "(không có)"


def _news_summary(
    news: NewsAgentResult | None,
    news_list: list[NewsAgentResult] | None = None,
) -> str:
    if news_list:
        chunks = []
        for n in news_list:
            titles = [i.title for i in (n.items or [])[:3] if i.title]
            if titles:
                chunks.append(f"{n.symbol}: " + "; ".join(titles))
            else:
                chunks.append(f"{n.symbol}: (không có tin)")
        return " | ".join(chunks) if chunks else "(không có tin)"
    if news is None or not news.items:
        return "(không có tin)"
    titles = [i.title for i in news.items[:5] if i.title]
    return "; ".join(titles) if titles else "(không có tin)"


def _eval_summary(eval_result: EvalAgentResult | None) -> str:
    if eval_result is None:
        return "(không có)"
    sev = eval_result.severity
    return f"level={sev.level.value}; confidence={sev.confidence:.2f}; {sev.reasoning}"


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
        prices: list[PriceAgentResult] | None = None,
        news_list: list[NewsAgentResult] | None = None,
    ) -> str:
        sym = symbol or (price.symbol if price else None) or "N/A"
        if prices and len(prices) > 1:
            sym = "+".join(p.symbol for p in prices)
        parts = [f"Trả lời về {sym}:"]
        for p in prices or ([price] if price else []):
            if p and p.change_pct is not None and p.latest_close is not None:
                parts.append(
                    f"{p.symbol} đóng cửa {p.latest_close}, "
                    f"thay đổi {p.change_pct:.2f}%."
                )
            elif p and p.error:
                parts.append(f"{p.symbol}: không lấy được giá ({p.error}).")
        for n in news_list or ([news] if news else []):
            if n and n.items:
                titles = "; ".join(i.title for i in n.items[:3])
                parts.append(f"Tin {n.symbol}: {titles}.")
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


class LlmAnswerDraftBrain:
    """LLM composer: Prompt Registry `answer_compose` + chat (plain text)."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
        self._prompt_version = prompt_version

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
        prices: list[PriceAgentResult] | None = None,
        news_list: list[NewsAgentResult] | None = None,
    ) -> str:
        evid = "; ".join(evidence) if evidence else "(không có)"
        viol = (
            "; ".join(previous_violations) if previous_violations else "(không)"
        )
        sym_label = symbol or (price.symbol if price else "") or ""
        if prices and len(prices) > 1:
            sym_label = "+".join(p.symbol for p in prices)
        prompt_text = registry().render(
            "answer_compose",
            version=self._prompt_version,
            question=question or "",
            symbol=sym_label,
            price_summary=_price_summary(price, prices=prices),
            news_summary=_news_summary(news, news_list=news_list),
            eval_summary=_eval_summary(eval_result),
            evidence=evid,
            violations=viol,
        )
        raw = self._chat_fn(
            [
                {
                    "role": "user",
                    "content": f"{prompt_text}\n\n(model gợi ý: {model}, attempt={attempt})",
                }
            ],
            DETERMINISTIC,
        )
        answer = (raw or "").strip()
        if not answer:
            raise ValueError("AnswerComposer LLM trả về rỗng")
        return answer


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_ANSWER_BRAIN_FACTORY: Callable[[], AnswerDraftBrain] = LlmAnswerDraftBrain


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
    *,
    prices: list[PriceAgentResult] | None = None,
    news_list: list[NewsAgentResult] | None = None,
) -> list[str]:
    evidence: list[str] = []
    price_rows = prices if prices else ([price] if price is not None else [])
    for p in price_rows:
        if p.symbol:
            evidence.append(f"symbol:{p.symbol}")
        if p.change_pct is not None:
            evidence.append(f"{p.symbol}.change_pct={p.change_pct:.2f}%")
        if p.latest_close is not None:
            evidence.append(f"{p.symbol}.latest_close={p.latest_close}")
        if p.prev_close is not None:
            evidence.append(f"{p.symbol}.prev_close={p.prev_close}")
        if p.error:
            evidence.append(f"price_error:{p.symbol}:{p.error}")
    news_rows = news_list if news_list else ([news] if news is not None else [])
    for n in news_rows:
        for item in (n.items or [])[:5]:
            evidence.append(f"news:{n.symbol}:{item.title}")
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


from src.portfolio_watch.infra.monitoring.tracing import agent_step

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
    prices: list[PriceAgentResult] | None = None,
    news_list: list[NewsAgentResult] | None = None,
    turn: str = "",
) -> AnswerComposeResult:
    """Soạn câu trả lời + vòng rewrite khi guardrail fail. Không tạo HITL."""
    _ = memory_store, user_id  # preferences có thể dùng sau; MVP heuristic không cần
    evidence = build_evidence(
        price, news, eval_result, prices=prices, news_list=news_list
    )
    model = select_answer_model(eval_result)
    draft_brain = brain or _DEFAULT_ANSWER_BRAIN_FACTORY()
    violations: list[str] = []
    answer = ""
    attempts = 0
    last_grounded = ""

    for attempt in range(max(max_attempts, 1)):
        attempts = attempt + 1
        with agent_step(turn, "answer_composer", "draft", input={"attempt": attempt}):
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
                    prices=prices,
                    news_list=news_list,
                )
            except Exception as exc:  # noqa: BLE001
                answer = (
                    f"Không soạn được câu trả lời ({exc}). "
                    f"Evidence: {'; '.join(evidence) if evidence else 'không có'}."
                )
        with agent_step(turn, "answer_composer", "guardrail_retry"):
            if has_evidence_grounding(answer, evidence):
                last_grounded = answer
            check = check_output("", answer, evidence)
            # Rewrite (attempt>0) không được bỏ hết số liệu evidence.
            ground = check_rewrite_grounding(
                answer, evidence, require=attempt > 0
            )
        if check.ok and ground.ok:
            return AnswerComposeResult(
                answer=answer,
                model=model,
                draft_attempts=attempts,
                guardrail_violations=[],
                evidence=evidence,
                hitl_used=False,
            )
        violations = list(check.violations) + list(ground.violations)

    # Fallback: gỡ mua/bán từ bản đã có số liệu, hoặc tóm tắt evidence.
    safe = rewrite_keep_grounding(last_grounded or answer, evidence)
    final_check = check_output("", safe, evidence)
    return AnswerComposeResult(
        answer=safe,
        model=model,
        draft_attempts=attempts,
        guardrail_violations=[] if final_check.ok else list(final_check.violations),
        evidence=evidence,
        hitl_used=False,
    )
