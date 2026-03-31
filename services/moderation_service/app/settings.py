from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    internal_api_key: str
    admin_token: str
    feed_service_url: str

    model_config = SettingsConfigDict(env_prefix="MODERATION_", env_file=".env", extra="ignore")


settings = Settings()
