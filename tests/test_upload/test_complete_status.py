"""
Тесты для POST /upload/complete и GET /upload/status/{upload_id}.
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.upload_service.app.models import UploadSession, UploadStatus
from shared.queue import TRANSCODE_QUEUE
from tests.test_upload.conftest import TEST_USER_ID

AUTH_HEADERS = {"Authorization": "Bearer test-token"}

TEST_UPLOAD_ID = uuid.uuid4()
OTHER_USER_ID = str(uuid.uuid4())


def _make_session(*, session_id=None, user_id=None, status=UploadStatus.pending,
                  description=None, hashtags=None, s3_key="raw/user/video.mp4"):
    resolved_user_id = user_id or uuid.UUID(TEST_USER_ID)
    session = UploadSession(
        user_id=resolved_user_id,
        s3_key=s3_key,
    )
    session.id = session_id or TEST_UPLOAD_ID
    session.user_id = resolved_user_id  # явно задаём, чтобы SQLAlchemy ORM не убирал
    session.status = status
    session.description = description
    session.hashtags = hashtags
    session.created_at = datetime.now(timezone.utc)
    return session


# ──────────────────────────────────────────────
# POST /upload/complete
# ──────────────────────────────────────────────

def test_complete_upload_success(client, mock_db_session, fake_redis_queue):
    """Успешное завершение: статус → uploaded, задача добавлена в очередь."""
    session = _make_session()
    mock_db_session.get.return_value = session

    payload = {
        "upload_id": str(TEST_UPLOAD_ID),
        "description": "My cool video",
        "hashtags": ["fun", "viral"],
    }
    response = client.post("/upload/complete", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert session.status == UploadStatus.uploaded
    assert session.description == "My cool video"
    assert session.hashtags == "fun,viral"
    mock_db_session.commit.assert_called_once()

    # Проверяем, что задача попала в Redis
    raw = fake_redis_queue.lrange(TRANSCODE_QUEUE, 0, -1)
    assert len(raw) == 1
    task = json.loads(raw[0])
    assert task["upload_id"] == str(TEST_UPLOAD_ID)
    assert task["user_id"] == TEST_USER_ID
    assert task["description"] == "My cool video"
    assert task["hashtags"] == ["fun", "viral"]


def test_complete_upload_empty_hashtags(client, mock_db_session, fake_redis_queue):
    """Завершение без хэштегов — hashtags сохраняется как пустая строка."""
    session = _make_session()
    mock_db_session.get.return_value = session

    payload = {"upload_id": str(TEST_UPLOAD_ID), "description": "desc"}
    response = client.post("/upload/complete", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert session.hashtags == ""


def test_complete_upload_not_found(client, mock_db_session):
    """Неизвестный upload_id → 404."""
    mock_db_session.get.return_value = None

    payload = {"upload_id": str(uuid.uuid4())}
    response = client.post("/upload/complete", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "upload not found"


def test_complete_upload_wrong_owner(client, mock_db_session):
    """Попытка завершить чужую сессию → 404."""
    session = _make_session(user_id=uuid.UUID(OTHER_USER_ID))
    mock_db_session.get.return_value = session

    payload = {"upload_id": str(TEST_UPLOAD_ID)}
    response = client.post("/upload/complete", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 404


# no-auth тесты покрыты в tests/test_shared/test_api.py —
# JWT-зависимость мокнута глобально в conftest.py.


# ──────────────────────────────────────────────
# GET /upload/status/{upload_id}
# ──────────────────────────────────────────────

def test_upload_status_success(client, mock_db_session):
    """GET /upload/status — возвращает корректный статус сессии."""
    session = _make_session(
        status=UploadStatus.transcoding,
        description="My video",
        hashtags="fun,viral",
    )
    mock_db_session.get.return_value = session

    response = client.get(f"/upload/status/{TEST_UPLOAD_ID}", headers=AUTH_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_UPLOAD_ID)
    assert data["status"] == "transcoding"
    assert data["description"] == "My video"
    assert data["hashtags"] == ["fun", "viral"]


def test_upload_status_no_hashtags(client, mock_db_session):
    """GET /upload/status — hashtags=None возвращает пустой список."""
    session = _make_session(hashtags=None)
    mock_db_session.get.return_value = session

    response = client.get(f"/upload/status/{TEST_UPLOAD_ID}", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["hashtags"] == []


def test_upload_status_not_found(client, mock_db_session):
    """GET /upload/status для неизвестного ID → 404."""
    mock_db_session.get.return_value = None

    response = client.get(f"/upload/status/{uuid.uuid4()}", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_upload_status_wrong_owner(client, mock_db_session):
    """GET /upload/status чужой сессии → 404."""
    session = _make_session(user_id=uuid.UUID(OTHER_USER_ID))
    mock_db_session.get.return_value = session

    response = client.get(f"/upload/status/{TEST_UPLOAD_ID}", headers=AUTH_HEADERS)
    assert response.status_code == 404


