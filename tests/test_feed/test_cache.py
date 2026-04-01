import uuid
from datetime import datetime, timezone
from services.feed_service.app.models import Video, VideoStatus

def test_foryou_feed_populates_cache(client, mock_db_session, fake_redis, test_video_id):
    mock_video = Video(
        id=test_video_id,
        author_id=uuid.uuid4(),
        description="Test video",       
        hashtags=[],                    
        hls_url="test.m3u8",
        thumbnail_url="test.jpg",      
        duration=10,                    
        status=VideoStatus.approved,
        created_at=datetime.now(timezone.utc)
    )
    mock_db_session.scalars.return_value.all.return_value = [mock_video]
    
    assert fake_redis.llen("feed:foryou") == 0

    response = client.get("/feed/foryou?limit=10")
    
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    
    assert fake_redis.llen("feed:foryou") == 1
    assert fake_redis.lindex("feed:foryou", 0) == str(test_video_id)


def test_foryou_feed_reads_from_cache(client, mock_db_session, fake_redis, test_video_id, mocker):
    fake_redis.rpush("feed:foryou", str(test_video_id))
    
    mock_video = Video(
        id=test_video_id, 
        author_id=uuid.uuid4(), 
        description="Test video",       
        hashtags=[],                    
        hls_url="test", 
        thumbnail_url="test.jpg",      
        duration=10,                    
        status=VideoStatus.approved, 
        created_at=datetime.now(timezone.utc)
    )
    mocker.patch("services.feed_service.app.main.fetch_videos_by_ids", return_value=[mock_video])

    response = client.get("/feed/foryou")
    
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    mock_db_session.scalars.assert_not_called()