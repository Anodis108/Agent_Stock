"""Long-term memory storage — Qdrant with in-memory fallback (Phase 8).

Cùng mô hình `llm-engineer-demo/app/agent_pr/memory.py`:
- Sự thật về user lọc theo `user_id`.
- Đầu lượt `recall_memory` đọc vào; cuối lượt `store_memory` ghi ra.
- Qdrant optional: khi có Qdrant client và embedding hợp lệ -> lưu vector.
- Không Qdrant / không có key / URL unset hoặc ':memory:' / lỗi kết nối:
  tự động fallback in-memory (keyword + recency), tuyệt đối không crash.
- `user_id` rỗng hoặc None -> bỏ qua long-term hoàn toàn.
"""

from __future__ import annotations

import time
import uuid
from functools import lru_cache
from typing import Any, Callable

from backend.shared.logging import get_logger
from backend.shared.settings import settings

_logger = get_logger(__name__)

# Fallback in-memory list: list[dict[str, Any]] with keys: user_id, text, ts
_FALLBACK_STORE: list[dict[str, Any]] = []


def clear_long_term_fallback(user_id: str | None = None) -> None:
    """Xóa fallback in-memory (dùng trong test hoặc reset session)."""
    global _FALLBACK_STORE
    if user_id is None:
        _FALLBACK_STORE.clear()
    else:
        uid = str(user_id).strip()
        _FALLBACK_STORE = [item for item in _FALLBACK_STORE if item.get("user_id") != uid]


def _has_valid_openai_key() -> bool:
    """Kiểm tra có OpenAI API key thực sự (không phải placeholder 'not-needed')."""
    valid_keys = [k for k in settings.api_keys if k and k != "not-needed"]
    return bool(valid_keys)


def _use_qdrant(*, client: Any = None, embed_fn: Any = None) -> bool:
    """Kiểm tra điều kiện dùng Qdrant (client/URL + key/embed_fn)."""
    if client is not None:
        return True
    url = (settings.qdrant_url or "").strip()
    if not url:
        return False
    if embed_fn is not None:
        return True
    return _has_valid_openai_key()


@lru_cache(maxsize=1)
def get_qdrant_client(url: str | None = None, api_key: str | None = None) -> Any:
    """Qdrant client singleton. Trả None nếu thiếu thư viện qdrant_client."""
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        _logger.warning("qdrant-client not installed; long-term memory will use in-memory fallback")
        return None

    target_url = url if url is not None else (settings.qdrant_url or "").strip()
    target_api_key = api_key if api_key is not None else (settings.qdrant_api_key or None)

    if not target_url:
        return None

    try:
        if target_url == ":memory:":
            return QdrantClient(location=":memory:")
        client = QdrantClient(
            url=target_url,
            api_key=target_api_key,
            timeout=0.5,
            check_compatibility=False,
        )
        # Fast connectivity check: nếu server không phản hồi, dùng fallback ngay
        try:
            client.get_collections()
        except Exception:
            _logger.debug("Qdrant server at %s not reachable, fallback in-memory", target_url)
            return None
        return client
    except Exception as exc:
        _logger.warning("Failed to initialize Qdrant client: %s", exc)
        return None


def _ensure_collection(client: Any, collection_name: str, dim: int = 1536) -> None:
    """Tạo collection nếu chưa có trên Qdrant."""
    from qdrant_client.models import Distance, VectorParams

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def _embed_passages(texts: list[str]) -> list[list[float]]:
    """Tạo vector embeddings qua OpenAI API (OpenAI Cloud)."""
    if not _has_valid_openai_key():
        raise ValueError("Missing valid OpenAI API key for embedding")

    from openai import OpenAI

    valid_keys = [k for k in settings.api_keys if k and k != "not-needed"]
    client = OpenAI(api_key=valid_keys[0])
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _fallback_save(user_id: str, fact: str) -> None:
    """Lưu fact vào in-memory store."""
    _FALLBACK_STORE.append(
        {
            "user_id": user_id,
            "text": fact,
            "ts": time.time(),
        }
    )


