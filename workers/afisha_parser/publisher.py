"""
Publisher: публикует AfishaEvent в feed_service через Internal API.

Шаги для каждого события:
1. POST /internal/videos  — создать запись (статус moderation_pending)
2. PUT  /internal/videos/{id}/status  — сразу одобрить (approved)
"""

import logging
import uuid

import httpx

from workers.afisha_parser.models import AfishaEvent
from workers.afisha_parser.settings import Settings

log = logging.getLogger(__name__)

# Публичный демо-HLS (Big Buck Bunny) — заглушка для видео-поля
_DEMO_HLS_URL = (
    "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
)

# Публичная заглушка-картинка, если у события нет обложки
_FALLBACK_THUMBNAIL = (
    "https://afisha.yandex.ru/favicon.ico"
)


def _build_payload(event: AfishaEvent, bot_user_id: str) -> dict:
    video_id = str(uuid.uuid4())

    payload: dict = {
        "id": video_id,
        "author_id": bot_user_id,
        "description": f"{event.title}\n\n{event.description}".strip(),
        "hashtags": event.tags,
        "hls_url": _DEMO_HLS_URL,
        "thumbnail_url": event.image_url or _FALLBACK_THUMBNAIL,
        "duration": None,
    }

    if any([event.place_name, event.city, event.latitude, event.longitude]):
        payload["location"] = {
            "name": event.place_name,
            "city": event.city,
            "latitude": event.latitude,
            "longitude": event.longitude,
        }

    return payload


def publish(event: AfishaEvent, settings: Settings, client: httpx.Client) -> bool:
    """
    Опубликовать одно событие в feed_service.
    Возвращает True при успехе, False при ошибке.
    """
    base = settings.feed_service_url.rstrip("/")
    headers = {"X-Internal-Api-Key": settings.internal_api_key}
    payload = _build_payload(event, settings.bot_user_id)
    video_id = payload["id"]

    # 1. Создать запись
    try:
        resp = client.post(f"{base}/internal/videos", json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.error(
            "Ошибка создания события '%s': HTTP %s — %s",
            event.title,
            exc.response.status_code,
            exc.response.text[:300],
        )
        return False
    except Exception as exc:
        log.error("Ошибка запроса создания '%s': %s", event.title, exc)
        return False

    # 2. Сразу одобрить
    try:
        resp = client.put(
            f"{base}/internal/videos/{video_id}/status",
            json={"status": "approved"},
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.error(
            "Ошибка апрува события '%s' (id=%s): HTTP %s — %s",
            event.title,
            video_id,
            exc.response.status_code,
            exc.response.text[:300],
        )
        return False
    except Exception as exc:
        log.error("Ошибка запроса апрува '%s': %s", event.title, exc)
        return False

    log.info("✓ Опубликовано: %s (id=%s)", event.title, video_id)
    return True
