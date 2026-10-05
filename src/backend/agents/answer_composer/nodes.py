"""AnswerComposer — soạn câu trả lời hỏi-đáp + guardrail (không HITL).

Phase 8: mặc định dùng LLM qua Prompt Registry (`answer_compose`) +
`infra/llm.completion.chat`. `HeuristicAnswerDraftBrain` giữ cho test / inject.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

_logger = logging.getLogger(__name__)


def sanitize_answer_chart_markdown(text: str) -> str:
    """Chuẩn hóa cú pháp markdown ảnh biểu đồ trong câu trả lời.

    1. Gỡ bỏ tiền tố nhầm 'chart_path:' (ví dụ ![alt](chart_path:/charts/xyz.png) -> ![alt](/charts/xyz.png))
    2. Đảm bảo đường dẫn biểu đồ cục bộ có dấu '/' dẫn đầu (ví dụ ![alt](charts/xyz.png) -> ![alt](/charts/xyz.png))
    """
    if not text:
        return text

    def _fix_image_url(match: re.Match) -> str:
        alt = match.group(1)
        raw_url = match.group(2).strip()
        cleaned_url = re.sub(r"^chart_path:\s*", "", raw_url, flags=re.IGNORECASE)
        if not (
            cleaned_url.startswith("/")
            or cleaned_url.startswith("http://")
            or cleaned_url.startswith("https://")
            or cleaned_url.startswith("data:")
        ):
            cleaned_url = "/" + cleaned_url
        return f"![{alt}]({cleaned_url})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _fix_image_url, text)


from backend.agents.eval_agent import EvalAgentResult
from backend.agents.news_agent import NewsAgentResult
from backend.agents.price_agent import PriceAgentResult
from backend.domain.entities import SeverityLevel
from backend.domain.guardrails.output_checks import (
    check_output,
    check_rewrite_grounding,
    has_evidence_grounding,
    rewrite_keep_grounding,
)
from backend.domain.ports import MemoryStore
from backend.infra.llm.completion import chat
from backend.infra.llm.params import DETERMINISTIC
from backend.infra.llm.prompt_experiment import pick_prompt_version
from backend.infra.llm.prompt_registry import registry
from backend.shared.settings import settings

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
        on_token: Callable[[str], None] | None = None,
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
    def _format_item(item) -> str:
        src = f" (nguồn: {getattr(item, 'source', 'CafeF')})" if getattr(item, "source", None) else ""
        return f"{item.title}{src}"

    if news_list:
        chunks = []
        for n in news_list:
            titles = [_format_item(i) for i in (n.items or [])[:3] if i.title]
            if titles:
                chunks.append(f"{n.symbol}: " + "; ".join(titles))
            else:
                chunks.append(f"{n.symbol}: (không có tin)")
        return " | ".join(chunks) if chunks else "(không có tin)"
    if news is None or not news.items:
        return "(không có tin)"
    titles = [_format_item(i) for i in news.items[:5] if i.title]
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
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        all_prices = prices or ([price] if price else [])
        all_news = news_list or ([news] if news else [])
        sym = symbol or (price.symbol if price else None) or "N/A"
        if all_prices and len(all_prices) > 1:
            sym = "+".join(p.symbol for p in all_prices)

        # Xử lý Empty State danh mục đầu tư (Task 5.2)
        if any("portfolio_status:empty" in e for e in evidence):
            parts = [
                "Danh mục đầu tư của bạn hiện tại chưa có cổ phiếu nào (danh mục rỗng).",
                "Hướng dẫn thêm mã đầu tiên:",
                "- Bước 1: Nhập mã cổ phiếu (ví dụ: FPT, VNM, HPG) vào ô 'Mã'.",
                "- Bước 2: Nhập số lượng cổ phiếu cần theo dõi (ví dụ: 100, 500, 1000).",
                "- Bước 3: Nhập giá mua bình quân (nghìn đồng, ví dụ: 66.0) rồi nhấn 'Thêm'.",
                "Hệ thống sẽ tự động cập nhật Tổng NAV và tính toán Lãi/Lỗ theo thời gian thực.",
                "Thông tin tham khảo, không phải lời khuyên đầu tư.",
            ]
            ans = "\n".join(parts)
            if on_token:
                words = ans.split(" ")
                for i, w in enumerate(words):
                    sep = " " if i < len(words) - 1 else ""
                    on_token(w + sep)
            return ans

        parts: list[str] = []
        if any("portfolio_status:active" in e for e in evidence):
            nav_e = next((e.split("=", 1)[1] for e in evidence if e.startswith("portfolio_total_nav=")), "")
            cost_e = next((e.split("=", 1)[1] for e in evidence if e.startswith("portfolio_total_cost=")), "")
            pnl_e = next((e.split("=", 1)[1] for e in evidence if e.startswith("portfolio_total_unrealized_pnl=")), "")
            pct_e = next((e.split("=", 1)[1] for e in evidence if e.startswith("portfolio_total_pnl_pct=")), "")
            if nav_e:
                parts.append(
                    f"Tổng quan danh mục: Tổng NAV {nav_e} VND, Vốn {cost_e} VND, Lãi/Lỗ {pnl_e} VND ({pct_e})."
                )
        if len(all_prices) > 1 or len(all_news) > 1:
            parts.append(f"Tổng hợp so sánh về {sym}:")
            # 1. So sánh giá
            price_details = []
            for p in all_prices:
                if p and p.change_pct is not None and p.latest_close is not None:
                    price_details.append(
                        f"{p.symbol} đóng cửa {p.latest_close}, thay đổi {p.change_pct:.2f}%"
                    )
                elif p and p.error:
                    price_details.append(f"{p.symbol}: lỗi giá ({p.error.strip()})")
            if price_details:
                parts.append("Mục so sánh giá: " + "; ".join(price_details) + ".")

            # 2. Tin tức
            news_details = []
            for n in all_news:
                if n and n.items:
                    formatted_titles = []
                    for i in n.items[:2]:
                        src_tag = f" (nguồn: {getattr(i, 'source', 'CafeF')})" if getattr(i, "source", None) else ""
                        formatted_titles.append(f"{i.title}{src_tag}")
                    news_details.append(f"{n.symbol}: {'; '.join(formatted_titles)}")
            if news_details:
                parts.append("Mục tin tức sự kiện: " + "; ".join(news_details) + ".")

            # 3. Đánh giá
            if eval_result is not None:
                sev = eval_result.severity
                parts.append(f"Mục đánh giá: {sev.reasoning} (mức {sev.level.value}).")
        else:
            parts.append(f"Trả lời về {sym}:")
            for p in all_prices:
                if p and p.change_pct is not None and p.latest_close is not None:
                    parts.append(
                        f"{p.symbol} đóng cửa {p.latest_close}, "
                        f"thay đổi {p.change_pct:.2f}%."
                    )
                elif p and p.error:
                    err_text = p.error.strip()
                    if any(k in err_text.lower() for k in ("không tìm thấy", "mã cổ phiếu", "không tồn tại")):
                        parts.append(
                            f"{p.symbol}: Không tìm thấy thông tin hoặc mã không tồn tại trên thị trường chứng khoán Việt Nam. "
                            f"Gợi ý: Quý khách vui lòng kiểm tra lại mã cổ phiếu (ví dụ các mã VN30 phổ biến như FPT, VNM, HPG, TCB, MBB)."
                        )
                    elif any(k in err_text.lower() for k in ("không lấy được", "nguồn dữ liệu", "kết nối")):
                        parts.append(f"{p.symbol}: {err_text}.")
                    else:
                        parts.append(f"{p.symbol}: không lấy được giá ({err_text}).")
            for n in all_news:
                if n and n.items:
                    formatted_titles = []
                    for i in n.items[:3]:
                        src_tag = f" (nguồn: {getattr(i, 'source', 'CafeF')})" if getattr(i, "source", None) else ""
                        formatted_titles.append(f"{i.title}{src_tag}")
                    parts.append(f"Tin {n.symbol}: {'; '.join(formatted_titles)}.")
            if eval_result is not None:
                sev = eval_result.severity
                parts.append(
                    f"Đánh giá: {sev.reasoning} "
                    f"(mức {sev.level.value})."
                )

        cp = next((e.split(":", 1)[1] for e in evidence if e.startswith("chart_path:")), None)
        if cp:
            parts.append(f"Đã tạo biểu đồ kỹ thuật: ![Biểu đồ {sym or 'kỹ thuật'}]({cp}) tại: {cp}.")
        if not evidence:
            parts.append("Chưa có đủ dữ liệu để kết luận chi tiết.")
        parts.append("Thông tin tham khảo, không phải lời khuyên đầu tư.")
        if attempt > 0 and previous_violations:
            parts.append(
                "Đã chỉnh lại để loại khuyến nghị mua/bán và số không có trong evidence."
            )
        ans = " ".join(parts)
        if on_token:
            words = ans.split(" ")
            for i, w in enumerate(words):
                sep = " " if i < len(words) - 1 else ""
                on_token(w + sep)
        return ans


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
        on_token: Callable[[str], None] | None = None,
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
        messages = [
            {
                "role": "user",
                "content": f"{prompt_text}\n\n(model gợi ý: {model}, attempt={attempt})",
            }
        ]
        from backend.infra.cache.exact import llm_cache_scope

        with llm_cache_scope(
            prompt_name="answer_compose",
            prompt_version=self._prompt_version,
            normalized_question=question or "",
        ):
            if on_token:
                from backend.infra.llm.completion import chat_stream
                chunks = []
                try:
                    for delta in chat_stream(messages, DETERMINISTIC, model=model):
                        chunks.append(delta)
                        on_token(delta)
                    answer = "".join(chunks).strip()
                except Exception:
                    raw = self._chat_fn(messages, DETERMINISTIC, model=model)
                    answer = (raw or "").strip()
                    if on_token and answer:
                        for w in answer.split(" "):
                            on_token(w + " ")
            else:
                raw = self._chat_fn(messages, DETERMINISTIC, model=model)
                answer = (raw or "").strip()

        if not answer:
            raise ValueError("AnswerComposer LLM trả về rỗng")
        return sanitize_answer_chart_markdown(answer)


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
    chart_path: str | None = None,
    portfolio_summary: Any | None = None,
    portfolio_watch_result: Any | None = None,
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
    if chart_path:
        norm_cp = str(chart_path).strip()
        if not (norm_cp.startswith("/") or norm_cp.startswith("http://") or norm_cp.startswith("https://")):
            norm_cp = "/" + norm_cp
        evidence.append(f"chart_path:{norm_cp}")
        evidence.append("chart_status:đã_tạo_biểu_đồ_thành_công")
    if portfolio_summary is not None:
        items = getattr(portfolio_summary, "items", None) or []
        u_id = getattr(portfolio_summary, "user_id", "default")
        evidence.append(f"portfolio_user_id:{u_id}")
        if len(items) == 0:
            evidence.append("portfolio_status:empty")
            evidence.append("portfolio_guide:bước 1 2 3 thêm mã cổ phiếu 100 500 1000 66.0 fpt vnm hpg")
        else:
            evidence.append("portfolio_status:active")
            nav = getattr(portfolio_summary, "total_nav", 0.0)
            cost = getattr(portfolio_summary, "total_cost", 0.0)
            pnl = getattr(portfolio_summary, "total_unrealized_pnl", 0.0)
            pnl_pct = getattr(portfolio_summary, "total_pnl_pct", 0.0)
            evidence.append(f"portfolio_total_nav={nav}")
            evidence.append(f"portfolio_total_cost={cost}")
            evidence.append(f"portfolio_total_unrealized_pnl={pnl}")
            evidence.append(f"portfolio_total_pnl_pct={pnl_pct:.2f}%")
            for it in items:
                evidence.append(
                    f"holding:{it.symbol}:qty={it.quantity}:cost={it.cost_basis}:pnl={it.unrealized_pnl}:pnl_pct={it.pnl_pct:.2f}%"
                )
    if portfolio_watch_result is not None:
        pw_items = getattr(portfolio_watch_result, "watchlist_items", []) or []
        if pw_items:
            evidence.append("watchlist_status:active")
            for it in pw_items:
                evidence.append(f"watchlist_symbol:{it.symbol}:threshold={it.threshold_pct:.1f}%")
        elif getattr(portfolio_watch_result, "intent", "") == "watchlist":
            evidence.append("watchlist_status:empty")

    # dedupe giữ thứ tự
    seen: set[str] = set()
    out: list[str] = []
    for e in evidence:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


from backend.infra.monitoring.tracing import agent_step

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
    chart_path: str | None = None,
    portfolio_summary: Any | None = None,
    portfolio_watch_result: Any | None = None,
    turn: str = "",
    on_token: Callable[[str], None] | None = None,
) -> AnswerComposeResult:
    """Soạn câu trả lời + vòng rewrite khi guardrail fail. Không tạo HITL."""
    _ = memory_store
    prompt_version = pick_prompt_version(
        user_id,
        enabled=settings.prompt_ab_enabled,
        version_a=settings.prompt_ab_version_a,
        version_b=settings.prompt_ab_version_b,
        split_pct=settings.prompt_ab_split_pct,
    )
    if brain is None:
        draft_brain: AnswerDraftBrain = LlmAnswerDraftBrain(prompt_version=prompt_version)
    else:
        draft_brain = brain
    from backend.infra.cost.tracker import set_cost_context

    set_cost_context(feature="answer_composer", prompt_version=str(prompt_version))
    effective_summary = portfolio_summary or (getattr(portfolio_watch_result, "portfolio_summary", None) if portfolio_watch_result else None)
    evidence = build_evidence(
        price,
        news,
        eval_result,
        prices=prices,
        news_list=news_list,
        chart_path=chart_path,
        portfolio_summary=effective_summary,
        portfolio_watch_result=portfolio_watch_result,
    )

    # Nếu đây là câu hỏi danh mục/watchlist và PortfolioWatchAgent đã định dạng bảng chuẩn
    if portfolio_watch_result is not None and getattr(portfolio_watch_result, "formatted_markdown", ""):
        formatted_ans = portfolio_watch_result.formatted_markdown
        if on_token:
            words = formatted_ans.split(" ")
            for i, w in enumerate(words):
                sep = " " if i < len(words) - 1 else ""
                on_token(w + sep)
        return AnswerComposeResult(
            answer=formatted_ans,
            model="portfolio_watch_direct",
            draft_attempts=1,
            guardrail_violations=[],
            evidence=evidence,
            hitl_used=False,
        )
    model = select_answer_model(eval_result)
    violations: list[str] = []
    answer = ""
    attempts = 0
    last_grounded = ""

    for attempt in range(max(max_attempts, 1)):
        attempts = attempt + 1
        with agent_step(turn, "answer_composer", "draft", input={"attempt": attempt}) as box:
            try:
                import inspect
                sig = inspect.signature(draft_brain.compose)
                kwargs = {
                    "question": question,
                    "symbol": symbol,
                    "price": price,
                    "news": news,
                    "eval_result": eval_result,
                    "evidence": evidence,
                    "model": model,
                    "attempt": attempt,
                    "previous_violations": list(violations),
                    "prices": prices,
                    "news_list": news_list,
                }
                if "on_token" in sig.parameters:
                    kwargs["on_token"] = on_token
                answer = draft_brain.compose(**kwargs)
                if on_token and "on_token" not in sig.parameters and answer:
                    for w in answer.split(" "):
                        on_token(w + " ")
                box["output"] = (answer or "")[:500]
            except Exception as exc:  # noqa: BLE001
                _logger.warning("AnswerComposer brain lỗi hoặc toàn bộ provider ngoại tuyến (%s). Kích hoạt Heuristic Fallback.", exc)
                try:
                    heuristic_brain = HeuristicAnswerDraftBrain()
                    heuristic_kwargs = {
                        "question": question,
                        "symbol": symbol,
                        "price": price,
                        "news": news,
                        "eval_result": eval_result,
                        "evidence": evidence,
                        "model": "heuristic-fallback",
                        "attempt": attempt,
                        "previous_violations": list(violations),
                        "prices": prices,
                        "news_list": news_list,
                        "on_token": on_token,
                    }
                    answer = heuristic_brain.compose(**heuristic_kwargs)
                    box["output"] = f"[HEURISTIC_FALLBACK] {(answer or '')[:400]}"
                except Exception as h_exc:
                    answer = (
                        f"Không soạn được câu trả lời ({exc}). "
                        f"Evidence: {'; '.join(evidence) if evidence else 'không có'}."
                    )
                    box["output"] = {"error": str(exc), "heuristic_error": str(h_exc)}
                    if on_token:
                        on_token(answer)
        with agent_step(
            turn,
            "answer_composer",
            "guardrail_retry",
            input={"answer": (answer or "")[:200]},
        ) as box:
            if has_evidence_grounding(answer, evidence):
                last_grounded = answer
            check = check_output("", answer, evidence)
            # Rewrite (attempt>0) không được bỏ hết số liệu evidence.
            ground = check_rewrite_grounding(
                answer, evidence, require=attempt > 0
            )
            box["output"] = {
                "ok": check.ok and ground.ok,
                "violations": list(check.violations) + list(ground.violations),
            }
        if check.ok and ground.ok:
            return AnswerComposeResult(
                answer=sanitize_answer_chart_markdown(answer),
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
        answer=sanitize_answer_chart_markdown(safe),
        model=model,
        draft_attempts=attempts,
        guardrail_violations=[] if final_check.ok else list(final_check.violations),
        evidence=evidence,
        hitl_used=False,
    )
