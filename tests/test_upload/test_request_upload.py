"""
Тесты для POST /upload/request — инициализация сессии загрузки.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.upload_service.app.models import UploadSession, UploadStatus
from tests.test_upload.conftest import TEST_USER_ID

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _make_session(*, session_id=None, user_id=None, s3_key="raw/user/video.mp4"):
    session = UploadSession(
        user_id=user_id or uuid.UUID(TEST_USER_ID),
        s3_key=s3_key,
    )
    session.id = session_id or uuid.uuid4()
    session.status = UploadStatus.pending
    session.description = None
    session.hashtags = None
    session.created_at = datetime.now(timezone.utc)
    return session


# ──────────────────────────────────────────────
# POST /upload/request
# ──────────────────────────────────────────────

def test_request_upload_success(client, mock_db_session, mocker):
    """Успешный запрос presigned URL — возвращает upload_id, upload_url, s3_key."""
    created_session = _make_session()

    def _refresh(obj):
        obj.id = created_session.id
        obj.status = UploadStatus.pending
        obj.created_at = created_session.created_at

    mock_db_session.refresh.side_effect = _refresh

    # Мокаем presigned URL
    import services.upload_service.app.main as main_module
    main_module.presign_s3_client = MagicMock()
    main_module.presign_s3_client.generate_presigned_url.return_value = "https://s3/presigned-url"

    payload = {"file_name": "my_video.mp4", "content_type": "video/mp4"}
    response = client.post("/upload/request", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert "upload_id" in data
    assert data["upload_url"] == "https://s3/presigned-url"
    assert "s3_key" in data
    assert data["expires_in_seconds"] == 1800

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


def test_request_upload_default_content_type(client, mock_db_session, mocker):
    """Если content_type не передан, используется video/mp4 по умолчанию."""
    created_session = _make_session()

    def _refresh(obj):
        obj.id = created_session.id
        obj.status = UploadStatus.pending
        obj.created_at = created_session.created_at

    mock_db_session.refresh.side_effect = _refresh

    import services.upload_service.app.main as main_module
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3/url"
    main_module.presign_s3_client = mock_s3

    payload = {"file_name": "video.mp4"}
    response = client.post("/upload/request", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 200
    # Проверяем, что ContentType передан как video/mp4
    call_kwargs = mock_s3.generate_presigned_url.call_args
    assert call_kwargs[1]["Params"]["ContentType"] == "video/mp4"


def test_request_upload_missing_file_name(client, mock_db_session):
    """POST /upload/request без file_name → 422."""
    response = client.post("/upload/request", json={}, headers=AUTH_HEADERS)
    assert response.status_code == 422


# no-auth тесты покрыты в tests/test_shared/test_api.py —
# JWT-зависимость мокнута глобально в conftest.py.
