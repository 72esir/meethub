import uuid
from datetime import datetime, timezone
from services.feed_service.app.models import Video, VideoStatus

def test_get_video_success(client, mock_db_session, test_video_id):
    mock_video = Video(
        id=test_video_id,
        author_id=uuid.uuid4(),
        description="Test video description",   
        hashtags=["test", "video"],             
        hls_url="http://example.com/hls.m3u8",
        thumbnail_url="http://example.com/thumb.jpg", 
        duration=15,                           
        status=VideoStatus.approved,
        created_at=datetime.now(timezone.utc)
    )
    mock_db_session.get.return_value = mock_video

    response = client.get(f"/videos/{test_video_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_video_id)
    assert data["status"] == "approved"
    mock_db_session.get.assert_called_once()

def test_get_video_not_found(client, mock_db_session):
    # Настраиваем мок БД: видео нет
    mock_db_session.get.return_value = None

    response = client.get(f"/videos/{uuid.uuid4()}")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "video not found"