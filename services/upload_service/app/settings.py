from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    internal_api_key: str
    redis_queue_url: str
    s3_endpoint_url: str
    s3_public_endpoint_url: str | None = None
    s3_access_key: str
    s3_secret_key: str
    s3_region: str = "us-east-1"
    s3_bucket_raw: str
    s3_bucket_images: str = "images"
    cdn_base_url: str = "http://localhost:9000"
    feed_service_url: str = "http://feed_service:8000"

    model_config = SettingsConfigDict(env_prefix="UPLOAD_", env_file=".env", extra="ignore")


settings = Settings()
