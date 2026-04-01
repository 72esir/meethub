import uuid
from sqlalchemy.exc import IntegrityError
from services.auth_service.app.models import User

def test_register_success(client, mock_db_session, mocker):
    # Мокаем функции безопасности, чтобы не тратить время на реальное хэширование
    mocker.patch("services.auth_service.app.main.hash_password", return_value="hashed_test_pass")
    mocker.patch("services.auth_service.app.main.create_access_token", return_value="mock_access")
    mocker.patch("services.auth_service.app.main.create_refresh_token", return_value="mock_refresh")

    # Имитируем, что БД возвращает созданного пользователя с ID
    def mock_refresh_user(obj):
        obj.id = uuid.uuid4()
        
    mock_db_session.refresh.side_effect = mock_refresh_user

    payload = {
        "email": "test@example.com",
        "password": "strongpassword123",
        "username": "testuser"
    }
    
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["access_token"] == "mock_access"
    assert data["refresh_token"] == "mock_refresh"
    assert data["token_type"] == "bearer"
    
    # Проверяем, что в базу дважды сделали add (один раз User, второй раз SessionModel)
    assert mock_db_session.add.call_count == 2
    mock_db_session.commit.assert_called()


def test_register_duplicate_user(client, mock_db_session, mocker):
    mocker.patch("services.auth_service.app.main.hash_password", return_value="hashed_test_pass")
    
    # Имитируем ошибку уникальности в БД (email или username уже заняты)
    mock_db_session.commit.side_effect = IntegrityError("mock error", "mock params", "mock orig")

    payload = {
        "email": "duplicate@example.com",
        "password": "strongpassword123",
        "username": "duplicate_user"
    }
    
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "email or username already exists"}
    
    # Проверяем, что произошел откат транзакции
    mock_db_session.rollback.assert_called_once()