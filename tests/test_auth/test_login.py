import uuid
from services.auth_service.app.models import User

def test_login_success(client, mock_db_session, mocker):
    # Мокаем проверку пароля и генерацию токенов
    mocker.patch("services.auth_service.app.main.verify_password", return_value=True)
    mocker.patch("services.auth_service.app.main.create_access_token", return_value="mock_access")
    mocker.patch("services.auth_service.app.main.create_refresh_token", return_value="mock_refresh")

    # Имитируем, что пользователь найден в БД
    mock_user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hashed_pw")
    mock_db_session.scalar.return_value = mock_user

    payload = {"email": "test@example.com", "password": "correctpassword"}
    response = client.post("/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json()["access_token"] == "mock_access"


def test_login_invalid_credentials(client, mock_db_session, mocker):
    # Имитируем, что пароль неверный
    mocker.patch("services.auth_service.app.main.verify_password", return_value=False)
    
    mock_user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hashed_pw")
    mock_db_session.scalar.return_value = mock_user

    payload = {"email": "test@example.com", "password": "wrongpassword"}
    response = client.post("/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_login_user_not_found(client, mock_db_session):
    # Имитируем, что пользователя нет в БД
    mock_db_session.scalar.return_value = None

    payload = {"email": "notfound@example.com", "password": "anypassword"}
    response = client.post("/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}