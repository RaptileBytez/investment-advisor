"""TTLCache correctness — used by the data provider for quotes and history."""

from __future__ import annotations

import time

from app.core.cache import TTLCache


def test_get_returns_none_for_missing_key():
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    assert cache.get("missing") is None


def test_set_then_get_returns_value():
    cache: TTLCache[str] = TTLCache(ttl_seconds=10)
    cache.set("a", "value")
    assert cache.get("a") == "value"


def test_entries_expire_after_ttl():
    cache: TTLCache[int] = TTLCache(ttl_seconds=0.01)
    cache.set("a", 1)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_get_or_compute_calls_fn_only_on_miss():
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    calls = {"n": 0}

    def make():
        calls["n"] += 1
        return 42

    assert cache.get_or_compute("k", make) == 42
    assert cache.get_or_compute("k", make) == 42
    assert calls["n"] == 1


def test_invalidate_specific_key():
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.invalidate("a")
    assert cache.get("a") is None
    assert cache.get("b") == 2


def test_invalidate_all():
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.invalidate()
    assert len(cache) == 0
