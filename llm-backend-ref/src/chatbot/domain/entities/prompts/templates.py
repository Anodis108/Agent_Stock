"""Prompt templates — Bài 1, Section 3 (Prompt Patterns).

Minh hoạ role prompting (persona luật sư VN) + chỗ chèn context cho RAG (Buổi 5).
Ở Buổi 1, context luôn rỗng (retriever là stub) — system prompt được thiết kế để
xử lý cả trường hợp "không có tài liệu" một cách trung thực.
"""

from __future__ import annotations

from src.chatbot.domain.service.retrieval.retriever import RetrievedChunk





def build_messages(
    question: str, system_content: str, context_chunks: list[RetrievedChunk] | None = None
) -> list[dict]:
    """Dựng danh sách messages cho một câu hỏi.

    Nếu có context_chunks (từ Buổi 5 trở đi) thì chèn vào trước câu hỏi —
    đây chính là bước "Augment" của RAG. Ở Buổi 1, context_chunks rỗng.
    """

    if context_chunks:
        # Hiển thị source (từ Buổi 5 chunk có metadata thật) để model trích dẫn đúng nguồn.
        context_block = "\n\n".join(
            f"[Nguồn {i + 1}: {c.source or 'tài liệu'}] {c.text}"
            for i, c in enumerate(context_chunks)
        )
        system_content += f"\n\n--- TÀI LIỆU THAM KHẢO ---\n{context_block}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]
