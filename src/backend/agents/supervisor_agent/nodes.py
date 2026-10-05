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

from backend.agents.supervisor_agent.schemas import (
    RewriteOutput,
    SupervisorOutput,
)
from backend.domain.entities import RoutingDecision
from backend.infra.llm.params import DETERMINISTIC
from backend.infra.llm.prompt_registry import registry
from backend.infra.llm.structured import call_llm_structured
from backend.infra.storage.long_term_memory import (
    recall_long_term,
    save_to_long_term,
)
from backend.shared.schemas import MemoryFact

_MA_SYMBOL_RE = re.compile(r"(?:mã|ma|cổ phiếu|co phieu|cp)\s+([A-Za-z]{3,4})\b", re.IGNORECASE)
_INDICATOR_PATTERN = re.compile(
    r"(?:chỉ báo|chi bao|chỉ số|chi so|đường|duong|tín hiệu|tin hieu)\s+([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_TICKER_RE = re.compile(r"\b([A-Z]{3})\b")
_TICKER_STOPWORDS = frozenset(
    {
        # Từ tiếng Anh phổ biến
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "WHY", "HOW", "WHO", "OUT",
        # Chỉ báo kỹ thuật & thuật ngữ tài chính (Technical Indicators & Financial Metrics)
        "RSI", "SMA", "EMA", "WMA", "MAC", "MACD", "ATR", "ADX", "CCI", "MFI", "OBV", "VOL",
        "EPS", "ROE", "ROA", "NAV", "VND", "USD", "EUR", "VNI", "VNX", "HNX", "HSX", "UPC", "ETF",
        "ATC", "ATO",
        # Từ tiếng Việt 3 chữ cái phổ biến (tránh nhận nhầm khi text.upper())
        "QUA",  # «qua» / «quá» (qua các chỉ báo, hôm qua)
        "CHI",  # «chỉ» (chỉ báo, chỉ số)
        "BAO",  # «bao» / «báo» (bao nhiêu, chỉ báo, bài báo)
        "NEN",  # «nên» / «nến» (nên mua, biểu đồ nến)
        "TRA",  # «tra» (kiểm tra, tra cứu)
        "KIE",  # «kiểm»
        "DANH", # «danh» (danh mục, danh sách)
        "XIN",  # «xin» (xin vui lòng, xin chào)
        "VUI",  # «vui» (xin vui lòng)
        "LONG", # «lòng»
        "LUC",  # «lúc»
        "KHI",  # «khi»
        "BAN",  # «bán» / «bản»
        "MUA",  # «mua»
        "DAY",  # «đây» / «đáy»
        "DIN",  # «đỉnh»
        "XEM",  # «xem»
        "HOI",  # «hỏi»
        "DAN",  # «dẫn» / «danh»
        "PHU",  # «phụ»
        "TOP",  # «top»
        "BOT",  # «bot»
        "APP",  # «app»
        "WEB",  # «web»
        "API",  # «api»
        "VON",  # «vốn»
        "LAI",  # «lãi» / «lại»
        "QUY",  # «quỹ» / «quý»
        "TON",  # «tồn»
        "DON",  # «đơn»
        "LEN",  # «lên»
        "DOC",  # «đọc»
        "LAM",  # «làm»
        "CAN",  # «cần»
        "CON",  # «còn» / «con»
        "HON",  # «hơn»
        "GAP",  # «gặp» / «gấp»
        "BAT",  # «bắt»
        "DAT",  # «đạt» / «đặt»
        "GIO",  # «giờ»
        "TAM",  # «tạm» / «tầm»
        "MUC",  # «mức» / «mục»
        "BAI",  # «bài»
        "GIA",  # «giá»
        "TAI",  # «tại»
        "TIA",  # typo «tịa»
        "HIEN", # «hiện»
        "HIE",
        "TOI",  # «tôi»
        "THE",  # «thế» / «thể»
        "SAO",  # «sao»
        "NAY",  # «này»
        "ROI",  # «rồi»
        "CUA",  # «của»
        "NHE",  # «nhé»
        "VAY",  # «vậy»
        "TIN",  # «tin»
        "TUC",  # «tức»
        "MOT",  # «một»
        "HAY",  # «hay»
        "CHO",  # «cho»
        "CAC",  # «các»
        "DEN",  # «đến»
        "VOI",  # «với»
        "NUA",  # «nữa»
        "RAT",  # «rất»
        "HOM",  # «hôm»
        "NAO",  # «nào»
        "NGAY", # «ngày»
        "TUAN", # «tuần»
        "THANG",# «tháng»
        "NAM",  # «năm»
    }
)
_REF_PREV_RE = re.compile(
    r"("
    r"mã đó|ma do|mã này|ma nay|"
    r"còn mã|con ma|mã vừa|ma vua|cùng mã|cung ma|"
    r"cổ phiếu đó|co phieu do|cổ phiếu này|co phieu nay|"
    r"cổ phiếu vừa rồi|co phieu vua roi|mã vừa rồi|ma vua roi|mã trên|ma tren|mã trước|ma truoc|"
    r"con này|con nay|con đó|con do|"
    r"\bnó\b|\bno\b|em đó|em do|em này|em nay"
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
    "phân tích",
    "phan tich",
    "kỹ thuật",
    "ky thuat",
    "chỉ báo",
    "chi bao",
    "xu hướng",
    "xu huong",
    "đánh giá",
    "danh gia",
    "nhận định",
    "nhan dinh",
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
_CHART_PHRASES = (
    "vẽ biểu đồ",
    "ve bieu do",
    "biểu đồ giá",
    "bieu do gia",
    "biểu đồ",
    "bieu do",
    "đồ thị giá",
    "do thi gia",
    "đồ thị",
    "do thi",
    "so sánh chart",
    "so sanh chart",
    "chart",
    "nến",
    "nen",
    "candlestick",
    "candle",
)
_FOLLOWUP_RE = re.compile(
    r"("
    r"tại sao|tai sao|vì sao|vi sao|nguyên nhân|nguyen nhan|lý do|ly do|"
    r"sao lại|sao lai|sao thế|sao the|sao vậy|sao vay|sao thế nhỉ|sao the nhi|"
    r"thế nào|the nao|ra sao|sao rồi|sao roi|như nào|nhu nao|thế nào rồi|the nao roi|"
    r"giá|gia|giảm|giam|tăng|tang|biến động|bien dong|rơi|sụt|lên|xuống|"
    r"tin tức|tin tuc|tin gì|tin moi|tin mới|bài báo|bai bao|"
    r"biểu đồ|bieu do|đồ thị|do thi|chart"
    r")",
    re.IGNORECASE,
)
_PORTFOLIO_PHRASES = (
    "danh mục",
    "danh muc",
    "portfolio",
    "lãi lỗ",
    "lai lo",
    "lãi hay lỗ",
    "lai hay lo",
    "lời lỗ",
    "loi lo",
    "lời hay lỗ",
    "loi hay lo",
    "tổng giá trị nav",
    "tong gia tri nav",
    "giá trị nav",
    "gia tri nav",
    "tổng nav",
    "tong nav",
    "hiệu suất p&l",
    "hieu suat p&l",
    "p&l",
    "pnl",
    "nắm giữ",
    "nam giu",
    "vị thế",
    "vi the",
)
_WATCHLIST_PHRASES = (
    "watchlist",
    "danh sách theo dõi",
    "danh sach theo doi",
    "mã theo dõi",
    "ma theo doi",
    "danh mục theo dõi",
    "danh muc theo doi",
    "các mã trong danh sách theo dõi",
    "cac ma trong danh sach theo doi",
    "ngưỡng cảnh báo biến động",
    "nguong canh bao bien dong",
    "ngưỡng cảnh báo",
    "nguong canh bao",
    "danh sách cảnh báo",
    "danh sach canh bao",
)


def _has_portfolio_intent(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in _PORTFOLIO_PHRASES)


def _has_watchlist_intent(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in _WATCHLIST_PHRASES)


_ALLOWED_AGENTS = frozenset({"price", "news", "eval", "diagram", "chart", "portfolio_watch"})
_ALLOWED_INTENTS = frozenset({"price_lookup", "news_lookup", "explain", "diagram", "chart", "portfolio", "watchlist"})


@dataclass(slots=True)
class RewrittenQuestion:
    original: str
    rewritten: str
    symbol: str | None
    intent: str  # price_lookup | news_lookup | explain
    # So sánh đa mã (VNM+HPG…); symbol = mã chính (phần tử đầu).
    symbols: list[str] = field(default_factory=list)
    sub_questions: list[str] = field(default_factory=list)


class RewriteBrain(Protocol):
    def rewrite(
        self, question: str, conversation: list[dict]
    ) -> RewrittenQuestion:
        ...


class SupervisorBrain(Protocol):
    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        ...


def _extract_symbols(text: str) -> list[str]:
    """Lấy mọi mã 3-4 chữ cái (theo thứ tự xuất hiện, loại bỏ stopwords và chỉ báo kỹ thuật, không trùng)."""
    if not text:
        return []
    indicator_terms = {m.group(1).strip().upper() for m in _INDICATOR_PATTERN.finditer(text)}
    out: list[str] = []
    for ma in _MA_SYMBOL_RE.finditer(text):
        sym = ma.group(1).strip().upper()
        if sym and sym not in _TICKER_STOPWORDS and sym not in indicator_terms and sym not in out:
            out.append(sym)
    for match in _TICKER_RE.finditer(text.upper()):
        sym = match.group(1)
        if sym not in _TICKER_STOPWORDS and sym not in indicator_terms and sym not in out:
            out.append(sym)
    return out


def _extract_symbol(text: str) -> str | None:
    syms = _extract_symbols(text)
    return syms[0] if syms else None


def _symbols_from_original_question(q: str) -> list[str]:
    """Mã trích từ câu hỏi gốc — không dùng rewritten (tránh «xin vui» → XIN/VUI)."""
    return _extract_symbols(q)


def _restrict_symbols_to_original(q: str, symbols: list[str]) -> list[str]:
    """Giữ mã có trong câu gốc; nếu gốc không có mã thì giữ nguyên (follow-up/memory)."""
    q_syms = _symbols_from_original_question(q)
    if not q_syms:
        return symbols
    allowed = set(q_syms)
    return [s for s in symbols if s in allowed]


def _normalize_symbols(
    *,
    primary: str | None,
    from_text: list[str],
    from_llm: list[str] | None = None,
) -> tuple[str | None, list[str]]:
    text_set = {(s or "").strip().upper() for s in from_text if (s or "").strip()}
    llm_syms = list(from_llm or [])
    # Bỏ mã LLM bịa không xuất hiện trong câu hỏi khi đã trích được mã từ text.
    if text_set and llm_syms:
        llm_syms = [
            s for s in llm_syms if (s or "").strip().upper() in text_set
        ]
    ordered: list[str] = []
    for sym in llm_syms + ([primary] if primary else []) + list(from_text):
        s = (sym or "").strip().upper()
        if s and s not in ordered:
            ordered.append(s)
    return (ordered[0] if ordered else None), ordered


def _symbol_from_conversation(conversation: list[dict]) -> str | None:
    """Lấy mã gần nhất từ hội thoại (ưu tiên user turn gần nhất, sau đó assistant)."""
    # 1. Quét các lượt hỏi của user từ gần nhất về trước
    for turn in reversed(conversation or []):
        if turn.get("role") == "user":
            content = str(turn.get("content") or "")
            sym = _extract_symbol(content)
            if sym:
                return sym
    # 2. Quét các lượt trả lời của assistant từ gần nhất về trước
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


def _has_chart_intent(lower: str) -> bool:
    return any(h in lower for h in _CHART_PHRASES)


def _is_actionless_followup(q: str) -> bool:
    """Kiểm tra câu hỏi tỉnh lược hành động (chỉ nêu mã hoặc hỏi lửng lơ: 'Còn VNM thì sao?', 'HPG?', 'Vậy còn HPG?')."""
    q_clean = (q or "").strip()
    if not q_clean:
        return False
    q_lower = q_clean.lower()
    has_explicit_action = (
        _has_chart_intent(q_lower)
        or _has_diagram_intent(q_lower)
        or any(h in q_lower for h in _EXPLAIN_HINTS)
        or _has_news_intent(q_lower)
        or _has_portfolio_intent(q_lower)
        or _has_watchlist_intent(q_lower)
        or any(k in q_lower for k in ("giá bao nhiêu", "gia bao nhieu", "đóng cửa", "dong cua", "khớp lệnh", "khop lenh"))
    )
    if has_explicit_action:
        return False

    followup_patterns = (
        "thì sao", "thi sao", "thế nào", "the nao", "sao rồi", "sao roi", "ra sao",
        "còn", "con", "thế còn", "the con", "vậy còn", "vay con", "với", "voi",
        "sang", "qua", "như nào", "nhu nao", "thế", "the",
    )
    if any(p in q_lower for p in followup_patterns):
        return True

    words = re.findall(r"\w+", q_lower)
    syms = _extract_symbols(q)
    if len(words) <= 4 and syms:
        return True

    return False


def _get_prev_intent_and_action(conversation: list[dict]) -> tuple[str | None, str | None]:
    """Lấy intent và hành động của lượt trao đổi liền trước trong hội thoại."""
    for turn in reversed(conversation or []):
        content = str(turn.get("content") or "").strip()
        c_lower = content.lower()
        if turn.get("role") == "user":
            if _has_chart_intent(c_lower):
                return "chart", "Vẽ biểu đồ giá"
            if _has_diagram_intent(c_lower):
                return "diagram", "Vẽ sơ đồ"
            if _has_watchlist_intent(c_lower):
                return "watchlist", "Theo dõi danh mục"
            if _has_portfolio_intent(c_lower):
                return "portfolio", "Tra cứu danh mục"
            if any(h in c_lower for h in _EXPLAIN_HINTS):
                return "explain", "Giải thích biến động"
            if _has_news_intent(c_lower):
                return "news_lookup", "Tra cứu tin tức"
            if any(k in c_lower for k in ("giá", "gia")):
                return "price_lookup", "Tra cứu giá"
        elif turn.get("role") == "assistant":
            if turn.get("chart_path") or "![biểu đồ" in c_lower or "đã tạo biểu đồ" in c_lower:
                return "chart", "Vẽ biểu đồ giá"
            if "### 💼 báo cáo hiệu suất danh mục" in c_lower or "tổng nav" in c_lower:
                return "portfolio", "Tra cứu danh mục"
    return None, None



def _decompose_query(
    question: str,
    rewritten: str,
    symbols: list[str],
    intent: str,
    llm_sub_questions: list[str] | None = None,
) -> list[str]:
    """Phân rã câu hỏi phức tạp / đa mã thành các sub-questions độc lập (Query Decomposition).
    
    Hỗ trợ cơ chế Fallback an toàn (Task 7.3): Nếu câu hỏi không thể phân rã hoặc gặp lỗi,
    hệ thống tự động quay về chính câu hỏi gốc/câu viết lại để tiếp tục chu trình xử lý.
    """
    q_main = (rewritten or question or "").strip()
    try:
        if llm_sub_questions and len(llm_sub_questions) > 1:
            return [sq.strip() for sq in llm_sub_questions if sq.strip()]

        combined_text = f"{question} {rewritten}".lower()
        has_news = _has_news_intent(combined_text) or "tin tức" in combined_text or "tin" in combined_text
        has_price = any(k in combined_text for k in ("giá", "gia", "thị giá", "biến động", "đóng cửa")) or intent == "price_lookup"

        # 1. Câu hỏi so sánh hoặc chứa nhiều mã cổ phiếu (DEC-01, DEC-04)
        if len(symbols) > 1:
            sub_qs: list[str] = []
            q_lower = (question or "").lower()
            is_comparison = any(
                k in combined_text
                for k in ("so sánh", "so sanh", "so với", "so voi", "khác nhau", "vs", "versus")
            )
            asks_both_price_and_news = (
                (has_news and has_price and any(k in q_lower for k in ("tin", "tin tức", "sự kiện", "bài báo")))
                or (is_comparison and any(k in q_lower for k in ("tin", "tin tức", "sự kiện", "bài báo")))
                or ("so sánh với" in q_lower and has_news)
            )
            if asks_both_price_and_news:
                for s in symbols:
                    sub_qs.append(f"Giá và biến động gần nhất của cổ phiếu {s} là bao nhiêu?")
                for s in symbols:
                    sub_qs.append(f"Tin tức và sự kiện gần đây về cổ phiếu {s} là gì?")
                return sub_qs
            elif is_comparison or len(symbols) == 2:
                # Tách câu hỏi so sánh đa mã (VD: FPT vs HPG hoặc So sánh FPT và HPG) thành 2 sub-queries độc lập
                for s in symbols:
                    sub_qs.append(f"Giá và biến động gần nhất của cổ phiếu {s} là bao nhiêu?")
                return sub_qs
            elif intent == "chart":
                for s in symbols:
                    sub_qs.append(f"Vẽ biểu đồ kỹ thuật cho cổ phiếu {s}")
                return sub_qs
            elif intent == "news_lookup" or has_news:
                for s in symbols:
                    sub_qs.append(f"Tin tức mới nhất về cổ phiếu {s}")
                return sub_qs
            else:
                for s in symbols:
                    sub_qs.append(f"Giá cổ phiếu {s} hôm nay là bao nhiêu?")
                return sub_qs

        # 2. Câu hỏi đa ý trên 1 mã (DEC-02: vừa hỏi giá vừa hỏi tin tức hoặc nguyên nhân)
        if len(symbols) == 1:
            sym = symbols[0]
            has_explain_cause = any(
                h in combined_text
                for h in ("tại sao", "tai sao", "vì sao", "vi sao", "lý do", "ly do", "nguyên nhân", "nguyen nhan", "giải thích", "giai thich")
            )
            if (has_price and has_news) or (has_price and has_explain_cause) or (intent == "explain" and has_explain_cause):
                return [
                    f"Giá và biến động hiện tại của cổ phiếu {sym} là bao nhiêu?",
                    f"Tin tức và nguyên nhân tác động đến biến động giá cổ phiếu {sym} gần đây là gì?",
                ]

        if intent == "chart" and symbols:
            return [f"Vẽ biểu đồ kỹ thuật cho cổ phiếu {s}" for s in symbols]

        if intent == "diagram":
            return ["Vẽ sơ đồ luồng hệ thống"]

        if llm_sub_questions and len(llm_sub_questions) == 1 and llm_sub_questions[0].strip():
            return [llm_sub_questions[0].strip()]

        # 3. Câu hỏi đơn giản hoặc không thể phân tách thêm (DEC-03)
        return [q_main] if q_main else [question.strip()]
    except Exception as exc:
        _logger.warning("Lỗi phân rã câu hỏi: %s. Fallback an toàn về câu hỏi gốc.", exc)
        return [q_main] if q_main else [question.strip()]


def _needs_memory_symbol(question: str, symbol: str | None) -> bool:
    """Xác định câu hỏi có cần bổ sung mã cổ phiếu từ bộ nhớ hội thoại không."""
    q_lower = (question or "").lower()
    # Đại từ luôn resolve từ hội thoại (kể cả khi extract nhầm ticker).
    if _REF_PREV_RE.search(question):
        return True
    # Câu hỏi so sánh với mã mới nhưng kế thừa mã trước ("So sánh với HPG...")
    if re.search(r"\b(?:so sánh với|so sanh voi|so với|so voi|còn\s+\w+\s+thì\s+sao\s+so\s+với)\b", q_lower):
        return True
    if symbol is not None:
        return False
    # Câu follow-up không có ticker → lấy symbol từ hội thoại nếu chứa từ khóa follow-up hoặc giải thích/tin tức/chart
    is_followup = (
        bool(_FOLLOWUP_RE.search(question))
        or any(h in q_lower for h in _EXPLAIN_HINTS)
        or _has_news_intent(q_lower)
        or _has_chart_intent(q_lower)
        or _has_diagram_intent(q_lower)
    )
    return is_followup and len(question.strip()) < 300


class HeuristicRewriteBrain:
    """Chuẩn hoá câu hỏi + suy ra symbol (kể cả tham chiếu 'mã đó' hoặc câu hỏi nối tiếp 'tại sao lại giảm')."""

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
        if _has_chart_intent(lower):
            intent = "chart"
        elif _has_diagram_intent(lower):
            intent = "diagram"
        elif _has_watchlist_intent(lower):
            intent = "watchlist"
        elif _has_portfolio_intent(lower):
            intent = "portfolio"
        elif any(h in lower for h in _EXPLAIN_HINTS):
            intent = "explain"
        elif _has_news_intent(lower):
            intent = "news_lookup"
        elif _is_actionless_followup(q):
            prev_intent, _ = _get_prev_intent_and_action(conversation)
            if prev_intent:
                intent = prev_intent

        symbol, symbols = _normalize_symbols(primary=symbol, from_text=symbols)
        if intent in ("portfolio", "watchlist"):
            has_explicit_ticker = any(k in lower for k in ("mã", "ma", "cổ phiếu", "co phieu", "cp"))
            if not has_explicit_ticker and symbols:
                symbol = None
                symbols = []

        # Nếu câu hỏi dạng so sánh hoặc nguyên nhân 'tại sao lại giảm/tăng' không có ticker, chuẩn hoá câu hỏi tự nhiên
        rewritten_candidate = q
        if len(symbols) >= 2 and re.search(r"\b(?:so sánh với|so sanh voi|so với|so voi)\b", lower):
            rewritten_candidate = f"So sánh cổ phiếu {symbols[0]} và {symbols[1]} về biến động giá và tin tức gần đây."
        elif len(symbols) >= 2 and re.search(r"\b(?:vs|versus)\b", lower):
            rewritten_candidate = f"So sánh cổ phiếu {symbols[0]} và {symbols[1]}."
        elif _is_actionless_followup(q):
            prev_intent, prev_action = _get_prev_intent_and_action(conversation)
            if prev_action and symbol:
                rewritten_candidate = f"{prev_action} cổ phiếu {symbol}."
        elif symbol and symbol not in _extract_symbols(q):
            if re.search(
                r"(?:tại sao|tai sao|vì sao|vi sao|sao lại|sao lai|lý do|ly do|nguyên nhân|nguyen nhan)\s+(?:lại\s+)?giảm",
                lower,
            ):
                rewritten_candidate = f"Tại sao giá cổ phiếu {symbol} lại giảm hôm nay?"
            elif re.search(
                r"(?:tại sao|tai sao|vì sao|vi sao|sao lại|sao lai|lý do|ly do|nguyên nhân|nguyen nhan)\s+(?:lại\s+)?tăng",
                lower,
            ):
                rewritten_candidate = f"Tại sao giá cổ phiếu {symbol} lại tăng hôm nay?"
            elif _has_chart_intent(lower):
                rewritten_candidate = f"{q} của cổ phiếu {symbol}"

        rewritten = _ground_rewritten(q, symbols, rewritten_candidate)
        sub_questions = _decompose_query(
            question=q,
            rewritten=rewritten,
            symbols=symbols,
            intent=intent,
        )
        return RewrittenQuestion(
            original=q,
            rewritten=rewritten,
            symbol=symbol,
            intent=intent,
            symbols=symbols,
            sub_questions=sub_questions,
        )


class HeuristicSupervisorBrain:
    """Routing heuristic: price-only / +news / +eval theo intent và sub_questions."""

    def route(self, rewritten: RewrittenQuestion) -> RoutingDecision:
        intent = rewritten.intent or "price_lookup"
        if intent == "chart":
            if len(rewritten.symbols) > 1:
                agents = ["price", "chart", "eval"]
                reason = "yêu cầu vẽ biểu đồ so sánh → price+chart+eval"
            else:
                agents = ["price", "chart"]
                reason = "yêu cầu vẽ biểu đồ giá → price+chart"
        elif intent == "diagram":
            agents = ["diagram"]
            reason = "yêu cầu vẽ sơ đồ → diagram_agent"
        elif intent == "explain":
            agents = ["price", "news", "eval"]
            reason = "câu hỏi cần giải thích/so sánh → price+news+eval"
        elif intent == "news_lookup":
            agents = ["price", "news"]
            reason = "câu hỏi về tin → price+news"
        elif intent == "portfolio":
            agents = ["portfolio_watch"]
            reason = "truy vấn danh mục đầu tư (P&L/NAV) → portfolio_watch_agent"
        elif intent == "watchlist":
            agents = ["portfolio_watch"]
            reason = "truy vấn danh sách theo dõi (Watchlist) → portfolio_watch_agent"
        else:
            agents = ["price"]
            reason = "tra cứu giá → chỉ PriceAgent"

        # Quét qua toàn bộ sub_questions để không bỏ sót worker nào (DEC-05)
        for sq in (rewritten.sub_questions or []):
            sq_lower = sq.lower()
            if any(k in sq_lower for k in ("tin", "tin tức", "sự kiện", "báo chí")) and "news" not in agents:
                agents.append("news")
            if any(k in sq_lower for k in ("giá", "thị giá", "biến động", "đóng cửa")) and "price" not in agents:
                agents.insert(0, "price")
            if any(k in sq_lower for k in ("nguyên nhân", "tại sao", "vì sao", "lý do", "đánh giá", "rủi ro", "so sánh")) and "eval" not in agents:
                agents.append("eval")
            if any(k in sq_lower for k in ("biểu đồ", "đồ thị", "chart")) and "chart" not in agents:
                agents.append("chart")
            if any(k in sq_lower for k in ("sơ đồ", "lưu đồ", "diagram")) and "diagram" not in agents:
                agents.append("diagram")

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

        from backend.infra.cache.exact import llm_cache_scope

        try:
            with llm_cache_scope(
                prompt_name="rewrite_question",
                prompt_version=self._prompt_version,
                normalized_question=q,
            ):
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
        symbols = _restrict_symbols_to_original(q, symbols)
        symbol = symbols[0] if symbols else symbol
        # Đại từ / follow-up không có ticker → lấy mã từ conversation hoặc long-term memory.
        symbol, symbols = _apply_memory_symbol(
            q,
            symbol=symbol,
            symbols=symbols,
            conversation=conversation,
            memories=memories,
        )
        # Action inheritance: nếu câu hỏi tỉnh lược mã mới không có action, kế thừa action lượt trước
        if _is_actionless_followup(q):
            prev_intent, prev_action = _get_prev_intent_and_action(conversation)
            if prev_intent:
                intent = prev_intent
                if prev_action and symbol:
                    rewritten_lower = rewritten.lower()
                    needs_rewrite_override = (
                        (prev_intent == "chart" and not _has_chart_intent(rewritten_lower))
                        or (prev_intent == "news_lookup" and not _has_news_intent(rewritten_lower))
                        or (prev_intent == "diagram" and not _has_diagram_intent(rewritten_lower))
                        or (prev_intent == "explain" and not any(h in rewritten_lower for h in _EXPLAIN_HINTS))
                        or any(k in rewritten_lower for k in ("thì sao", "như thế nào", "thông tin", "giá hiện tại", "giá cổ phiếu"))
                    )
                    if needs_rewrite_override:
                        rewritten = f"{prev_action} cổ phiếu {symbol}."
                        if hasattr(output, "sub_questions"):
                            output.sub_questions = [f"{prev_action} cổ phiếu {symbol}."]

        # Đa mã / từ khóa trực tiếp từ blob câu hỏi -> chart, diagram, explain
        blob = f"{q} {rewritten}".lower()
        if _has_chart_intent(blob):
            intent = "chart"
        elif _has_diagram_intent(blob):
            intent = "diagram"
        elif _has_watchlist_intent(blob):
            intent = "watchlist"
        elif _has_portfolio_intent(blob):
            intent = "portfolio"
        elif len(symbols) > 1 or any(h in blob for h in _EXPLAIN_HINTS):
            if intent == "price_lookup":
                intent = "explain"

        if intent in ("portfolio", "watchlist"):
            has_explicit_ticker = any(k in q.lower() for k in ("mã", "ma", "cổ phiếu", "co phieu", "cp"))
            if not has_explicit_ticker and symbols:
                symbol = None
                symbols = []

        symbol, symbols = _normalize_symbols(primary=symbol, from_text=symbols)
        rewritten = _ground_rewritten(q, symbols, rewritten)
        sub_questions = _decompose_query(
            question=q,
            rewritten=rewritten,
            symbols=symbols,
            intent=intent,
            llm_sub_questions=getattr(output, "sub_questions", None),
        )
        return RewrittenQuestion(
            original=q,
            rewritten=rewritten,
            symbol=symbol,
            intent=intent,
            symbols=symbols,
            sub_questions=sub_questions,
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

        from backend.infra.cache.exact import llm_cache_scope

        route_q = rewritten.rewritten or rewritten.original or ""
        try:
            with llm_cache_scope(
                prompt_name="supervisor_routing",
                prompt_version=self._prompt_version,
                normalized_question=route_q,
            ):
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
            if intent == "chart":
                fallback_agents = ["price", "chart", "eval"] if len(rewritten.symbols) > 1 else ["price", "chart"]
            elif intent == "diagram":
                fallback_agents = ["diagram"]
            elif intent == "explain":
                fallback_agents = ["price", "news", "eval"]
            elif intent == "news_lookup":
                fallback_agents = ["price", "news"]
            elif intent == "portfolio":
                fallback_agents = ["portfolio_watch"]
            elif intent == "watchlist":
                fallback_agents = ["portfolio_watch"]
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
        if rewritten.intent in ("portfolio", "watchlist"):
            agents = ["portfolio_watch"]
        elif rewritten.intent == "chart":
            if "chart" not in agents:
                agents.append("chart")
            if "price" not in agents:
                agents.insert(0, "price")

        # Quét qua sub_questions để không bỏ sót worker nào (DEC-05)
        for sq in (rewritten.sub_questions or []):
            sq_lower = sq.lower()
            if any(k in sq_lower for k in ("tin", "tin tức", "sự kiện", "báo chí")) and "news" not in agents:
                agents.append("news")
            if any(k in sq_lower for k in ("giá", "thị giá", "biến động", "đóng cửa")) and "price" not in agents:
                agents.insert(0, "price")
            if any(k in sq_lower for k in ("nguyên nhân", "tại sao", "vì sao", "lý do", "đánh giá", "rủi ro", "so sánh")) and "eval" not in agents:
                agents.append("eval")
            if any(k in sq_lower for k in ("biểu đồ", "đồ thị", "chart")) and "chart" not in agents:
                agents.append("chart")
            if any(k in sq_lower for k in ("sơ đồ", "lưu đồ", "diagram")) and "diagram" not in agents:
                agents.append("diagram")

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


from backend.infra.monitoring.tracing import agent_step

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
                "sub_questions": list(res.sub_questions or []),
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
            sub_questions=[q] if q else [],
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
        prompt_text = registry().render(
            "memory_fact",
            question=question or "",
            answer=answer or "",
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
