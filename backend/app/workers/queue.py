from __future__ import annotations

import json
from collections import deque
from threading import Lock
from uuid import UUID

try:
    from redis import Redis
except ImportError:  # Local development can run without Redis installed.
    Redis = None  # type: ignore[assignment,misc]

from app.core.config import settings


QUEUE_NAME = "nexus:jobs"


class LocalJobQueue:
    """Process-local fallback used for tests/development without Redis."""

    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._lock = Lock()

    def enqueue(self, job_id: UUID) -> None:
        with self._lock:
            self._items.append(str(job_id))

    def dequeue(self) -> UUID | None:
        with self._lock:
            if not self._items:
                return None
            return UUID(self._items.popleft())


class RedisJobQueue:
    def __init__(self, url: str | None = None) -> None:
        if Redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = Redis.from_url(url or settings.REDIS_URL, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def enqueue(self, job_id: UUID) -> None:
        self.client.rpush(QUEUE_NAME, str(job_id))

    def dequeue(self, timeout: int = 1) -> UUID | None:
        try:
            item = self.client.blpop(QUEUE_NAME, timeout=timeout)
        except Exception:
            return None
        if not item:
            return None
        return UUID(item[1])


def get_redis_queue() -> RedisJobQueue | None:
    if not settings.REDIS_ENABLED or Redis is None:
        return None
    queue = RedisJobQueue()
    return queue if queue.ping() else None
