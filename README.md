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

Services now run Alembic migrations before startup.

Migration docs:

- [docs/MIGRATIONS.md](/c:/Users/asala/projects/python/meethub/docs/MIGRATIONS.md)

## Gateway

- API entrypoint: `http://localhost:8080`
- Health: `GET http://localhost:8080/healthz`
- Traefik dashboard: `http://127.0.0.1:8081/dashboard/`

## Port exposure

- Public entrypoint is only Traefik on `:8080`
- Direct service ports (`8001`-`8004`), PostgreSQL (`5433`-`5436`), Redis (`6379`, `6380`), MinIO (`9000`, `9001`) and Traefik dashboard (`8081`) are bound to `127.0.0.1` only
- Services communicate with each other over the internal Docker network; they do not need published ports for inter-service traffic

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
