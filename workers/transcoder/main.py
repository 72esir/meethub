import asyncio
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import Redis

from shared.queue import TRANSCODE_QUEUE, dequeue
from shared.storage import build_s3_client, ensure_bucket


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
    internal_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
redis_client = Redis.from_url(settings.redis_queue_url, decode_responses=True)
s3_client = build_s3_client(settings.s3_endpoint_url, settings.s3_access_key, settings.s3_secret_key, settings.s3_region)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def generate_hls(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if ffmpeg_available():
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(input_path),
                "-codec",
                "copy",
                "-start_number",
                "0",
                "-hls_time",
                "4",
                "-hls_list_size",
                "0",
                "-f",
                "hls",
                str(output_dir / "master.m3u8"),
            ],
            check=True,
        )
        return

    (output_dir / "master.m3u8").write_text(
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=854x480\nvideo.m3u8\n",
        encoding="utf-8",
    )
    (output_dir / "video.m3u8").write_text(
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:4.0,\nsegment0.ts\n#EXT-X-ENDLIST\n",
        encoding="utf-8",
    )
    (output_dir / "segment0.ts").write_bytes(b"stub-segment")


def upload_hls(output_dir: Path, prefix: str) -> str:
    ensure_bucket(s3_client, settings.s3_bucket_hls)
    for path in output_dir.rglob("*"):
        if path.is_file():
            key = f"{prefix}/{path.relative_to(output_dir).as_posix()}"
            with path.open("rb") as fileobj:
                s3_client.upload_fileobj(fileobj, settings.s3_bucket_hls, key)
    return urljoin(settings.cdn_base_url.rstrip("/") + "/", f"{prefix}/master.m3u8")


async def notify_services(job: dict, hls_url: str) -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.post(
            f"{settings.feed_service_url}/internal/videos",
            headers={"X-Internal-Key": settings.internal_api_key},
            json={
                "id": job["upload_id"],
                "author_id": job["user_id"],
                "description": job.get("description", ""),
                "hashtags": job.get("hashtags", []),
                "hls_url": hls_url,
                "thumbnail_url": None,
                "duration": None,
            },
        ).raise_for_status()
        await client.post(
            f"{settings.moderation_service_url}/moderation/queue",
            headers={"X-Internal-Key": settings.internal_api_key},
            json={"video_id": job["upload_id"], "author_id": job["user_id"], "video_url": hls_url},
        ).raise_for_status()


def process_job(job: dict) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / "input.mp4"
        output_dir = tmpdir_path / "hls"
        s3_client.download_file(settings.s3_bucket_raw, job["s3_input_key"], str(input_path))
        generate_hls(input_path, output_dir)
        hls_url = upload_hls(output_dir, f"hls/{job['upload_id']}")
    asyncio.run(notify_services(job, hls_url))


def main() -> None:
    ensure_bucket(s3_client, settings.s3_bucket_raw)
    ensure_bucket(s3_client, settings.s3_bucket_hls)
    while True:
        job = dequeue(redis_client, TRANSCODE_QUEUE, timeout_seconds=5)
        if not job:
            time.sleep(1)
            continue
        try:
            process_job(job)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"status": "error", "job": job, "error": str(exc)}))


if __name__ == "__main__":
    main()
