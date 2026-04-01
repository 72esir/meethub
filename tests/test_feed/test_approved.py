import uuid
from services.feed_service.app.models import Video, VideoStatus

def test_internal_update_status_approved(client, mock_db_session, fake_redis, test_video_id):
    author_id = uuid.uuid4()
    mock_video = Video(id=test_video_id, author_id=author_id, status=VideoStatus.moderation_pending)
    mock_db_session.get.return_value = mock_video
    
    follower_1 = uuid.uuid4()
    follower_2 = uuid.uuid4()
    mock_db_session.scalars.return_value.all.return_value = [follower_1, follower_2]

    response = client.put(f"/internal/videos/{test_video_id}/status", json={"status": "approved"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "approved"}
    
    assert fake_redis.llen("feed:foryou") == 1
    assert fake_redis.llen(f"feed:following:{follower_1}") == 1
    assert fake_redis.llen(f"feed:following:{follower_2}") == 1