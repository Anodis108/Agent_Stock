"""Cắt năm file khái niệm, embed, ghi collection stock_concepts.

Collection này khác portfolio_watch_memory. Hàm này không tìm và không trả lời.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from backend.infra.cache.exact import normalize_question
from backend.infra.storage.long_term_memory import _ensure_collection
from backend.shared.settings import settings

_NAMESPACE = uuid.UUID("6f0c1d2e-3a4b-5c6d-7e8f-90a1b2c3d4e5")


@dataclass(frozen=True, slots=True)
class ConceptChunk:
    text: str
    source_file: str
    chunk_index: int
    heading: str


def concepts_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "resources" / "docs" / "concepts"


def chunk_markdown(source_file: str, text: str, *, chunk_size: int = 512) -> list[ConceptChunk]:
    """Cắt theo đoạn văn. Mỗi đoạn mang tên heading của file."""
    heading = ""
    body_lines: list[str] = []
    for line in text.splitlines():
        if not heading and line.startswith("# "):
            heading = line[2:].strip()
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    pieces: list[str] = []
    for paragraph in paragraphs:
        pieces.extend(_fit(paragraph, chunk_size))
    chunks: list[ConceptChunk] = []
    for index, piece in enumerate(pieces):
        prefixed = f"{heading}\n\n{piece}" if heading else piece
        chunks.append(
            ConceptChunk(
                text=prefixed,
                source_file=source_file,
                chunk_index=index,
                heading=heading,
            )
        )
    return chunks


def load_concept_chunks() -> list[ConceptChunk]:
    chunks: list[ConceptChunk] = []
    for path in sorted(concepts_dir().glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(path.name, text))
    return chunks


def embed_concept_texts(texts: list[str]) -> list[list[float]]:
    """Embed offline, ổn định giữa các lần chạy. Không gọi OpenAI."""
    return [_embed_stable(text) for text in texts]


def _embed_stable(text: str) -> list[float]:
    vec = [0.0] * 256
    normalized = normalize_question(text)
    for index in range(max(0, len(normalized) - 2)):
        tri = normalized[index : index + 3]
        vec[_bucket(tri)] += 1.0
    tokens = normalized.split()
    for token in tokens:
        vec[_bucket(f"w:{token}")] += 1.5
    for index in range(len(tokens) - 1):
        vec[_bucket(f"bg:{tokens[index]}_{tokens[index + 1]}")] += 0.75
    norm = math.sqrt(sum(item * item for item in vec))
    if norm > 0:
        vec = [item / norm for item in vec]
    return vec


def _bucket(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 256


def index_concepts(
    *,
    client: object,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    collection_name: str | None = None,
) -> int:
    """Ghi đoạn khái niệm vào Qdrant. Trả về số điểm đã ghi."""
    name = (collection_name or settings.concept_collection).strip()
    memory_name = (settings.qdrant_collection or "").strip()
    if not name or name == memory_name:
        raise ValueError("collection khái niệm phải khác collection bộ nhớ dài hạn")

    chunks = load_concept_chunks()
    if not chunks:
        raise ValueError("không có file khái niệm để nạp")

    vectors = (embed_fn or embed_concept_texts)([chunk.text for chunk in chunks])
    if len(vectors) != len(chunks) or not vectors[0]:
        raise ValueError("embed không trả đủ vector")

    from qdrant_client.models import PointStruct

    if client.collection_exists(name):
        client.delete_collection(name)
    _ensure_collection(client, name, dim=len(vectors[0]))
    points = [
        PointStruct(
            id=str(uuid.uuid5(_NAMESPACE, f"{chunk.source_file}:{chunk.chunk_index}")),
            vector=vector,
            payload={
                "text": chunk.text,
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
                "heading": chunk.heading,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    client.upsert(collection_name=name, points=points)
    return len(points)


def _fit(text: str, chunk_size: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            split_at = text.rfind(". ", start, end)
            if split_at > start:
                end = split_at + 1
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = end
    return pieces
