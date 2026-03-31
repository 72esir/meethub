import time

from sqlalchemy import text
from sqlalchemy.engine import Engine


def wait_for_database(engine: Engine, service_name: str, attempts: int = 20, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"{service_name}: database not ready, attempt {attempt}/{attempts}: {exc}")
            time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error
