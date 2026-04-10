"""
Точка входа воркера afisha_parser.

Алгоритм:
1. Загрузить уже обработанные external_id из кеш-файла (дедупликация).
2. Запросить события с Яндекс.Афиши.
3. Отфильтровать новые (те, чьих ID нет в кеше).
4. Опубликовать каждое новое событие в feed_service.
5. Сохранить обновлённый список ID в кеш-файл.
"""

import json
import logging
import sys
from pathlib import Path

import httpx

from workers.afisha_parser.fetcher import fetch_events
from workers.afisha_parser.publisher import publish
from workers.afisha_parser.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("afisha_parser")


def load_seen_ids(path: str) -> set[str]:
    p = Path(path)
    if p.exists():
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:
            log.warning("Не удалось прочитать кеш ID (%s): %s", path, exc)
    return set()


def save_seen_ids(path: str, ids: set[str]) -> None:
    try:
        Path(path).write_text(json.dumps(list(ids), ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        log.warning("Не удалось сохранить кеш ID (%s): %s", path, exc)


def main() -> None:
    log.info("=== afisha_parser запущен ===")
    log.info("Город: %s | feed_service: %s", settings.city, settings.feed_service_url)

    # 1. Загрузить уже виденные ID
    seen_ids = load_seen_ids(settings.seen_ids_path)
    log.info("В кеше %d уже обработанных событий", len(seen_ids))

    # 2. Получить события с Афиши
    events = fetch_events(settings)
    if not events:
        log.warning("Не удалось получить ни одного события. Завершение.")
        sys.exit(0)

    # 3. Отфильтровать новые
    new_events = [e for e in events if e.external_id not in seen_ids]
    log.info("Новых событий для публикации: %d / %d", len(new_events), len(events))

    if not new_events:
        log.info("Нет новых событий. Завершение.")
        sys.exit(0)

    # 4. Публикация
    published = 0
    failed = 0
    newly_seen: set[str] = set()

    with httpx.Client(timeout=20) as client:
        for event in new_events:
            success = publish(event, settings, client)
            if success:
                published += 1
                newly_seen.add(event.external_id)
            else:
                failed += 1

    # 5. Сохранить обновлённый кеш
    seen_ids |= newly_seen
    save_seen_ids(settings.seen_ids_path, seen_ids)

    log.info(
        "=== Завершено: опубликовано %d, ошибок %d ===",
        published,
        failed,
    )
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
