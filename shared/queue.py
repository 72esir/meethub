import json
from typing import Any

from redis import Redis

TRANSCODE_QUEUE = "transcode-queue"


def enqueue(redis_client: Redis, queue_name: str, payload: dict[str, Any]) -> None:
    redis_client.rpush(queue_name, json.dumps(payload))


def dequeue(redis_client: Redis, queue_name: str, timeout_seconds: int = 5) -> dict[str, Any] | None:
    item = redis_client.blpop(queue_name, timeout=timeout_seconds)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)
