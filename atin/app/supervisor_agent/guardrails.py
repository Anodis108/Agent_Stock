"""Guardrails hub — injection/toxic chặn cứng, topic scope trả lời lịch sự,
output kiểm tra độ dài/số liệu/PII trước khi trả user."""

from __future__ import annotations

from app.guardrails.checks import check_input, check_output, redact_pii

STAT_KEYWORDS = frozenset(
    {
        "khu vực",
        "ra vào",
        "ra/vào",
        "lượt vào",
        "lượt ra",
        "thống kê",
        "báo cáo",
        "bao nhiêu người",
        "số lượt",
        "cổng",
        "nhân viên",
        "khu a",
        "khu b",
    }
)

OUT_OF_SCOPE_REPLY = (
    "Xin lỗi, tôi chỉ hỗ trợ thống kê lượt ra/vào khu vực từ dữ liệu hiện có — "
    "câu hỏi này nằm ngoài phạm vi đó. Hãy hỏi ví dụ: "
    '"Từ 3h đến 4h chiều hôm nay có bao nhiêu người vào Khu A?".'
)


def in_scope(question: str) -> bool:
    low = question.lower()
    return any(k in low for k in STAT_KEYWORDS)


def evidence_snippets(state: dict) -> list[str]:
    bits = [str(state.get("question") or "")]
    stat = state.get("stat")
    if stat is not None:
        bits.append(str(stat.detail or ""))
        query = getattr(stat, "query", None)
        if query is not None:
            bits.append(str(query.row_count))
            for row in query.rows[:50]:
                bits.append(" ".join(str(v) for v in row))
    return [b for b in bits if b.strip()]


def guardrail_input(state: dict) -> dict:
    """Injection/toxic raise (nguy hại thật). Ngoài phạm vi KHÔNG raise —
    trả lời lịch sự, đánh dấu out_of_scope để hub bỏ qua stat_agent."""
    question = str(state.get("question") or "").strip()
    check_input(question)
    if not in_scope(question):
        from app.supervisor_agent.schemas import Agent_Output

        return {
            "out_of_scope": True,
            "question": question,
            "output": Agent_Output(question=question, answer=OUT_OF_SCOPE_REPLY),
        }
    safe = redact_pii(question)
    return {"question": safe} if safe != question else {}


def guardrail_output(state: dict) -> dict:
    output = state.get("output")
    raw = getattr(output, "answer", None) or ""
    result = check_output(raw, evidence_snippets(state))
    updates: dict = {"output_issues": result.issues}
    if output is not None and result.answer != raw and hasattr(output, "model_copy"):
        updates["output"] = output.model_copy(update={"answer": result.answer})
    return updates
