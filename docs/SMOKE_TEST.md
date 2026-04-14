# Smoke Test

This project includes a PowerShell smoke test for the main MVP flow:

1. Health and readiness checks
2. Author user registration
3. Viewer user registration
4. Upload session creation
5. Binary upload to MinIO via presigned URL
6. Upload completion
7. Polling upload status until `ready`
8. Polling moderation queue
9. Moderation approve
10. Polling `feed/foryou`
11. Validation of video location metadata in feed and video endpoints
12. Video read / like / view checks from another user
13. Follow / follow-status / followers / following / unfollow checks
14. Optional image upload and feed visibility checks when `-ImagePath` is provided

## Script

- Script path: [scripts/smoke_test.ps1](/c:/Users/asala/projects/python/meethub/scripts/smoke_test.ps1)

## Prerequisites

- Docker stack is running:
  - `docker compose up -d`
- All service readiness endpoints return `200`
- You have a local MP4 file for upload
- Direct service ports used by the smoke test are intentionally bound to `127.0.0.1` only

## Run

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1 -VideoPath "C:\...\test.mp4"
```

## Optional parameters

- `-GatewayUrl` default: `http://localhost:8080`
- `-AuthUrl` default: `http://localhost:8001`
- `-UploadUrl` default: `http://localhost:8002`
- `-FeedUrl` default: `http://localhost:8003`
- `-ModerationUrl` default: `http://localhost:8004`
- `-AdminToken` default: `123`
- `-ImagePath` optional local image file for image upload checks
- `-UploadPollAttempts` default: `20`
- `-UploadPollDelaySeconds` default: `3`
- `-ModerationPollAttempts` default: `20`
- `-ModerationPollDelaySeconds` default: `3`
- `-FeedPollAttempts` default: `20`
- `-FeedPollDelaySeconds` default: `3`

## Expected result

The script returns an object like:

```powershell
author_user_id : ...
viewer_user_id : ...
upload_id      : ...
video_id       : ...
moderation_id  : ...
feed_status    : ok
follow_status  : ok
upload_status  : ready
image_status   : skipped
```

## Failure points

- `health` or `ready` failed:
  - one of the services or dependencies is not ready
- upload stuck before `ready`:
  - inspect `upload_service` and `transcoder_worker` logs
- moderation item not created:
  - inspect `transcoder_worker` and `moderation_service` logs
- video not appearing in feed:
  - inspect `feed_service` and moderation approval flow
- follow status mismatch or missing users in followers/following:
  - inspect `feed_service` logs and follow graph endpoints

## What it validates

- `auth_service`:
  - registration
  - token issuance
  - authenticated profile fetch
- `upload_service`:
  - upload session creation
  - image upload session creation when `-ImagePath` is provided
  - completion callback
  - upload status polling
  - location metadata acceptance
- `transcoder_worker`:
  - queue consumption
  - HLS generation
  - internal callbacks to upload/feed/moderation
- `moderation_service`:
  - pending queue creation
  - approve flow
- `feed_service`:
  - approved video visibility in `for you`
  - image visibility in `for you` when `-ImagePath` is provided
  - location metadata preservation on video publish
  - video metadata read
  - like and view endpoints
  - author videos list
  - follow graph endpoints

## Useful logs

```powershell
docker compose logs --tail 200 auth_service upload_service feed_service moderation_service transcoder_worker gateway
```
