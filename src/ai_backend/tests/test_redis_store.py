"""RedisStore và ExactCache dùng chung get/setex. Không cần Redis thật."""

from __future__ import annotations

import builtins

from ai_backend.infra.cache.exact import ExactCache, InMemoryStore, get_exact_cache, reset_exact_cache_for_tests
from ai_backend.infra.cache.redis_store import RedisStore, redis_url_from_env
from common.settings import settings


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.data[key] = value
        self.ttls[key] = ttl_seconds


def test_redis_url_uses_compose_hostname_when_set(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert redis_url_from_env(None) == "redis://localhost:6379"
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379")
    assert redis_url_from_env(None) == "redis://redis:6379"
    assert redis_url_from_env("redis://other:6379") == "redis://other:6379"


def test_redis_store_get_setex_with_fake_client(monkeypatch):
    real_import = builtins.__import__

    def _block_redis(name, *args, **kwargs):
        if name == "redis" or name.startswith("redis."):
            raise AssertionError("RedisStore không được import redis khi đã có client")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_redis)
    fake = _FakeRedis()
    store = RedisStore(client=fake)
    assert store.get("missing") is None
    store.setex("k1", 60, "value1")
    assert store.get("k1") == "value1"
    assert fake.ttls["k1"] == 60


def test_exact_cache_uses_fake_store_setex():
    fake = _FakeRedis()
    cache = ExactCache(store=fake, ttl_seconds=30)
    assert cache.get("missing") is None
    cache.set("answer", "Xin chào")
    assert cache.get("answer") == "Xin chào"
    assert fake.ttls["answer"] == 30
    assert fake.data["answer"] == "Xin chào"


def test_redis_backend_builds_redis_store_without_connecting(monkeypatch):
    monkeypatch.setattr(settings, "cache_backend", "redis")
    created: dict[str, bool] = {}

    class _Store:
        def get(self, key: str) -> str | None:
            return None

        def setex(self, key: str, ttl_seconds: int, value: str) -> None:
            return None

    def _factory(url: str = "redis://localhost:6379", client=None):
        created["called"] = True
        assert client is None
        return _Store()

    monkeypatch.setattr("ai_backend.infra.cache.redis_store.RedisStore", _factory)
    reset_exact_cache_for_tests()
    try:
        cache = get_exact_cache()
        assert created["called"] is True
        assert isinstance(cache._store, _Store)
    finally:
        monkeypatch.setattr(settings, "cache_backend", "memory")
        reset_exact_cache_for_tests()


def test_default_exact_cache_stays_memory(monkeypatch):
    monkeypatch.setattr(settings, "cache_backend", "memory")
    reset_exact_cache_for_tests()
    try:
        cache = get_exact_cache()
        assert isinstance(cache._store, InMemoryStore)
        cache.set("k", "v")
        assert cache.get("k") == "v"
    finally:
        reset_exact_cache_for_tests()
