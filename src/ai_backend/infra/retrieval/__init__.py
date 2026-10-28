"""Retrieval infrastructure package — map `app/retrieval/` (llm-engineer-demo).

Hỗ trợ RAG khái niệm tài chính (Qdrant semantic search + local fallback):
- concepts: nạp và đánh chỉ mục chunks Markdown lên Qdrant (`stock_concepts`).
- answer: tìm kiếm top-k, tính độ tương đồng cosine, sinh câu trả lời bám sát evidence.
"""

from ai_backend.infra.retrieval.answer import (
    NOT_IN_DOCS,
    ConceptAnswer,
    answer_concept,
)
from ai_backend.infra.retrieval.concepts import (
    ConceptChunk,
    chunk_markdown,
    concepts_dir,
    embed_concept_texts,
    index_concepts,
    load_concept_chunks,
)

__all__ = [
    "NOT_IN_DOCS",
    "ConceptAnswer",
    "ConceptChunk",
    "answer_concept",
    "chunk_markdown",
    "concepts_dir",
    "embed_concept_texts",
    "index_concepts",
    "load_concept_chunks",
]
