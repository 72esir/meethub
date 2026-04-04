from dataclasses import dataclass

from redis import Redis

from shared.storage import build_s3_client, ensure_bucket
from workers.transcoder.application.service import TranscodeService
from workers.transcoder.gateways import FFmpegGateway, MediaPublisherGateway, S3Gateway
from workers.transcoder.settings import Settings


@dataclass(slots=True)
class TranscoderContainer:
    settings: Settings
    redis_client: Redis
    transcode_service: TranscodeService

    @classmethod
    def build(cls, settings: Settings) -> "TranscoderContainer":
        redis_client = Redis.from_url(settings.redis_queue_url, decode_responses=True)
        s3_client = build_s3_client(
            settings.s3_endpoint_url,
            settings.s3_access_key,
            settings.s3_secret_key,
            settings.s3_region,
        )
        service = TranscodeService(
            s3_gateway=S3Gateway(
                client=s3_client,
                raw_bucket=settings.s3_bucket_raw,
                hls_bucket=settings.s3_bucket_hls,
                cdn_base_url=settings.cdn_base_url,
                ensure_bucket_fn=ensure_bucket,
            ),
            ffmpeg_gateway=FFmpegGateway(),
            publisher_gateway=MediaPublisherGateway(
                feed_service_url=settings.feed_service_url,
                moderation_service_url=settings.moderation_service_url,
                upload_service_url=settings.upload_service_url,
                internal_api_key=settings.internal_api_key,
            ),
        )
        return cls(settings=settings, redis_client=redis_client, transcode_service=service)
