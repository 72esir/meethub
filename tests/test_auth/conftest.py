import pytest
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

os.environ["AUTH_DATABASE_URL"] = "postgresql+psycopg://fake:fake@localhost:5432/fake"
os.environ["AUTH_JWT_SECRET"] = "super-secret-test-key"

# Импортируем приложение и зависимость базы данных
from services.auth_service.app.main import app, db_dependency

@pytest.fixture
def mock_db_session():
    """Фикстура, создающая мок для сессии SQLAlchemy."""
    session = MagicMock()
    return session

@pytest.fixture
def client(mock_db_session):
    """Фикстура для тестового клиента с подмененной базой данных."""
    app.dependency_overrides[db_dependency] = lambda: mock_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()