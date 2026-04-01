import os
import uuid
import pytest
import fakeredis
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# 1. Задаем переменные окружения
os.environ["FEED_DATABASE_URL"] = "postgresql+psycopg://fake:fake@localhost:5432/fake"
os.environ["FEED_JWT_SECRET"] = "super-secret-test-key"
os.environ["FEED_INTERNAL_API_KEY"] = "fake-internal-key"
os.environ["FEED_REDIS_CACHE_URL"] = "redis://localhost:6379/0"

# Фиксируем тестовые ID для стабильности моков
TEST_USER_ID_STR = str(uuid.uuid4())
TEST_VIDEO_ID_UUID = uuid.uuid4()

# =====================================================================
# Перехватываем создание зависимостей ДО импорта main.py
# =====================================================================
import shared.api

# Создаем функции, которые всегда возвращают нужные нам данные
def mock_jwt_dependency():
    return TEST_USER_ID_STR

def mock_internal_key_dependency():
    return None

# Подменяем фабрики. Теперь, когда main.py при загрузке вызовет 
# require_jwt(...), он получит нашу mock-функцию!
shared.api.require_jwt = lambda secret: mock_jwt_dependency
shared.api.require_internal_api_key = lambda secret: mock_internal_key_dependency
# =====================================================================

# 3. Только ТЕПЕРЬ импортируем приложение
from services.feed_service.app.main import app, db_dependency

@pytest.fixture
def test_user_id():
    return TEST_USER_ID_STR

@pytest.fixture
def test_video_id():
    return TEST_VIDEO_ID_UUID

@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture
def client(mock_db_session, fake_redis):
    # Нам больше не нужно переопределять JWT/API_KEY через dependency_overrides, 
    # так как мы подменили их у самых истоков. Оставляем только БД.
    app.dependency_overrides[db_dependency] = lambda: mock_db_session
    
    import services.feed_service.app.main as main_app
    main_app.cache = fake_redis

    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def reset_state(mock_db_session, fake_redis):
    mock_db_session.reset_mock()
    fake_redis.flushall()