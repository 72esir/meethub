from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.alembic import upgrade_head
from services.auth_service.app.settings import settings as auth_settings
from services.feed_service.app.settings import settings as feed_settings
from services.moderation_service.app.settings import settings as moderation_settings
from services.upload_service.app.settings import settings as upload_settings


VALID_SERVICES = {"auth", "upload", "feed", "moderation"}
SERVICE_CONFIG = {
    "auth": {
        "database_url": auth_settings.database_url,
        "expected_tables": {"users", "sessions"},
    },
    "upload": {
        "database_url": upload_settings.database_url,
        "expected_tables": {"upload_sessions"},
    },
    "feed": {
        "database_url": feed_settings.database_url,
        "expected_tables": {"videos", "likes", "follows", "views"},
    },
    "moderation": {
        "database_url": moderation_settings.database_url,
        "expected_tables": {"moderation_queue"},
    },
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_SERVICES:
        print(f"Usage: python scripts/run_migrations.py <{'|'.join(sorted(VALID_SERVICES))}>")
        return 1

    service_name = sys.argv[1]
    config = SERVICE_CONFIG[service_name]
    upgrade_head(
        service_name,
        database_url=config["database_url"],
        expected_tables=config["expected_tables"],
    )
    print(f"Applied migrations for {service_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
