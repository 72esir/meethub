# MeetHub MVP Backend

Backend monorepo for a TikTok-like MVP on `FastAPI`.

## Services

- `auth_service`
- `upload_service`
- `feed_service`
- `moderation_service`
- `transcoder_worker`

## Local stack

- PostgreSQL per service
- Redis for cache and queue
- MinIO for object storage
- Traefik as API gateway

## Run

1. Copy `.env.example` to `.env`
2. Start the stack:
   - `docker compose up --build`

## Gateway

- API entrypoint: `http://localhost:8080`
- Health: `GET http://localhost:8080/healthz`
- Traefik dashboard: `http://localhost:8081/dashboard/`

## Routed prefixes

- `/auth`
- `/upload`
- `/feed`
- `/videos`
- `/users`
- `/moderation`

## Example

- `POST http://localhost:8080/auth/register`
- `POST http://localhost:8080/auth/login`
- `POST http://localhost:8080/upload/request`
- `GET http://localhost:8080/feed/foryou`

## Smoke test

- Script: [scripts/smoke_test.ps1](/c:/Users/asala/projects/python/meethub/scripts/smoke_test.ps1)
- Docs: [docs/SMOKE_TEST.md](/c:/Users/asala/projects/python/meethub/docs/SMOKE_TEST.md)

Run example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1 -VideoPath "C:\Users\asala\OneDrive\Desktop\test.mp4"
```
