"""Pipeline orchestrator — nối guardrails + retrieval + prompt + LLM.

Đây là "xương sống" RAG. Ở Buổi 1, bước retrieve trả [] nên thực chất chỉ là
chatbot thuần LLM. Từ Buổi 5, chỉ cần retriever.retrieve() trả chunk thật là
toàn bộ pipeline thành RAG — KHÔNG phải sửa file này.

Luồng:
    guardrails.check_input(question)   — raise GuardrailViolation nếu injection
    → retrieve(query)
    → build_messages(q, ctx)
    → llm.chat / chat_stream / chat_parsed
    guardrails.check_output(answer, ctx) — chỉ ở answer() non-streaming; xem lý
                                            do trong docstring answer_stream().
"""

from __future__ import annotations

from collections.abc import Iterator

from src.chatbot.domain.service.guardrails.checks import check_input, check_output
from src.chatbot.infrastructure.llm import completion
from src.chatbot.domain.entities.params import GenerationParams
from src.chatbot.domain.service.monitoring.tracing import trace_answer, trace_stream
from src.chatbot.domain.entities.prompts.templates import build_messages
from src.chatbot.domain.service.retrieval.retriever import retrieve
from src.chatbot.domain.entities.schemas.domain import LegalAnswer

# Role prompting (Section 3): persona cụ thể, có quy tắc rõ ràng.
LEGAL_SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật doanh nghiệp Việt Nam.

Quy tắc:
- Trả lời chính xác, ngắn gọn, bằng tiếng Việt.
- Khi có TÀI LIỆU THAM KHẢO bên dưới, CHỈ trả lời dựa trên tài liệu đó và trích dẫn nguồn.
- Khi KHÔNG có tài liệu tham khảo, nói rõ rằng câu trả lời dựa trên hiểu biết chung
  và khuyến nghị người dùng kiểm chứng với văn bản luật chính thức.
- Luôn khuyên tham khảo luật sư cho các vụ việc cụ thể.
"""

def answer(question: str, params: GenerationParams | None = None) -> str:
    """Trả lời dạng text (non-streaming). Có đủ input + output guardrails."""
    check_input(question)
    with trace_answer("answer", question) as t:
        chunks = retrieve(question)  # Buổi 1: [] → trả lời thuần parametric knowledge
        messages = build_messages(question, LEGAL_SYSTEM_PROMPT, chunks)
        raw_answer = completion.chat(messages, params)

        result = check_output(raw_answer, [c.text for c in chunks])
        t["output"] = result.answer
    return result.answer


def answer_stream(
    question: str, params: GenerationParams | None = None
) -> Iterator[str]:
    """Trả lời dạng streaming (Section 6).

    Chỉ có input guardrail. Output guardrail không áp dụng được ở đây: token
    đã gửi tới client ngay khi sinh ra, nên không có cách nào "thay bằng
    fallback" sau khi phát hiện vấn đề — muốn kiểm tra output cho luồng
    streaming cần buffer toàn bộ trước (mất lợi ích của streaming) hoặc chấp
    nhận đánh đổi latency-thấp/không-guardrail-output.
    """
    check_input(question)
    chunks = retrieve(question)
    messages = build_messages(question, LEGAL_SYSTEM_PROMPT, chunks)
    yield from trace_stream(
        "answer_stream", question, completion.chat_stream(messages, params)
    )


def answer_structured(
    question: str, params: GenerationParams | None = None
) -> LegalAnswer:
    """Trả lời dạng structured output theo schema LegalAnswer (Section 4).

    Chỉ có input guardrail — LegalAnswer đã tự mang confidence/needs_lawyer,
    một hình thức "self-reported groundedness" riêng của schema này.
    """
    check_input(question)
    with trace_answer("answer_structured", question) as t:
        chunks = retrieve(question)
        messages = build_messages(question, LEGAL_SYSTEM_PROMPT, chunks)
        result = completion.chat_parsed(messages, LegalAnswer, params)
        t["output"] = result.model_dump_json()
    return result
