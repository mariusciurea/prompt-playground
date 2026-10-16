"""Key-value store for rate limits, locks, and short-lived cache entries.

Redis backs it in production; an in-process store serves development and tests.
"""

import asyncio
import time
from typing import Protocol

from redis.asyncio import Redis


class Store(Protocol):
    """Minimal async key-value operations the app relies on."""

    async def incr(self, key: str, ttl_seconds: int) -> int:
        """Increment a counter, setting its TTL when it is created."""
        ...

    async def get(self, key: str) -> str | None:
        """Return a value, or None if missing or expired."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store a value with a TTL."""
        ...

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Store a value only if the key is free; return whether it was stored."""
        ...

    async def delete(self, *keys: str) -> None:
        """Remove keys."""
        ...

    async def ping(self) -> bool:
        """Check connectivity."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...


class RedisStore:
    """Store backed by Redis."""

    def __init__(self, url: str) -> None:
        self._redis: Redis = Redis.from_url(url, decode_responses=True)

    async def incr(self, key: str, ttl_seconds: int) -> int:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            count, _ = await pipe.execute()
        return int(count)

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        return None if value is None else str(value)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        return bool(await self._redis.set(key, value, ex=ttl_seconds, nx=True))

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._redis.delete(*keys)

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def close(self) -> None:
        await self._redis.aclose()


class MemoryStore:
    """Single-process store for development and tests."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    def _live(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at <= time.monotonic():
            del self._data[key]
            return None
        return value

    async def incr(self, key: str, ttl_seconds: int) -> int:
        async with self._lock:
            current = self._live(key)
            if current is None:
                self._data[key] = ("1", time.monotonic() + ttl_seconds)
                return 1
            count = int(current) + 1
            self._data[key] = (str(count), self._data[key][1])
            return count

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._live(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        async with self._lock:
            self._data[key] = (value, time.monotonic() + ttl_seconds)

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        async with self._lock:
            if self._live(key) is not None:
                return False
            self._data[key] = (value, time.monotonic() + ttl_seconds)
            return True

    async def delete(self, *keys: str) -> None:
        async with self._lock:
            for key in keys:
                self._data.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._data.clear()


def create_store(redis_url: str | None) -> Store:
    """Build a Redis store when a URL is configured, else an in-memory one."""
    return RedisStore(redis_url) if redis_url else MemoryStore()
