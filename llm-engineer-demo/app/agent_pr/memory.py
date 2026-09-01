"""Long-term memory — Hierarchical VN-stock (`agent_pr`).

Cùng mô hình `app.agent_m2.memory`: sự thật về user nằm NGOÀI graph state,
lọc theo `user_id`. Đầu lượt `recall_memory` đọc vào; cuối lượt `store_memory`
ghi ra (xem supervisor_agent/nodes.py).

Vector store: Qdrant + embedding native (`app.retrieval.embeddings`). Không
có OPENAI_API_KEYS → fallback in-memory (keyword), đủ để test/demo.
"""

from __future__ import annotations

import time
import uuid
from functools import lru_cache

from app.config import settings


def _use_qdrant() -> bool:
    """Có key để embed không? Không → fallback, không crash."""
    return bool(settings.api_keys)


@lru_cache(maxsize=1)
def _client():
    """Qdrant client singleton — `:memory:` cho test/demo, ngược lại nối `qdrant_url` thật."""
    from qdrant_client import QdrantClient

    if settings.qdrant_url == ":memory:":
        return QdrantClient(location=":memory:")
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


def _ensure_collection() -> None:
    """Tạo collection `agent_memory_collection` nếu chưa có — gọi trước mỗi upsert."""
    from qdrant_client.models import Distance, VectorParams

    client = _client()
    name = settings.agent_memory_collection
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dim, distance=Distance.COSINE
            ),
        )


# Fallback khi không embed được. list[(user_id, fact)].
_FALLBACK: list[tuple[str, str]] = []


def _fallback_save(user_id: str, fact: str) -> None:
    """Lưu fact vào list in-memory (không key OpenAI hoặc Qdrant lỗi)."""
    _FALLBACK.append((user_id, fact))


def _fallback_recall(user_id: str, query: str, k: int) -> list[str]:
    """Retrieve thô: xếp theo số từ khoá trùng `query`, hoà điểm thì ưu tiên fact mới nhất."""
    mine = [fact for uid, fact in _FALLBACK if uid == user_id]
    query_words = {w.lower() for w in query.split() if len(w) > 2}
    scored = sorted(
        reversed(mine),
        key=lambda f: len(query_words & {w.lower() for w in f.split()}),
        reverse=True,
    )
    return scored[:k]


def save_to_long_term(user_id: str, fact: str) -> None:
    """Lưu 1 sự thật dài hạn về user (mã theo dõi, khẩu vị, …)."""
    fact = fact.strip()
    if not fact:
        return

    if not _use_qdrant():
        _fallback_save(user_id, fact)
        return

    from qdrant_client.models import PointStruct

    from app.retrieval.embeddings import embed_passages

    try:
        _ensure_collection()
        vector = embed_passages([fact])[0]
        _client().upsert(
            collection_name=settings.agent_memory_collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "text": fact,
                        "user_id": user_id,
                        "type": "semantic",
                        "ts": time.time(),
                    },
                )
            ],
        )
    except Exception:
        _fallback_save(user_id, fact)


def recall_long_term(user_id: str, query: str, k: int = 3) -> list[str]:
    """Tối đa k memory liên quan tới query, chỉ của user này."""
    if not _use_qdrant():
        return _fallback_recall(user_id, query, k)

    try:
        client = _client()
        if not client.collection_exists(settings.agent_memory_collection):
            return []

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        from app.retrieval.embeddings import embed_query

        response = client.query_points(
            collection_name=settings.agent_memory_collection,
            query=embed_query(query),
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=k,
        )
        return [h.payload.get("text", "") for h in response.points]
    except Exception:
        return _fallback_recall(user_id, query, k)
