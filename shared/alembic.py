from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


ROOT_DIR = Path(__file__).resolve().parents[1]


def build_alembic_config(service_name: str) -> Config:
    migrations_dir = ROOT_DIR / "migrations" / service_name
    config = Config(str(migrations_dir / "alembic.ini"))
    config.set_main_option("script_location", str(migrations_dir))
    return config


def upgrade_head(service_name: str, *, database_url: str, expected_tables: set[str]) -> None:
    config = build_alembic_config(service_name)
    config.set_main_option("sqlalchemy.url", database_url)

    engine = create_engine(database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    engine.dispose()

    if "alembic_version" not in table_names and expected_tables.issubset(table_names):
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")
