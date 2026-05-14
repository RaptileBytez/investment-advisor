"""Tiny in-memory TTL cache used by the data layer.

Designed for a single-process FastAPI worker. If we ever scale beyond one
worker we'll swap this for Redis behind the same interface."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Thread-safe key → value cache with per-item TTL."""

    def __init__(self, ttl_seconds: float):
        self._ttl = float(ttl_seconds)
        self._data: dict[str, tuple[T, float]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at < now:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._data[key] = (value, time.monotonic() + self._ttl)

    def get_or_compute(self, key: str, fn: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fn()
        self.set(key, value)
        return value

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._data.clear()
            else:
                self._data.pop(key, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
