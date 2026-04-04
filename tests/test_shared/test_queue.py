"""
Тесты для shared/queue.py: enqueue / dequeue.
Используется fakeredis — реальный Redis не нужен.
"""
import json

import fakeredis
import pytest

from shared.queue import TRANSCODE_QUEUE, dequeue, enqueue


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


# ──────────────────────────────────────────────
# enqueue
# ──────────────────────────────────────────────

class TestEnqueue:
    def test_enqueue_adds_item(self, redis):
        payload = {"upload_id": "abc", "user_id": "u1"}
        enqueue(redis, TRANSCODE_QUEUE, payload)
        assert redis.llen(TRANSCODE_QUEUE) == 1

    def test_enqueue_serializes_to_json(self, redis):
        payload = {"key": "value", "number": 42}
        enqueue(redis, TRANSCODE_QUEUE, payload)
        raw = redis.lrange(TRANSCODE_QUEUE, 0, -1)[0]
        assert json.loads(raw) == payload

    def test_enqueue_multiple_items_fifo(self, redis):
        enqueue(redis, TRANSCODE_QUEUE, {"n": 1})
        enqueue(redis, TRANSCODE_QUEUE, {"n": 2})
        enqueue(redis, TRANSCODE_QUEUE, {"n": 3})
        items = [json.loads(x) for x in redis.lrange(TRANSCODE_QUEUE, 0, -1)]
        assert [i["n"] for i in items] == [1, 2, 3]

    def test_enqueue_to_custom_queue(self, redis):
        enqueue(redis, "my-queue", {"task": "do_something"})
        assert redis.llen("my-queue") == 1
        assert redis.llen(TRANSCODE_QUEUE) == 0


# ──────────────────────────────────────────────
# dequeue
# ──────────────────────────────────────────────

class TestDequeue:
    def test_dequeue_returns_item(self, redis):
        payload = {"upload_id": "xyz"}
        enqueue(redis, TRANSCODE_QUEUE, payload)
        result = dequeue(redis, TRANSCODE_QUEUE, timeout_seconds=1)
        assert result == payload

    def test_dequeue_order_is_fifo(self, redis):
        enqueue(redis, TRANSCODE_QUEUE, {"n": 1})
        enqueue(redis, TRANSCODE_QUEUE, {"n": 2})

        first = dequeue(redis, TRANSCODE_QUEUE, timeout_seconds=1)
        second = dequeue(redis, TRANSCODE_QUEUE, timeout_seconds=1)

        assert first["n"] == 1
        assert second["n"] == 2

    def test_dequeue_removes_item(self, redis):
        enqueue(redis, TRANSCODE_QUEUE, {"n": 1})
        dequeue(redis, TRANSCODE_QUEUE, timeout_seconds=1)
        assert redis.llen(TRANSCODE_QUEUE) == 0

    def test_dequeue_empty_queue_returns_none(self, redis):
        """timeout_seconds=0 в Redis означает «ждать вечно», поэтому используем 1 секунду."""
        result = dequeue(redis, TRANSCODE_QUEUE, timeout_seconds=1)
        assert result is None
