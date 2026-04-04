# Smoke Test

This project includes a PowerShell smoke test for the main MVP flow:

1. Health and readiness checks
2. User registration
3. Upload session creation
4. Binary upload to MinIO via presigned URL
5. Upload completion
6. Polling upload status until `ready`
7. Polling moderation queue
8. Moderation approve
9. Polling `feed/foryou`
10. Video read / like / view checks

## Script

- Script path: [scripts/smoke_test.ps1](/c:/Users/asala/projects/python/meethub/scripts/smoke_test.ps1)

## Prerequisites

- Docker stack is running:
  - `docker compose up -d`
- All service readiness endpoints return `200`
- You have a local MP4 file for upload

## Run

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1 -VideoPath "C:\Users\asala\OneDrive\Desktop\test.mp4"
```

## Optional parameters

- `-GatewayUrl` default: `http://localhost:8080`
- `-AuthUrl` default: `http://localhost:8001`
- `-UploadUrl` default: `http://localhost:8002`
- `-FeedUrl` default: `http://localhost:8003`
- `-ModerationUrl` default: `http://localhost:8004`
- `-AdminToken` default: `123`
- `-UploadPollAttempts` default: `20`
- `-UploadPollDelaySeconds` default: `3`
- `-ModerationPollAttempts` default: `20`
- `-ModerationPollDelaySeconds` default: `3`
- `-FeedPollAttempts` default: `20`
- `-FeedPollDelaySeconds` default: `3`

## Expected result

The script returns an object like:

```powershell
user_id       : ...
upload_id     : ...
video_id      : ...
moderation_id : ...
feed_status   : ok
upload_status : ready
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

## Useful logs

```powershell
docker compose logs --tail 200 auth_service upload_service feed_service moderation_service transcoder_worker gateway
```
