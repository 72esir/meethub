# Migrations

The project now uses Alembic for every service that owns a PostgreSQL database:

- `auth`
- `upload`
- `feed`
- `moderation`

Migration directories:

- [migrations/auth](/c:/Users/asala/projects/python/meethub/migrations/auth)
- [migrations/upload](/c:/Users/asala/projects/python/meethub/migrations/upload)
- [migrations/feed](/c:/Users/asala/projects/python/meethub/migrations/feed)
- [migrations/moderation](/c:/Users/asala/projects/python/meethub/migrations/moderation)

## How it works

- Each API service runs `python scripts/run_migrations.py <service>` before `uvicorn`
- On a fresh database, Alembic applies `upgrade head`
- On an existing local database created by old `create_all()` startup logic, the runner stamps `head` if all expected tables already exist

This makes the transition from startup DDL to Alembic safe for the current local MVP setup.

## Manual run

Examples:

```powershell
python .\scripts\run_migrations.py auth
python .\scripts\run_migrations.py upload
python .\scripts\run_migrations.py feed
python .\scripts\run_migrations.py moderation
```

## Rebuild after migration changes

```powershell
docker compose build auth_service upload_service feed_service moderation_service
docker compose up -d auth_service upload_service feed_service moderation_service
```

## Notes

- Startup `create_all()` and ad-hoc `ALTER TABLE` logic were removed from services
- Schema changes should now go through Alembic revisions
- The current repository contains baseline `0001_initial` revisions for all four services
