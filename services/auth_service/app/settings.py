from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str

    model_config = SettingsConfigDict(env_prefix="AUTH_", env_file=".env", extra="ignore")


settings = Settings()
