from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.alembic import upgrade_head


VALID_SERVICES = {"auth", "upload", "feed", "moderation"}


def get_service_config(service_name: str) -> dict[str, Any]:
    if service_name == "auth":
        from services.auth_service.app.settings import settings

        return {
            "database_url": settings.database_url,
            "expected_tables": {"users", "sessions"},
            "baseline_revision": "0001_auth_initial",
        }
    if service_name == "upload":
        from services.upload_service.app.settings import settings

        return {
            "database_url": settings.database_url,
            "expected_tables": {"upload_sessions"},
            "baseline_revision": "0001_upload_initial",
        }
    if service_name == "feed":
        from services.feed_service.app.settings import settings

        return {
            "database_url": settings.database_url,
            "expected_tables": {"videos", "likes", "follows", "views"},
            "baseline_revision": "0001_feed_initial",
        }
    if service_name == "moderation":
        from services.moderation_service.app.settings import settings

        return {
            "database_url": settings.database_url,
            "expected_tables": {"moderation_queue"},
            "baseline_revision": "0001_moderation_initial",
        }
    raise ValueError(f"Unknown service: {service_name}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_SERVICES:
        print(f"Usage: python scripts/run_migrations.py <{'|'.join(sorted(VALID_SERVICES))}>")
        return 1

    service_name = sys.argv[1]
    config = get_service_config(service_name)
    upgrade_head(
        service_name,
        database_url=config["database_url"],
        expected_tables=config["expected_tables"],
        baseline_revision=config["baseline_revision"],
    )
    print(f"Applied migrations for {service_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
