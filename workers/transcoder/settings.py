from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_queue_url: str
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str = "us-east-1"
    s3_bucket_raw: str
    s3_bucket_hls: str
    cdn_base_url: str
    feed_service_url: str
    moderation_service_url: str
    upload_service_url: str
    internal_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
