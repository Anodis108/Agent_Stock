"""Tool retrieval cho từng agent_pr — cùng ý agent_m2, catalog truyền vào.

Không MCP. Index theo tên tool (cache). Không embed được → trả catalog[:k]
(test/offline vẫn bind được tool).
"""

from __future__ import annotations

import math

from app.config import settings

_index: dict[tuple[str, ...], list[tuple[str, list[float]]]] = {}


def _desc(t) -> str:
    return f"{getattr(t, 'name', '')}: {getattr(t, 'description', '') or ''}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _key(catalog: list) -> tuple[str, ...]:
    return tuple(getattr(t, "name", str(i)) for i, t in enumerate(catalog))


def select_tools(query: str, catalog: list, k: int | None = None) -> list:
    """Top-k tool trong `catalog` theo embedding mô tả. Catalog rỗng → []."""
    if not catalog:
        return []
    top = k if k is not None else int(settings.agent_tool_retrieval_k)
    top = max(1, min(top, len(catalog)))
    q = (query or "").strip()
    if not q:
        return list(catalog[:top])

    names = _key(catalog)
    try:
        from app.retrieval.embeddings import embed_passages, embed_query

        if names not in _index:
            vecs = embed_passages([_desc(t) for t in catalog])
            _index[names] = list(zip(names, vecs))
        qv = embed_query(q)
        scored = [(n, _cosine(qv, v)) for n, v in _index[names]]
        scored.sort(key=lambda p: p[1], reverse=True)
        want = {n for n, _ in scored[:top]}
        by_name = {getattr(t, "name", ""): t for t in catalog}
        return [by_name[n] for n in want if n in by_name]
    except Exception:
        return list(catalog[:top])


def reset_cache() -> None:
    _index.clear()
