"""supervisor_agent nodes + RewriteQuestion — nhánh hỏi-đáp (routing agent cần gọi).

Phase 6+: mặc định dùng LLM qua Prompt Registry
(`rewrite_question`, `supervisor_routing`) + structured output.
Heuristic*Brain giữ cho unit test / inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.portfolio_watch.agents.supervisor_agent.schemas import (
    RewriteOutput,
    SupervisorOutput,
)
from src.portfolio_watch.domain.entities import RoutingDecision
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry
from src.portfolio_watch.infra.llm.structured import call_llm_structured
from src.portfolio_watch.infra.storage.long_term_memory import (
    recall_long_term,
    save_to_long_term,
)
from src.portfolio_watch.shared.schemas import MemoryFact

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
        "CUA",
        "NHE",
        "VAY",
        "TIN",  # "tin tức" — không phải mã
        "TUC",
        "MOT",
        "HAY",
        "CHO",
        "CAC",
        "DEN",
        "VOI",
        "NUA",
        "RAT",
        "HOM",
        "NAY",
        "BAO",  # «bao nhiêu» — không phải mã
    }
)
_REF_PREV_RE = re.compile(
    r"("
    r"mã đó|ma do|mã này|ma nay|"
    r"còn mã|con ma|mã vừa|ma vua|cùng mã|cung ma|"
    r"cổ phiếu đó|co phieu do|cổ phiếu này|co phieu nay|"
    r"\bnó\b|\bno\b|em đó|em do"
    r")",
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
    "đối chiếu",
    "doi chieu",
    "biến động",
    "bien dong",
    "mạnh hơn",
    "manh hon",
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
_DIAGRAM_PHRASES = (
    "vẽ sơ đồ",
    "ve so do",
    "diagram",
    "flowchart",
    "sơ đồ",
    "so do",
)
_FOLLOWUP_RE = re.compile(
    r"(giá|gia|giảm|giam|tăng|tang|thế nào|the nao|ra sao|sao rồi|sao roi)",
    re.IGNORECASE,
)
_ALLOWED_AGENTS = frozenset({"price", "news", "eval", "diagram"})
_ALLOWED_INTENTS = frozenset({"price_lookup", "news_lookup", "explain", "diagram"})


@dataclass(slots=True)
class RewrittenQuestion:
    original: str
    rewritten: str
    symbol: str | None
    intent: str  # price_lookup | news_lookup | explain
    # So sánh đa mã (VNM+HPG…); symbol = mã chính (phần tử đầu).
    symbols: list[str] = field(default_factory=list)


class RewriteBrain(Protocol):
    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        ...


class SupervisorBrain(Protocol):
    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        ...


def _extract_symbols(text: str) -> list[str]:
    """Lấy mọi mã 3 chữ cái (theo thứ tự xuất hiện, không trùng)."""
    if not text:
        return []
    out: list[str] = []
    for ma in _MA_SYMBOL_RE.finditer(text):
        sym = ma.group(1).strip().upper()
        if sym and sym not in out:
            out.append(sym)
    for match in _TICKER_RE.finditer(text.upper()):
        sym = match.group(1)
        if sym not in _TICKER_STOPWORDS and sym not in out:
            out.append(sym)
    return out


def _extract_symbol(text: str) -> str | None:
    syms = _extract_symbols(text)
    return syms[0] if syms else None


def _normalize_symbols(
    *,
    primary: str | None,
    from_text: list[str],
    from_llm: list[str] | None = None,
) -> tuple[str | None, list[str]]:
    ordered: list[str] = []
    for sym in list(from_llm or []) + ([primary] if primary else []) + list(from_text):
        s = (sym or "").strip().upper()
        if s and s not in ordered:
            ordered.append(s)
    return (ordered[0] if ordered else None), ordered


def _symbol_from_conversation(conversation: list[dict]) -> str | None:
    """Lấy mã gần nhất từ hội thoại (user trước, rồi assistant)."""
    for turn in reversed(conversation or []):
        content = str(turn.get("content") or "")
        sym = _extract_symbol(content)
        if sym:
            return sym
    return None


def _symbol_from_memories(memories: list[str] | None) -> str | None:
    """Lấy mã gần nhất từ danh sách long-term memories."""
    for mem in memories or []:
        sym = _extract_symbol(str(mem))
        if sym:
            return sym
    return None


def _apply_memory_symbol(
    question: str,
    *,
    symbol: str | None,
    symbols: list[str],
    conversation: list[dict],
    memories: list[str] | None = None,
) -> tuple[str | None, list[str]]:
    """Gắn mã từ memory (conversation hoặc long-term memories) khi câu hỏi dùng đại từ / follow-up không có ticker."""
    if not _needs_memory_symbol(question, symbol):
        return symbol, symbols
    mem = _symbol_from_conversation(conversation) or _symbol_from_memories(memories)
    if not mem:
        return symbol, symbols
    # Đại từ → memory thắng (tránh false ticker kiểu BAO từ «bao nhiêu»).
    if _REF_PREV_RE.search(question):
        return mem, [mem]
    if not symbols:
        return mem, [mem]
    if mem not in symbols:
        return mem, [mem, *symbols]
    return mem, symbols


def _ground_rewritten(question: str, symbols: list[str], rewritten: str) -> str:
    """Đảm bảo câu rewrite gắn mã tường minh (downstream agents)."""
    q = (rewritten or question or "").strip() or (question or "").strip()
    if not symbols:
        return q
    tag = "+".join(symbols)
    if tag in q.upper():
        return q
    return f"[{tag}] {q}"


def _has_news_intent(lower: str) -> bool:
    """Tránh false positive: 'thông tin' chứa 'tin' nhưng không phải hỏi tin tức."""
    cleaned = (
        lower.replace("thông tin", " ").replace("thong tin", " ")
    )
    if any(h in cleaned for h in _NEWS_PHRASES):
        return True
    return re.search(r"\btin\b", cleaned) is not None


def _has_diagram_intent(lower: str) -> bool:
    return any(h in lower for h in _DIAGRAM_PHRASES)


def _needs_memory_symbol(question: str, symbol: str | None) -> bool:
    # Đại từ luôn resolve từ hội thoại (kể cả khi extract nhầm ticker).
    if _REF_PREV_RE.search(question):
        return True
    if symbol is not None:
        return False
    # Câu follow-up ngắn không có ticker → lấy symbol từ hội thoại
    return bool(_FOLLOWUP_RE.search(question)) and len(question.strip()) < 80


class HeuristicRewriteBrain:
    """Chuẩn hoá câu hỏi + suy ra symbol (kể cả tham chiếu 'mã đó')."""

    def rewrite(
        self,
        question: str,
        conversation: list[dict],
        *,
        memories: list[str] | None = None,
    ) -> RewrittenQuestion:
        q = (question or "").strip()
        symbols = _extract_symbols(q)
        symbol = symbols[0] if symbols else None
        symbol, symbols = _apply_memory_symbol(
            q,
            symbol=symbol,
            symbols=symbols,
            conversation=conversation,
            memories=memories,
        )

        intent = "price_lookup"
        lower = q.lower()
        if _has_diagram_intent(lower):
            intent = "diagram"
        elif any(h in lower for h in _EXPLAIN_HINTS):
            intent = "explain"
        elif _has_news_intent(lower):
            intent = "news_lookup"

        symbol, symbols = _normalize_symbols(primary=symbol, from_text=symbols)
        rewritten = _ground_rewritten(q, symbols, q)
        return RewrittenQuestion(
            original=q,
            rewritten=rewritten,
            symbol=symbol,
            intent=intent,
            symbols=symbols,
        )


class HeuristicSupervisorBrain:
    """Routing heuristic: price-only / +news / +eval theo intent."""

    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        intent = rewritten.intent or "price_lookup"
        if intent == "diagram":
            agents = ["diagram"]
            reason = "yêu cầu vẽ sơ đồ → diagram_agent"
        elif intent == "explain":
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


class LlmRewriteBrain:
    """LLM rewrite qua registry `rewrite_question` + structured output."""

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

    def rewrite(
        self,
        question: str,
        conversation: list[dict],
        *,
        memories: list[str] | None = None,
    ) -> RewrittenQuestion:
        q = (question or "").strip()
        conv_json = json.dumps(conversation or [], ensure_ascii=False)
        prompt_text = registry().render(
            "rewrite_question",
            version=self._prompt_version,
            question=q,
            conversation=conv_json,
        )
        messages = [{"role": "user", "content": prompt_text}]

        try:
            output = call_llm_structured(
                messages,
                RewriteOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
        except Exception:  # inner schema-fail guard: do not crash
            syms_from_q = _extract_symbols(q)
            output = RewriteOutput(
                rewritten=q,
                symbol=syms_from_q[0] if syms_from_q else None,
                symbols=syms_from_q,
                intent="price_lookup",
            )

        rewritten = (output.rewritten or q).strip() or q
        symbol = output.symbol
        llm_syms = output.symbols
        intent = output.intent
        if intent not in _ALLOWED_INTENTS:
            intent = "price_lookup"

        # Heuristic bổ sung: LLM hay chỉ trả 1 mã dù câu hỏi so sánh nhiều mã.
        symbol, symbols = _normalize_symbols(
            primary=symbol,
            from_text=_extract_symbols(f"{q} {rewritten}"),
            from_llm=llm_syms,
        )
        # Đại từ / follow-up không có ticker → lấy mã từ conversation hoặc long-term memory.
        symbol, symbols = _apply_memory_symbol(
            q,
            symbol=symbol,
            symbols=symbols,
            conversation=conversation,
            memories=memories,
        )
        symbol, symbols = _normalize_symbols(primary=symbol, from_text=symbols)
        rewritten = _ground_rewritten(q, symbols, rewritten)
        # Đa mã / từ khóa so sánh → explain (price+news+eval).
        blob = f"{q} {rewritten}".lower()
        if _has_diagram_intent(blob):
            intent = "diagram"
        elif len(symbols) > 1 or any(h in blob for h in _EXPLAIN_HINTS):
            if intent == "price_lookup":
                intent = "explain"
        return RewrittenQuestion(
            original=q,
            rewritten=rewritten,
            symbol=symbol,
            intent=intent,
            symbols=symbols,
        )


class LlmSupervisorBrain:
    """LLM routing qua registry `supervisor_routing` + structured output."""

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

    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        prompt_text = registry().render(
            "supervisor_routing",
            version=self._prompt_version,
            rewritten_question=rewritten.rewritten or rewritten.original,
            symbol=rewritten.symbol or "",
            intent=rewritten.intent or "price_lookup",
        )
        messages = [{"role": "user", "content": prompt_text}]

        try:
            output = call_llm_structured(
                messages,
                SupervisorOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
        except Exception as exc:  # inner schema-fail guard: do not crash
            intent = rewritten.intent or "price_lookup"
            if intent == "diagram":
                fallback_agents = ["diagram"]
            elif intent == "explain":
                fallback_agents = ["price", "news", "eval"]
            elif intent == "news_lookup":
                fallback_agents = ["price", "news"]
            else:
                fallback_agents = ["price"]
            output = SupervisorOutput(
                agents_to_call=fallback_agents,
                reason=f"supervisor schema fallback: {exc}",
            )

        agents: list[str] = []
        for a in output.agents_to_call:
            name = str(a).strip().lower()
            if name in _ALLOWED_AGENTS and name not in agents:
                agents.append(name)
        if not agents:
            agents = ["price"]
        reason = str(output.reason or "").strip() or "llm routing"
        return RoutingDecision(
            route=rewritten.intent or "price_lookup",
            reason=reason,
            agents_to_call=agents,
        )


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_REWRITE_FACTORY: Callable[[], RewriteBrain] = LlmRewriteBrain
_DEFAULT_SUPERVISOR_FACTORY: Callable[[], SupervisorBrain] = LlmSupervisorBrain


from src.portfolio_watch.infra.monitoring.tracing import agent_step

def rewrite_question(
    question: str,
    conversation: list[dict],
    *,
    brain: RewriteBrain | None = None,
    turn: str = "",
    memories: list[str] | None = None,
) -> RewrittenQuestion:
    rewriter = brain or _DEFAULT_REWRITE_FACTORY()
    try:
        with agent_step(
            turn,
            "rewrite_question",
            "rewrite",
            input={"question": question},
        ) as step_box:
            try:
                res = rewriter.rewrite(question, conversation, memories=memories)
            except TypeError:
                res = rewriter.rewrite(question, conversation)
            step_box["output"] = {
                "rewritten": res.rewritten,
                "symbol": res.symbol,
                "symbols": list(res.symbols or []),
            }
            return res
    except Exception:  # noqa: BLE001
        q = (question or "").strip()
        symbol, symbols = _normalize_symbols(
            primary=None, from_text=_extract_symbols(q)
        )
        return RewrittenQuestion(
            original=q,
            rewritten=q,
            symbol=symbol,
            intent="price_lookup",
            symbols=symbols,
        )


def route_question(
    rewritten: RewrittenQuestion,
    *,
    brain: SupervisorBrain | None = None,
    turn: str = "",
) -> RoutingDecision:
    supervisor = brain or _DEFAULT_SUPERVISOR_FACTORY()
    try:
        with agent_step(
            turn,
            "supervisor",
            "route",
            input={"question": rewritten.rewritten or rewritten.original},
        ) as step_box:
            res = supervisor.route(rewritten)
            step_box["output"] = {
                "route": str(getattr(res.route, "value", res.route)),
                "agents": list(res.agents_to_call or []),
                "reason": res.reason,
            }
            return res
    except Exception as exc:  # noqa: BLE001
        return RoutingDecision(
            route="price_lookup",
            reason=f"supervisor lỗi, fallback price: {exc}",
            agents_to_call=["price"],
        )


def recall_memory(state: dict[str, Any], *, k: int = 3) -> dict[str, Any]:
    """Đầu lượt: đọc long-term (Qdrant hoặc in-memory fallback) theo user_id.

    Không user_id hoặc user_id rỗng -> bỏ qua long-term, không crash.
    """
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        return {"memories": []}

    query = str(state.get("rewritten_question") or state.get("question") or "").strip()
    try:
        memories = recall_long_term(user_id, query, k=k)
    except Exception:
        memories = []
    return {"memories": memories}


def _extract_long_term_fact(
    question: str,
    answer: str,
    state: dict[str, Any] | None = None,
    *,
    chat_fn: Callable[..., str] | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> str:
    """Trích 1 sự thật dài hạn về user: mã theo dõi, khẩu vị, sở thích."""
    q = (question or "").strip()
    symbols = list((state.get("symbols") if state else None) or _extract_symbols(q))

    # Thử qua Structured LLM call nếu có brain / key
    try:
        prompt_text = (
            "Trích 1 sự thật đáng nhớ dài hạn về user (mã theo dõi, danh mục, khẩu vị, phong cách) "
            "từ đoạn hội thoại sau, nếu có. Không bịa.\n\n"
            f"Câu hỏi: {question}\nTrả lời: {answer}"
        )
        fact_obj = call_llm_structured(
            [{"role": "user", "content": prompt_text}],
            MemoryFact,
            chat_fn=chat_fn,
            chat_parsed_fn=chat_parsed_fn,
            params=DETERMINISTIC,
            max_retries=1,
        )
        if fact_obj.worth_saving and fact_obj.fact.strip():
            return fact_obj.fact.strip()
    except Exception:
        pass

    # Heuristic fallback an toàn (đủ cho test/offline/deterministic)
    lower = q.lower()
    interest_words = (
        "quan tâm",
        "theo dõi",
        "nắm giữ",
        "danh mục",
        "đang giữ",
        "mua",
        "bán",
        "thích",
    )
    has_interest = any(w in lower for w in interest_words)
    # Chỉ heuristic-store khi user thể hiện quan tâm/theo dõi — không lưu mọi câu lookup có ticker.
    if symbols and has_interest:
        sym_str = ", ".join(symbols)
        return f"Người dùng quan tâm theo dõi mã {sym_str}."
    if has_interest and len(q) < 120:
        return f"Người dùng: {q}"
    return ""


def store_memory(
    state: dict[str, Any],
    *,
    brain: Any | None = None,
    extract_fn: Callable[[str, str], MemoryFact | None] | None = None,
) -> dict[str, Any]:
    """Cuối lượt: trích xuất sự thật dài hạn (nếu có) rồi lưu vào long-term memory.

    Không user_id hoặc user_id rỗng -> bỏ qua long-term, không crash.
    """
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        return {}

    question = str(state.get("question") or "").strip()
    answer = str(state.get("answer") or "").strip()
    if not question or not answer:
        return {}

    fact_text = ""
    if extract_fn is not None:
        try:
            mf = extract_fn(question, answer)
            if mf and mf.worth_saving and mf.fact.strip():
                fact_text = mf.fact.strip()
        except Exception:
            fact_text = ""
    elif brain is not None and hasattr(brain, "extract_fact"):
        try:
            fact_text = str(brain.extract_fact(question, answer) or "").strip()
        except Exception:
            fact_text = ""
    else:
        fact_text = _extract_long_term_fact(question, answer, state)

    if fact_text:
        try:
            save_to_long_term(user_id, fact_text)
            return {"stored_fact": fact_text}
        except Exception:
            pass
    return {}
