"""
Fetcher для Яндекс.Афиши через HTML-парсинг.

Яндекс.Афиша рендерит список мероприятий прямо в HTML страницы.
Парсим несколько страниц-рубрик и извлекаем:
  - название события
  - описание
  - место проведения
  - картинку
  - теги/рубрику

Используемые URL:
  https://afisha.yandex.ru/{city}/{rubric}
"""

import logging
import re
import json
from typing import Any

import httpx
from bs4 import BeautifulSoup

from workers.afisha_parser.models import AfishaEvent
from workers.afisha_parser.settings import Settings

log = logging.getLogger(__name__)

_BASE_URL = "https://afisha.yandex.ru"

_RUBRICS = [
    ("concert", "концерт"),
    ("theatre", "театр"),
    ("exhibition", "выставка"),
    ("standup", "стендап"),
    ("kids", "дети"),
    ("other", "другое"),
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# Города: afisha использует русские имена в URL
_CITY_MAP = {
    "moscow": "moscow",
    "spb": "saint-petersburg",
    "saint-petersburg": "saint-petersburg",
    "novosibirsk": "novosibirsk",
    "ekaterinburg": "yekaterinburg",
}


def _extract_json_state(html: str) -> dict | None:
    """Пробует вытащить __INITIAL_STATE__ из HTML страницы Афиши."""
    # Афиша вшивает данные в тег <script> как window.__INITIAL_STATE__ = {...}
    patterns = [
        r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*(?:window|</script>)",
        r"__INITIAL_STATE__\s*=\s*(\{.*?\});",
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return None


def _parse_events_from_state(state: dict, city: str, rubric_tag: str) -> list[AfishaEvent]:
    """Извлечь события из __INITIAL_STATE__ объекта."""
    events: list[AfishaEvent] = []
    # Пути где могут лежать события в state
    candidates: list[Any] = []

    def _collect(obj, depth=0):
        if depth > 6:
            return
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict) and ("title" in obj[0] or "event" in obj[0]):
                candidates.extend(obj)
            for item in obj:
                _collect(item, depth + 1)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect(v, depth + 1)

    _collect(state)

    seen: set[str] = set()
    for raw in candidates:
        event_data = raw.get("event") or raw
        eid = str(event_data.get("id") or "")
        if not eid or eid in seen:
            continue
        title = event_data.get("title") or ""
        if not title:
            continue
        seen.add(eid)

        description = event_data.get("description") or event_data.get("argument") or title
        description = re.sub(r"<[^>]+>", " ", description).strip()

        # Картинка
        image_url = None
        poster = event_data.get("poster") or {}
        if isinstance(poster, dict):
            sizes = poster.get("sizes") or {}
            for k in ("wide", "original", "normal", "small"):
                u = (sizes.get(k) or {}).get("url")
                if u:
                    image_url = u
                    break

        # Место
        place_name = None
        latitude = None
        longitude = None
        schedules = raw.get("schedules") or []
        if schedules and isinstance(schedules[0], dict):
            place = schedules[0].get("place") or {}
            place_name = place.get("title") or place.get("name")
            coords = place.get("coordinates") or {}
            latitude = coords.get("latitude")
            longitude = coords.get("longitude")

        tags = [rubric_tag]
        for t in event_data.get("tags") or []:
            name = (t.get("name") if isinstance(t, dict) else str(t)) or ""
            if name:
                tags.append(name.lower())
        tags = list(dict.fromkeys(tags))

        events.append(AfishaEvent(
            external_id=eid,
            title=title,
            description=description,
            city=city,
            place_name=place_name,
            latitude=latitude,
            longitude=longitude,
            image_url=image_url,
            tags=tags,
        ))

    return events


def _parse_events_from_html(html: str, city: str, rubric_tag: str) -> list[AfishaEvent]:
    """Fallback: вытащить события из HTML через BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    events: list[AfishaEvent] = []
    seen: set[str] = set()

    # Ищем карточки мероприятий — они обычно в article или li с data-* атрибутами
    cards = (
        soup.select("article[data-event-id]")
        or soup.select("[data-event-id]")
        or soup.select(".event-card")
        or soup.select(".tiles-item")
        or soup.select(".event-snippet")
    )

    for card in cards:
        eid = (
            card.get("data-event-id")
            or card.get("data-id")
            or str(hash(card.get_text()[:50]))
        )
        if eid in seen:
            continue
        seen.add(str(eid))

        # Заголовок
        title_el = card.select_one("h2,h3,[class*='title'],[class*='name']")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        # Описание
        desc_el = card.select_one("[class*='desc'],[class*='annotation'],[class*='argument']")
        description = desc_el.get_text(strip=True) if desc_el else title

        # Место
        place_el = card.select_one("[class*='place'],[class*='venue'],[class*='location']")
        place_name = place_el.get_text(strip=True) if place_el else None

        # Картинка
        img_el = card.select_one("img[src],img[data-src]")
        image_url = None
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src")
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

        events.append(AfishaEvent(
            external_id=str(eid),
            title=title,
            description=description,
            city=city,
            place_name=place_name,
            latitude=None,
            longitude=None,
            image_url=image_url,
            tags=[rubric_tag],
        ))

    return events


def fetch_events(settings: Settings) -> list[AfishaEvent]:
    """
    Получить мероприятия с Яндекс.Афиши.
    Сначала пробует вытащить из __INITIAL_STATE__ JSON внутри HTML,
    затем fallback на CSS-селекторы.
    """
    city_slug = _CITY_MAP.get(settings.city, settings.city)
    all_events: list[AfishaEvent] = []
    seen_ids: set[str] = set()
    per_rubric = max(10, settings.events_limit // len(_RUBRICS))

    with httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
        for rubric_slug, rubric_tag in _RUBRICS:
            if len(all_events) >= settings.events_limit:
                break

            url = f"{_BASE_URL}/{city_slug}/{rubric_slug}"
            try:
                log.info("GET %s", url)
                resp = client.get(url)
                resp.raise_for_status()
                html = resp.text
            except Exception as exc:
                log.error("Ошибка загрузки %s: %s", url, exc)
                continue

            # 1. Пробуем __INITIAL_STATE__
            state = _extract_json_state(html)
            if state:
                events = _parse_events_from_state(state, settings.city, rubric_tag)
                log.info("  __INITIAL_STATE__: найдено %d событий", len(events))
            else:
                # 2. Fallback — HTML-парсинг
                events = _parse_events_from_html(html, settings.city, rubric_tag)
                log.info("  HTML-парсинг: найдено %d событий", len(events))

            for ev in events:
                if ev.external_id not in seen_ids and len(all_events) < settings.events_limit:
                    seen_ids.add(ev.external_id)
                    all_events.append(ev)

            if not events:
                log.warning("  Рубрика '%s': события не найдены", rubric_slug)

    log.info("Итого собрано событий: %d", len(all_events))
    return all_events
