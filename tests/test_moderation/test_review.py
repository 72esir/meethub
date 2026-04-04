"""
Тесты для GET /moderation/pending,
POST /moderation/{item_id}/approve,
POST /moderation/{item_id}/reject
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.moderation_service.app.models import ModerationQueueItem, ModerationStatus
from tests.test_moderation.conftest import TEST_VIDEO_ID, TEST_AUTHOR_ID, TEST_ITEM_ID

ADMIN_HEADERS = {"x-admin-token": "fake-admin-token"}


def _make_item(*, item_id=None, status=ModerationStatus.pending, reason=None):
    item = ModerationQueueItem(
        video_id=TEST_VIDEO_ID,
        author_id=TEST_AUTHOR_ID,
        video_url="http://storage/video.mp4",
    )
    item.id = item_id or TEST_ITEM_ID
    item.status = status
    item.reason = reason
    item.created_at = datetime.now(timezone.utc)
    return item


# ──────────────────────────────────────────────
# GET /moderation/pending
# ──────────────────────────────────────────────

def test_pending_items_returns_list(client, mock_db_session):
    """GET /moderation/pending с admin-токеном возвращает список."""
    items = [_make_item(), _make_item(item_id=uuid.uuid4())]
    mock_db_session.scalars.return_value.all.return_value = items

    response = client.get("/moderation/pending", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["status"] == "pending"


def test_pending_items_empty(client, mock_db_session):
    """GET /moderation/pending — пустой список, если нет заявок."""
    mock_db_session.scalars.return_value.all.return_value = []

    response = client.get("/moderation/pending", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == []


# no-auth тесты для этих эндпоинтов покрыты в tests/test_shared/test_api.py —
# здесь auth мокнут глобально в conftest.py.


# ──────────────────────────────────────────────
# POST /moderation/{item_id}/approve
# ──────────────────────────────────────────────

def test_approve_success(client, mock_db_session, mocker):
    """Успешное одобрение: статус меняется, sync_feed_status вызывается."""
    item = _make_item()
    mock_db_session.get.return_value = item

    mock_sync = mocker.patch(
        "services.moderation_service.app.main.sync_feed_status",
        new_callable=AsyncMock,
    )

    response = client.post(f"/moderation/{TEST_ITEM_ID}/approve", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"status": "approved"}
    assert item.status == ModerationStatus.approved
    mock_db_session.commit.assert_called_once()
    mock_sync.assert_awaited_once_with(item.video_id, "approved")


def test_approve_not_found(client, mock_db_session, mocker):
    """Одобрение несуществующего элемента → 404."""
    mock_db_session.get.return_value = None
    mocker.patch(
        "services.moderation_service.app.main.sync_feed_status",
        new_callable=AsyncMock,
    )

    response = client.post(f"/moderation/{uuid.uuid4()}/approve", headers=ADMIN_HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "moderation item not found"





# ──────────────────────────────────────────────
# POST /moderation/{item_id}/reject
# ──────────────────────────────────────────────

def test_reject_success(client, mock_db_session, mocker):
    """Успешный reject: статус и reason устанавливаются, sync вызывается."""
    item = _make_item()
    mock_db_session.get.return_value = item

    mock_sync = mocker.patch(
        "services.moderation_service.app.main.sync_feed_status",
        new_callable=AsyncMock,
    )

    response = client.post(
        f"/moderation/{TEST_ITEM_ID}/reject",
        json={"reason": "Inappropriate content"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "rejected"}
    assert item.status == ModerationStatus.rejected
    assert item.reason == "Inappropriate content"
    mock_db_session.commit.assert_called_once()
    mock_sync.assert_awaited_once_with(item.video_id, "rejected")


def test_reject_not_found(client, mock_db_session, mocker):
    """Отклонение несуществующего элемента → 404."""
    mock_db_session.get.return_value = None
    mocker.patch(
        "services.moderation_service.app.main.sync_feed_status",
        new_callable=AsyncMock,
    )

    response = client.post(
        f"/moderation/{uuid.uuid4()}/reject",
        json={"reason": "spam"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404


def test_reject_missing_reason(client, mock_db_session):
    """Отклонение без обязательного поля reason → 422."""
    item = _make_item()
    mock_db_session.get.return_value = item

    response = client.post(
        f"/moderation/{TEST_ITEM_ID}/reject",
        json={},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422


