# MeetHub MVP Backend

1. Скопировать `.env.example` в `.env` и задать секреты.
2. Запустить `docker compose up --build`.
3. Использовать gateway:
   - `POST http://localhost:8080/auth/register`
   - `POST http://localhost:8080/auth/login`
   - `POST http://localhost:8080/upload/request`
   - `GET http://localhost:8080/feed/foryou`