def _fallback_recall(user_id: str, query: str, k: int = 3) -> list[str]:
    """Retrieve thô: lọc theo user_id, xếp theo số từ khóa trùng + độ mới (recency)."""
    mine = [item for item in _FALLBACK_STORE if item.get("user_id") == user_id]
    if not mine:
        return []

    query_words = {w.lower() for w in (query or "").split() if len(w) > 2}

    def _score(item: dict[str, Any]) -> tuple[int, float]:
        text = str(item.get("text") or "")
        fact_words = {w.lower() for w in text.split()}
        overlap = len(query_words & fact_words)
        ts = float(item.get("ts") or 0.0)
        return (overlap, ts)

    scored = sorted(mine, key=_score, reverse=True)
    return [str(item.get("text") or "") for item in scored[:k] if item.get("text")]


def save_to_long_term(
    user_id: str | None,
    fact: str,
    *,
    client: Any = None,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> None:
    """Lưu 1 sự thật dài hạn về user (mã theo dõi, khẩu vị đầu tư, v.v.).

    - user_id rỗng hoặc None -> bỏ qua, không crash.
    - Qdrant không sẵn sàng hoặc lỗi -> lưu in-memory fallback.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return

    text = str(fact or "").strip()
    if not text:
        return

    if not _use_qdrant(client=client, embed_fn=embed_fn):
        _fallback_save(uid, text)
        return

    try:
        q_client = client or get_qdrant_client()
        if q_client is None:
            _fallback_save(uid, text)
            return

        col_name = settings.qdrant_collection
        dim = settings.embedding_dim
        _ensure_collection(q_client, col_name, dim=dim)

        embed_func = embed_fn or _embed_passages
        vectors = embed_func([text])
        if not vectors or not vectors[0]:
            _fallback_save(uid, text)
            return

        from qdrant_client.models import PointStruct

        q_client.upsert(
            collection_name=col_name,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[0],
                    payload={
                        "text": text,
                        "user_id": uid,
                        "type": "semantic",
                        "ts": time.time(),
                    },
                )
            ],
        )
    except Exception as exc:
        _logger.debug("Qdrant upsert failed (%s), falling back to in-memory: %s", exc, text)
        _fallback_save(uid, text)


def recall_long_term(
    user_id: str | None,
    query: str,
    k: int = 3,
    *,
    client: Any = None,
    embed_fn: Callable[[str], list[float]] | None = None,
) -> list[str]:
    """Truy xuất tối đa k sự thật liên quan tới query, chỉ của user này.

    - user_id rỗng hoặc None -> trả về [] an toàn, không crash.
    - Qdrant không sẵn sàng hoặc lỗi -> truy xuất từ in-memory fallback.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return []

    limit = max(int(k), 1)

    if not _use_qdrant(client=client, embed_fn=embed_fn):
        return _fallback_recall(uid, query, limit)

    try:
        q_client = client or get_qdrant_client()
        if q_client is None:
            return _fallback_recall(uid, query, limit)

        col_name = settings.qdrant_collection
        if not q_client.collection_exists(col_name):
            return _fallback_recall(uid, query, limit)

        def _default_embed_query(q_str: str) -> list[float]:
            return _embed_passages([q_str])[0]

        query_embed_func = embed_fn or _default_embed_query
        vector = query_embed_func(query or "user facts")

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        response = q_client.query_points(
            collection_name=col_name,
            query=vector,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=uid))]
            ),
            limit=limit,
        )
        memories = [
            str(h.payload.get("text", ""))
            for h in response.points
            if h.payload and h.payload.get("text")
        ]
        return memories if memories else _fallback_recall(uid, query, limit)
    except Exception as exc:
        _logger.debug("Qdrant recall failed (%s), falling back to in-memory for %s", exc, uid)
        return _fallback_recall(uid, query, limit)
