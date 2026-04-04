from collections.abc import Callable

import httpx
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Engine


def check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis(redis_client) -> None:
    redis_client.ping()


def check_s3(client) -> None:
    client.list_buckets()


def check_http(url: str) -> None:
    response = httpx.get(url, timeout=3.0)
    response.raise_for_status()


def readiness_response(service: str, checks: dict[str, Callable[[], None]]) -> dict[str, object]:
    results: dict[str, str] = {}
    failed: dict[str, str] = {}
    for name, check in checks.items():
        try:
            check()
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            results[name] = "error"
            failed[name] = str(exc)

    payload = {"service": service, "status": "ok" if not failed else "error", "checks": results}
    if failed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={**payload, "errors": failed},
        )
    return payload
