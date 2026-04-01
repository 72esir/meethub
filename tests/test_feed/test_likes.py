import uuid
from services.feed_service.app.models import Like

def test_toggle_like_creates_new(client, mock_db_session, test_video_id):
    # Лайка еще нет
    mock_db_session.scalar.return_value = None

    response = client.post(f"/videos/{test_video_id}/like")
    
    assert response.status_code == 200
    assert response.json() == {"liked": True}
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_toggle_like_removes_existing(client, mock_db_session, test_video_id, test_user_id):
    # Лайк уже существует
    existing_like = Like(user_id=uuid.UUID(test_user_id), video_id=test_video_id)
    mock_db_session.scalar.return_value = existing_like

    response = client.post(f"/videos/{test_video_id}/like")
    
    assert response.status_code == 200
    assert response.json() == {"liked": False}
    mock_db_session.delete.assert_called_once_with(existing_like)
    mock_db_session.commit.assert_called_once()