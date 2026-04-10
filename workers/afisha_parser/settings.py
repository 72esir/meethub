from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    city: str = "moscow"
    feed_service_url: str = "http://localhost:8003"
    internal_api_key: str = "changeme"
    # UUID пользователя-бота, от имени которого публикуются события
    bot_user_id: str = "00000000-0000-0000-0000-000000000001"
    # Сколько мероприятий тянуть за один запуск
    events_limit: int = 50
    # Файл-кеш уже обработанных ID (дедупликация)
    seen_ids_path: str = ".parsed_ids.json"

    model_config = {"env_prefix": "AFISHA_", "extra": "ignore"}


settings = Settings()
