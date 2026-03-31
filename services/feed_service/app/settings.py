from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    internal_api_key: str
    redis_cache_url: str

    model_config = SettingsConfigDict(env_prefix="FEED_", env_file=".env", extra="ignore")


settings = Settings()
