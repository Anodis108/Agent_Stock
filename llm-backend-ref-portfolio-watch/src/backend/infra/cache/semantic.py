"""Semantic LLM response cache — M3-B3 Phase 9.

Embed câu hỏi (sau rewrite_node), cosine ≥ 0.93, bỏ qua câu có ngày/giá động.
MVP in-memory; embedding OpenAI khi có API key, fallback char-hash vector offline.
"""

from __future__ import annotations

import math
import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from backend.infra.cache.exact import get_llm_cache_context, normalize_question
from backend.shared.settings import settings

COSINE_THRESHOLD = 0.93
TTL_SECONDS = 24 * 3600
_EMBED_DIM = 256

_semantic_question_ctx: ContextVar[str | None] = ContextVar("semantic_question", default=None)

_DYNAMIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bhôm nay\b",
        r"\bhôm qua\b",
        r"\btuần nay\b",
        r"\btuần này\b",
        r"\btháng này\b",
        r"\bnăm nay\b",
        r"\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?",
        r"\b\d{4,}\s*(?:vnd|đ|đồng)\b",
    )
)


def is_semantic_cache_enabled() -> bool:
    val = os.environ.get("SEMANTIC_CACHE_ENABLED", "true").lower()
    return val in ("1", "true", "yes")


def set_semantic_question(text: str | None) -> None:
    """Gọi sau rewrite_node — câu đã rewrite dùng cho semantic lookup."""
    _semantic_question_ctx.set((text or "").strip() or None)


def get_semantic_question() -> str | None:
    return _semantic_question_ctx.get()


def clear_semantic_question() -> None:
    _semantic_question_ctx.set(None)


def is_dynamic_question(text: str) -> bool:
    """Bỏ qua cache semantic cho câu có ngày/giá động."""
    s = (text or "").strip()
    if not s:
        return False
    return any(p.search(s) for p in _DYNAMIC_PATTERNS)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _embed_simple(text: str) -> list[float]:
    """Offline embedding — char trigrams + word tokens, L2-normalized."""
    vec = [0.0] * _EMBED_DIM
    normalized = normalize_question(text)
    for i in range(max(0, len(normalized) - 2)):
        tri = normalized[i : i + 3]
        vec[hash(tri) % _EMBED_DIM] += 1.0
    tokens = normalized.split()
    for tok in tokens:
        vec[hash(f"w:{tok}") % _EMBED_DIM] += 1.5
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]}_{tokens[i + 1]}"
        vec[hash(f"bg:{bg}") % _EMBED_DIM] += 0.75
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def embed_question(text: str) -> list[float]:
    """Embed câu hỏi — OpenAI nếu có key, else simple offline vector."""
    normalized = normalize_question(text)
    try:
        from backend.infra.storage.long_term_memory import (
            _embed_passages,
            _has_valid_openai_key,
        )

        if _has_valid_openai_key():
            vectors = _embed_passages([normalized])
            if vectors and vectors[0]:
                return list(vectors[0])
    except Exception:
        pass
    return _embed_simple(normalized)


@dataclass(slots=True)
class _SemanticEntry:
    embedding: list[float]
    value: str
    source_question: str
    expires_at: float


@dataclass(slots=True)
class SemanticHitAudit:
    query: str
    matched_question: str
    similarity: float
    prompt_name: str
    false_hit_risk: str = "low"

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "matched_question": self.matched_question,
            "similarity": round(self.similarity, 4),
            "prompt_name": self.prompt_name,
            "false_hit_risk": self.false_hit_risk,
        }


@dataclass
class SemanticCache:
    threshold: float = COSINE_THRESHOLD
    ttl_seconds: float = TTL_SECONDS
    _entries: dict[str, list[_SemanticEntry]] = field(default_factory=dict)
    audit_log: list[SemanticHitAudit] = field(default_factory=list)

    def _bucket_key(self, prompt_name: str, prompt_version: str, model: str) -> str:
        return f"{prompt_name}|{prompt_version}|{model}"

    def lookup(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        model: str,
        question: str,
    ) -> tuple[str, float, str] | None:
        """Trả (value, similarity, matched_question) hoặc None."""
        if is_dynamic_question(question):
            return None
        embedding = embed_question(question)
        key = self._bucket_key(prompt_name, prompt_version, model)
        best: tuple[str, float, str] | None = None
        now = time.time()
        alive: list[_SemanticEntry] = []
        for entry in self._entries.get(key, []):
            if now >= entry.expires_at:
                continue
            alive.append(entry)
            sim = cosine_similarity(embedding, entry.embedding)
            if sim >= self.threshold and (best is None or sim > best[1]):
                best = (entry.value, sim, entry.source_question)
        self._entries[key] = alive
        if best is not None:
            self.audit_log.append(
                SemanticHitAudit(
                    query=question,
                    matched_question=best[2],
                    similarity=best[1],
                    prompt_name=prompt_name,
                )
            )
        return best

    def store(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        model: str,
        question: str,
        value: str,
    ) -> None:
        if is_dynamic_question(question) or not value:
            return
        key = self._bucket_key(prompt_name, prompt_version, model)
        self._entries.setdefault(key, []).append(
            _SemanticEntry(
                embedding=embed_question(question),
                value=value,
                source_question=question,
                expires_at=time.time() + self.ttl_seconds,
            )
        )

    def clear(self) -> None:
        self._entries.clear()
        self.audit_log.clear()

    @property
    def size(self) -> int:
        return sum(len(v) for v in self._entries.values())


_global_semantic = SemanticCache()


def get_semantic_cache() -> SemanticCache:
    return _global_semantic


def _cache_context_fields() -> tuple[str, str, str, str] | None:
    ctx = get_llm_cache_context()
    prompt_name = ctx.get("prompt_name")
    if not prompt_name:
        return None
    prompt_version = str(ctx.get("prompt_version") or "production")
    semantic_q = get_semantic_question()
    question = semantic_q or ctx.get("normalized_question")
    if question is None:
        return None
    return (
        str(prompt_name),
        prompt_version,
        settings.llm_model,
        str(question),
    )


def try_semantic_cache_get() -> str | None:
    """Tier 2 lookup — sau exact miss."""
    if not is_semantic_cache_enabled():
        return None
    fields = _cache_context_fields()
    if fields is None:
        return None
    prompt_name, prompt_version, model, question = fields
    hit = get_semantic_cache().lookup(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        model=model,
        question=question,
    )
    if hit is None:
        return None
    return hit[0]


def store_semantic_cache_entry(value: str) -> None:
    """Lưu response sau LLM miss (exact đã store riêng)."""
    if not is_semantic_cache_enabled() or not value:
        return
    fields = _cache_context_fields()
    if fields is None:
        return
    prompt_name, prompt_version, model, question = fields
    get_semantic_cache().store(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        model=model,
        question=question,
        value=value,
    )
