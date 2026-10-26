"""Opt-in real-service check; CI supplies Redis, never silently substitutes a mock."""
import os
from uuid import uuid4

import pytest

from app.workers import queue


@pytest.mark.skipif(os.environ.get("NEXUS_TEST_REDIS") != "1", reason="requires real Redis service")
def test_real_redis_queue_round_trip_preserves_order(monkeypatch):
    key = f"nexus:test:jobs:{uuid4().hex}"
    monkeypatch.setattr(queue, "QUEUE_NAME", key)
    redis_queue = queue.RedisJobQueue()
    first, second = uuid4(), uuid4()
    assert redis_queue.ping(), "Redis integration was requested but service is unavailable"
    try:
        redis_queue.enqueue(first)
        redis_queue.enqueue(second)
        assert redis_queue.dequeue() == first
        assert redis_queue.dequeue() == second
        assert redis_queue.dequeue() is None
    finally:
        redis_queue.client.delete(key)
        redis_queue.client.close()
