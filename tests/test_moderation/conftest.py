import os
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# =====================================================================
# 1. Задаём переменные окружения ДО любых импортов сервиса
# =====================================================================
os.environ.setdefault("MODERATION_DATABASE_URL", "postgresql+psycopg://fake:fake@localhost:5432/fake")
os.environ.setdefault("MODERATION_INTERNAL_API_KEY", "fake-internal-key")
os.environ.setdefault("MODERATION_ADMIN_TOKEN", "fake-admin-token")
os.environ.setdefault("MODERATION_FEED_SERVICE_URL", "http://fake-feed-service")

# =====================================================================
# 2. Подменяем фабрики auth-зависимостей ДО импорта main.py,
#    чтобы при загрузке модуля они уже были «безопасными».
# =====================================================================
import shared.api

TEST_USER_ID = str(uuid.uuid4())
TEST_ADMIN_DUMMY = None


def _mock_internal_key():
    return None


def _mock_admin_token():
    return None


shared.api.require_internal_api_key = lambda key: _mock_internal_key
shared.api.require_admin_token = lambda token: _mock_admin_token

# =====================================================================
# 3. Теперь импортируем приложение
# =====================================================================
from services.moderation_service.app.main import app, db_dependency  # noqa: E402

# Тестовые UUID-константы
TEST_VIDEO_ID = uuid.uuid4()
TEST_AUTHOR_ID = uuid.uuid4()
TEST_ITEM_ID = uuid.uuid4()


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy сессии."""
    return MagicMock()


@pytest.fixture
def client(mock_db_session):
    """TestClient с подменённой БД."""
    app.dependency_overrides[db_dependency] = lambda: mock_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_mocks(mock_db_session):
    mock_db_session.reset_mock()
