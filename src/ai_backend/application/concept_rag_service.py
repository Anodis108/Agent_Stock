"""Concept RAG Service — Tìm kiếm ngữ nghĩa tài liệu khái niệm chứng khoán trên Qdrant.

Kế thừa BaseService từ common.base.base_service.
Tuân thủ AC-8: Trả về đoạn văn bản cùng source_file nếu tìm thấy;
nếu không tìm thấy hoặc ngoài tài liệu, trả về "Không có trong tài liệu." và source_file=None.
Hỗ trợ cả Qdrant Vector Client lẫn In-memory Fallback trên 5 file markdown phục vụ kiểm thử offline 100%.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from common.base.base_model import CustomBaseModel
from common.base.base_service import BaseService
from common.logging.logger import get_logger

logger = get_logger("ai_backend.application.concept_rag")

NOT_IN_DOCS = "Không có trong tài liệu."

_WORD_REGEX = re.compile(r"\w+", re.UNICODE)
_STOP_WORDS = frozenset(
    {
        "là", "gì", "của", "và", "các", "cho", "một", "những", "thế", "nào",
        "như", "thì", "có", "không", "trong", "được", "với", "này", "đó", "khi",
        "để", "về", "the", "what", "is",
    }
)


def _content_tokens(text: str) -> set[str]:
    return {
        word
        for word in (part.casefold() for part in _WORD_REGEX.findall(text or ""))
        if len(word) >= 2 and word not in _STOP_WORDS
    }


def _grade_chunk(question: str, chunk_text: str) -> bool:
    """Đánh giá mức độ liên quan giữa câu hỏi và đoạn trích."""
    asked = _content_tokens(question)
    if not asked:
        return False
    overlap = asked & _content_tokens(chunk_text)
    needed = 1 if len(asked) == 1 else 2
    return len(overlap) >= needed


def _find_concepts_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        cand = parent / "resources" / "docs" / "concepts"
        if cand.is_dir():
            return cand
    return current.parents[3] / "resources" / "docs" / "concepts"


class ConceptRagInput(CustomBaseModel):
    """Input cho Concept RAG Service."""
    question: str
    top_k: int = 4
    client: Any = None


class ConceptRagOutput(CustomBaseModel):
    """Output từ Concept RAG Service."""
    question: str
    answer: str
    source_file: str | None = None
    relevant: bool = False


class ConceptRagService(BaseService):
    """Service tìm kiếm và trả lời khái niệm chứng khoán."""

    def __init__(self, *, qdrant_client: Any = None, collection_name: str = "stock_concepts") -> None:
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self._local_chunks: list[dict[str, str]] | None = None

    def _load_local_chunks(self) -> list[dict[str, str]]:
        if self._local_chunks is not None:
            return self._local_chunks
        chunks: list[dict[str, str]] = []
        concepts_dir = _find_concepts_dir()
        if concepts_dir.is_dir():
            for md_file in sorted(concepts_dir.glob("*.md")):
                text = md_file.read_text(encoding="utf-8")
                # Tách paragraphs
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                heading = ""
                for p in paragraphs:
                    if p.startswith("# "):
                        heading = p[2:].strip()
                        continue
                    full_chunk = f"{heading}\n\n{p}" if heading else p
                    chunks.append({"text": full_chunk, "source_file": md_file.name})
        self._local_chunks = chunks
        return chunks

    def process(self, inputs: ConceptRagInput) -> ConceptRagOutput:
        """Xử lý tra cứu khái niệm theo câu hỏi."""
        q = (inputs.question or "").strip()
        if not q:
            return ConceptRagOutput(question=q, answer=NOT_IN_DOCS, source_file=None, relevant=False)

        client = inputs.client or self.qdrant_client

        # 1. Nếu có Qdrant client được kết nối
        if client is not None:
            try:
                if hasattr(client, "collection_exists") and client.collection_exists(self.collection_name):
                    # Thử import helper embed
                    from ai_backend.infra.retrieval.concepts import embed_concept_texts
                    vector = embed_concept_texts([q])[0]
                    found = client.query_points(collection_name=self.collection_name, query=vector, limit=inputs.top_k)
                    for hit in getattr(found, "points", []):
                        payload = getattr(hit, "payload", {}) or {}
                        text = str(payload.get("text") or "").strip()
                        source = str(payload.get("source_file") or "").strip()
                        if text and _grade_chunk(q, text):
                            return ConceptRagOutput(
                                question=q,
                                answer=text,
                                source_file=source or None,
                                relevant=True,
                            )
            except Exception as exc:
                logger.warning(f"Qdrant query thất bại, fallback sang in-memory local chunks: {exc}")

        # 2. In-memory local chunks search (100% offline, không phụ thuộc Qdrant daemon)
        chunks = self._load_local_chunks()
        best_match: dict[str, str] | None = None
        max_overlap = 0
        asked_tokens = _content_tokens(q)

        for chunk in chunks:
            chunk_tokens = _content_tokens(chunk["text"])
            overlap = len(asked_tokens & chunk_tokens)
            needed = 1 if len(asked_tokens) == 1 else 2
            if overlap >= needed and overlap > max_overlap:
                max_overlap = overlap
                best_match = chunk

        if best_match is not None:
            return ConceptRagOutput(
                question=q,
                answer=best_match["text"],
                source_file=best_match["source_file"],
                relevant=True,
            )

        return ConceptRagOutput(
            question=q,
            answer=NOT_IN_DOCS,
            source_file=None,
            relevant=False,
        )
