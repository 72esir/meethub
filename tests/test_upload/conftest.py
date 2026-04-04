import os
import uuid
import pytest
import fakeredis
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# =====================================================================
# 1. Переменные окружения ДО импортов сервиса
# =====================================================================
os.environ.setdefault("UPLOAD_DATABASE_URL", "postgresql+psycopg://fake:fake@localhost:5432/fake")
os.environ.setdefault("UPLOAD_JWT_SECRET", "super-secret-test-key")
os.environ.setdefault("UPLOAD_REDIS_QUEUE_URL", "redis://localhost:6379/0")
os.environ.setdefault("UPLOAD_S3_ENDPOINT_URL", "http://fake-s3:9000")
os.environ.setdefault("UPLOAD_S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("UPLOAD_S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("UPLOAD_S3_BUCKET_RAW", "raw-videos")

# =====================================================================
# 2. Подмена JWT-зависимости и S3/Redis ДО импорта main.py
# =====================================================================
import shared.api

TEST_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _mock_jwt():
    return TEST_USER_ID


shared.api.require_jwt = lambda secret: _mock_jwt

# Мокаем boto3, чтобы не требовалось реальное S3-окружение
import unittest.mock as _mock
_patch_boto3 = _mock.patch("boto3.client", return_value=MagicMock())
_patch_boto3.start()

# =====================================================================
# 3. Теперь импортируем приложение
# =====================================================================
from services.upload_service.app.main import app, db_dependency  # noqa: E402

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def fake_redis_queue():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(mock_db_session, fake_redis_queue):
    """TestClient с подменёнными БД и Redis."""
    app.dependency_overrides[db_dependency] = lambda: mock_db_session

    import services.upload_service.app.main as main_module
    main_module.queue = fake_redis_queue

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_state(mock_db_session, fake_redis_queue):
    yield
    mock_db_session.reset_mock()
    fake_redis_queue.flushall()
