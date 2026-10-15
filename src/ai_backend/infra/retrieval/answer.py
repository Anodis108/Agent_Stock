"""Nhánh retrieval khái niệm: top-k, chấm liên quan, trả lời từ đoạn.

Không tách subquery, không rerank, không tìm web. Supervisor gửi câu khái niệm vào đây.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_backend.infra.qdrant.concepts import embed_concept_texts
from common.settings import settings

NOT_IN_DOCS = "Không có trong tài liệu."
_WORD = re.compile(r"\w+", re.UNICODE)
_STOP = frozenset(
    {
        "là",
        "gì",
        "của",
        "và",
        "các",
        "cho",
        "một",
        "những",
        "thế",
        "nào",
        "như",
        "thì",
        "có",
        "không",
        "trong",
        "được",
        "với",
        "này",
        "đó",
        "khi",
        "để",
        "về",
        "the",
        "what",
        "is",
    }
)


@dataclass(frozen=True, slots=True)
class ConceptAnswer:
    answer: str
    source_file: str | None
    relevant: bool


def content_tokens(text: str) -> set[str]:
    return {
        word
        for word in (part.casefold() for part in _WORD.findall(text or ""))
        if len(word) >= 2 and word not in _STOP
    }


def grade_chunk(question: str, chunk_text: str) -> bool:
    """Đoạn liên quan khi đủ từ nội dung trùng câu hỏi.

    Câu một từ thì một từ trùng là đủ. Câu nhiều từ cần ít nhất hai từ trùng,
    để một từ phổ biến như "ngày" không kéo cả đoạn giá trần vào.
    """
    asked = content_tokens(question)
    if not asked:
        return False
    overlap = asked & content_tokens(chunk_text)
    needed = 1 if len(asked) == 1 else 2
    return len(overlap) >= needed


def answer_concept(
    question: str,
    *,
    client: object,
    embed_fn=None,
    top_k: int = 4,
) -> ConceptAnswer:
    """Tìm top-k trên stock_concepts, chấm, rồi trả lời từ đoạn liên quan."""
    asked = (question or "").strip()
    name = (settings.concept_collection or "").strip()
    memory_name = (settings.qdrant_collection or "").strip()
    if not asked or not name or name == memory_name:
        return ConceptAnswer(NOT_IN_DOCS, None, False)
    if not client.collection_exists(name):
        return ConceptAnswer(NOT_IN_DOCS, None, False)

    embed = embed_fn or embed_concept_texts
    vector = embed([asked])[0]
    found = client.query_points(collection_name=name, query=vector, limit=max(int(top_k), 1))
    for hit in found.points:
        payload = hit.payload or {}
        text = str(payload.get("text") or "").strip()
        source = str(payload.get("source_file") or "").strip()
        if text and grade_chunk(asked, text):
            return ConceptAnswer(text, source or None, True)
    return ConceptAnswer(NOT_IN_DOCS, None, False)
