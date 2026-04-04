"""
Тесты для POST /moderation/queue
"""
import uuid
from unittest.mock import MagicMock

from services.moderation_service.app.models import ModerationQueueItem, ModerationStatus
from tests.test_moderation.conftest import TEST_VIDEO_ID, TEST_AUTHOR_ID, TEST_ITEM_ID

INTERNAL_HEADERS = {"x-internal-key": "fake-internal-key"}


def _make_item(*, video_id=None, author_id=None, item_id=None, status=ModerationStatus.pending):
    item = ModerationQueueItem(
        video_id=video_id or TEST_VIDEO_ID,
        author_id=author_id or TEST_AUTHOR_ID,
        video_url="http://storage/video.mp4",
    )
    item.id = item_id or TEST_ITEM_ID
    item.status = status
    item.reason = None
    from datetime import datetime, timezone
    item.created_at = datetime.now(timezone.utc)
    return item


# ──────────────────────────────────────────────
# queue_item  POST /moderation/queue
# ──────────────────────────────────────────────

def test_queue_item_success(client, mock_db_session):
    """Успешное добавление видео в очередь модерации."""
    created_item = _make_item()

    def _refresh(obj):
        obj.id = created_item.id
        obj.status = ModerationStatus.pending
        obj.reason = None
        obj.created_at = created_item.created_at

    mock_db_session.refresh.side_effect = _refresh

    payload = {
        "video_id": str(TEST_VIDEO_ID),
        "author_id": str(TEST_AUTHOR_ID),
        "video_url": "http://storage/video.mp4",
    }
    response = client.post("/moderation/queue", json=payload, headers=INTERNAL_HEADERS)

    assert response.status_code == 201
    data = response.json()
    assert data["video_id"] == str(TEST_VIDEO_ID)
    assert data["author_id"] == str(TEST_AUTHOR_ID)
    assert data["status"] == "pending"
    assert data["reason"] is None
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


def test_queue_item_missing_fields(client, mock_db_session):
    """POST /moderation/queue без обязательного поля video_id → 422."""
    payload = {
        "author_id": str(TEST_AUTHOR_ID),
        "video_url": "http://storage/video.mp4",
    }
    response = client.post("/moderation/queue", json=payload, headers=INTERNAL_HEADERS)
    assert response.status_code == 422


# Примечание: тест «no auth» для этих эндпоинтов покрыт в tests/test_shared/test_api.py,
# поскольку shared.api зависимости мокируются в conftest для изоляции тестов сервиса.
