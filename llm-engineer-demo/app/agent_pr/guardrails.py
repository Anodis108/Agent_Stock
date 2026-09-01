"""Guardrails agent_pr — Class 7 phần 3, gắn lên hub Hierarchical Coordinator.

Ba lớp (slide 21–28), tái sử dụng `app.guardrails`:
  Input     — injection regex (+ LLM tuỳ cấu hình), PII redact, topic cổ phiếu VN, toxic.
  Processing — bound_messages / bound_system trên rewrite, plan, ReAct worker.
  Output    — length, tiếng Việt, số liệu vs evidence, PII, toxicity/moderation.

Hub: START → guardrail_input → rewrite → … → reply → guardrail_output → store.
Worker không thêm node guardrail — wrap system prompt (lớp processing) + output hub.
"""

from __future__ import annotations

from app.agent_pr.context import set_history
from app.guardrails.checks import OutputCheckResult, check_output, prepare_input
from app.monitoring.tracing import trace_step

STOCK_KEYWORDS = frozenset(
    {
        "cổ phiếu",
        "chứng khoán",
        "niêm yết",
        "hose",
        "hnx",
        "upcom",
        "cafef",
        "vnstock",
        "vnindex",
        "vn-index",
        "mã",
        "giá",
        "tin tức",
        "tin",
        "phiên",
        "khớp lệnh",
        "biến động",
        "phân tích",
        "bluechip",
        "ticker",
        "stock",
    }
)

_STOCK_FALLBACK = (
    "Xin lỗi, tôi chưa đủ dữ liệu giá/tin đáng tin để trả lời. "
    "Hãy hỏi lại một mã niêm yết cụ thể (vd. HPG, FPT)."
)
_STOCK_DISCLAIMER = (
    " (Lưu ý: một số số liệu chưa khớp đúng nguồn giá/tin/DB trong lượt này.)"
)


def _history_blob(state: dict) -> str:
    bits: list[str] = []
    for msg in list(state.get("history") or [])[-8:]:
        if isinstance(msg, dict):
            bits.append(str(msg.get("content") or ""))
        else:
            bits.append(str(getattr(msg, "content", "") or ""))
    return " ".join(bits)


def evidence_snippets(state: dict) -> list[str]:
    """Nguồn groundedness — giá/tin/eval/DB, không gồm draft (tránh tự xác nhận)."""
    bits = [
        str(state.get("question") or ""),
        str(state.get("rewritten_question") or ""),
        str(state.get("symbol") or ""),
    ]
    price = state.get("price")
    if price:
        bits.append(
            f"{price.symbol} {price.last} {price.prev_close} {price.pct_change} {price.trading_date}"
        )
    news = state.get("news")
    if news:
        for item in news.articles or []:
            bits.append(f"{item.title} {item.url} {item.publish_time}")
    ev = state.get("eval")
    if ev:
        bits.append(
            f"{ev.detail} {ev.negative_count} {ev.positive_count} {ev.neutral_count}"
        )
        for item in ev.items or []:
            bits.append(f"{item.title} {item.sentiment}")
    db = state.get("db")
    if db:
        bits.append(str(db.detail or ""))
        for row in (db.price_history or [])[:30]:
            bits.append(f"{row.trading_date} {row.close}")
        for item in (db.saved_news or [])[:20]:
            bits.append(f"{item.title} {item.url}")
    return [b for b in bits if b.strip()]


def sanitize_stock_answer(answer: str, state: dict) -> OutputCheckResult:
    """Output guard cổ phiếu: PII + VI + toxic; số lạ → disclaimer, không nuốt cả câu."""
    return check_output(
        answer,
        evidence_snippets(state),
        redact=True,
        require_vietnamese=True,
        check_toxicity=True,
        unverified_mode="disclaimer",
        fallback=_STOCK_FALLBACK,
        disclaimer=_STOCK_DISCLAIMER,
    )


def guardrail_input(state: dict) -> dict:
    """Chặn injection/toxic/ngoài phạm vi; che PII trước rewrite/LLM."""
    question = str(state.get("question") or "").strip()
    extra = " ".join(
        [
            str(state.get("symbol") or ""),
            _history_blob(state),
        ]
    )
    with trace_step(state.get("_trace_span"), "guardrail_input", input=question):
        safe = prepare_input(
            question,
            redact=True,
            topic_keywords=STOCK_KEYWORDS,
            extra_scope=extra,
        )
    out: dict = {}
    if safe != question:
        out["question"] = safe
        out["trace"] = list(state.get("trace") or []) + ["Guardrail: đã che PII trong câu hỏi"]
    return out


def guardrail_output(state: dict) -> dict:
    """Lọc câu trả lời cuối — không raise; ghi đè answer + history assistant."""
    output = state.get("output")
    raw = getattr(output, "answer", None) or ""
    with trace_step(state.get("_trace_span"), "guardrail_output", input=raw) as t:
        result = sanitize_stock_answer(raw, state)
        t["output"] = {"answer": result.answer, "issues": result.issues}
    updates: dict = {"output_issues": result.issues}
    if result.issues:
        updates["trace"] = list(state.get("trace") or []) + [
            "Guardrail output: " + ", ".join(result.issues)
        ]
    if output is not None and result.answer != raw and hasattr(output, "model_copy"):
        updates["output"] = output.model_copy(update={"answer": result.answer})
        history = list(state.get("history") or [])
        if history and (
            (isinstance(history[-1], dict) and history[-1].get("role") == "assistant")
            or getattr(history[-1], "type", None) == "ai"
        ):
            history = history[:-1] + [{"role": "assistant", "content": result.answer}]
            updates["history"] = set_history(history)
    return updates
