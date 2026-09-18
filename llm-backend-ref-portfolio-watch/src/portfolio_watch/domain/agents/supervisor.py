"""Supervisor + RewriteQuestion — nhánh hỏi-đáp (routing agent cần gọi).

Phase 8: mặc định dùng LLM qua Prompt Registry
(`rewrite_question`, `supervisor_routing`) + `infra/llm.completion.chat`.
Heuristic*Brain giữ cho unit test / inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from src.portfolio_watch.domain.entities import RoutingDecision
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

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
_FOLLOWUP_RE = re.compile(
    r"(giá|gia|giảm|giam|tăng|tang|thế nào|the nao|ra sao|sao rồi|sao roi)",
    re.IGNORECASE,
)
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)
_ALLOWED_AGENTS = frozenset({"price", "news", "eval"})
_ALLOWED_INTENTS = frozenset({"price_lookup", "news_lookup", "explain"})


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


def _apply_memory_symbol(
    question: str,
    *,
    symbol: str | None,
    symbols: list[str],
    conversation: list[dict],
) -> tuple[str | None, list[str]]:
    """Gắn mã từ memory khi câu hỏi dùng đại từ / follow-up không có ticker."""
    if not _needs_memory_symbol(question, symbol):
        return symbol, symbols
    mem = _symbol_from_conversation(conversation)
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


def _needs_memory_symbol(question: str, symbol: str | None) -> bool:
    # Đại từ luôn resolve từ hội thoại (kể cả khi extract nhầm ticker).
    if _REF_PREV_RE.search(question):
        return True
    if symbol is not None:
        return False
    # Câu follow-up ngắn không có ticker → lấy symbol từ hội thoại
    return bool(_FOLLOWUP_RE.search(question)) and len(question.strip()) < 80


def _parse_json_obj(raw: str) -> dict:
    text = (raw or "").strip()
    match = _JSON_OBJ_RE.search(text)
    payload = match.group(0) if match else text
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("LLM không trả JSON object")
    return data


class HeuristicRewriteBrain:
    """Chuẩn hoá câu hỏi + suy ra symbol (kể cả tham chiếu 'mã đó')."""

    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        q = (question or "").strip()
        symbols = _extract_symbols(q)
        symbol = symbols[0] if symbols else None
        symbol, symbols = _apply_memory_symbol(
            q, symbol=symbol, symbols=symbols, conversation=conversation
        )

        intent = "price_lookup"
        lower = q.lower()
        if any(h in lower for h in _EXPLAIN_HINTS):
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
        if intent == "explain":
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
    """LLM rewrite qua registry `rewrite_question`."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
        self._prompt_version = prompt_version

    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        q = (question or "").strip()
        conv_json = json.dumps(conversation or [], ensure_ascii=False)
        prompt_text = registry().render(
            "rewrite_question",
            version=self._prompt_version,
            question=q,
            conversation=conv_json,
        )
        raw = self._chat_fn(
            [{"role": "user", "content": prompt_text}],
            DETERMINISTIC,
        )
        data = _parse_json_obj(raw)
        rewritten = str(data.get("rewritten") or q).strip() or q
        symbol_raw = data.get("symbol")
        symbol = (
            str(symbol_raw).strip().upper()
            if symbol_raw not in (None, "", "null")
            else None
        )
        llm_syms: list[str] = []
        raw_syms = data.get("symbols")
        if isinstance(raw_syms, list):
            for s in raw_syms:
                if s not in (None, "", "null"):
                    llm_syms.append(str(s).strip().upper())
        intent = str(data.get("intent") or "price_lookup").strip().lower()
        if intent not in _ALLOWED_INTENTS:
            intent = "price_lookup"
        # Heuristic bổ sung: LLM hay chỉ trả 1 mã dù câu hỏi so sánh nhiều mã.
        symbol, symbols = _normalize_symbols(
            primary=symbol,
            from_text=_extract_symbols(f"{q} {rewritten}"),
            from_llm=llm_syms,
        )
        # Đại từ / follow-up không có ticker → lấy mã từ conversation.
        symbol, symbols = _apply_memory_symbol(
            q, symbol=symbol, symbols=symbols, conversation=conversation
        )
        symbol, symbols = _normalize_symbols(primary=symbol, from_text=symbols)
        rewritten = _ground_rewritten(q, symbols, rewritten)
        # Đa mã / từ khóa so sánh → explain (price+news+eval).
        blob = f"{q} {rewritten}".lower()
        if len(symbols) > 1 or any(h in blob for h in _EXPLAIN_HINTS):
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
    """LLM routing qua registry `supervisor_routing`."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
        self._prompt_version = prompt_version

    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        prompt_text = registry().render(
            "supervisor_routing",
            version=self._prompt_version,
            rewritten_question=rewritten.rewritten or rewritten.original,
            symbol=rewritten.symbol or "",
            intent=rewritten.intent or "price_lookup",
        )
        raw = self._chat_fn(
            [{"role": "user", "content": prompt_text}],
            DETERMINISTIC,
        )
        data = _parse_json_obj(raw)
        agents_raw = data.get("agents_to_call") or []
        if not isinstance(agents_raw, list):
            agents_raw = []
        agents: list[str] = []
        for a in agents_raw:
            name = str(a).strip().lower()
            if name in _ALLOWED_AGENTS and name not in agents:
                agents.append(name)
        if not agents:
            agents = ["price"]
        reason = str(data.get("reason") or "").strip() or "llm routing"
        return RoutingDecision(
            route=rewritten.intent or "price_lookup",
            reason=reason,
            agents_to_call=agents,
        )


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_REWRITE_FACTORY: Callable[[], RewriteBrain] = LlmRewriteBrain
_DEFAULT_SUPERVISOR_FACTORY: Callable[[], SupervisorBrain] = LlmSupervisorBrain


def rewrite_question(
    question: str,
    conversation: list[dict],
    *,
    brain: RewriteBrain | None = None,
) -> RewrittenQuestion:
    rewriter = brain or _DEFAULT_REWRITE_FACTORY()
    try:
        return rewriter.rewrite(question, conversation)
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
) -> RoutingDecision:
    supervisor = brain or _DEFAULT_SUPERVISOR_FACTORY()
    try:
        return supervisor.route(rewritten)
    except Exception as exc:  # noqa: BLE001
        return RoutingDecision(
            route="price_lookup",
            reason=f"supervisor lỗi, fallback price: {exc}",
            agents_to_call=["price"],
        )
