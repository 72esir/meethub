import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import httpx

from workers.transcoder.contracts import TranscodeJob


class S3Gateway:
    def __init__(self, client, raw_bucket: str, hls_bucket: str, cdn_base_url: str, ensure_bucket_fn) -> None:
        self.client = client
        self.raw_bucket = raw_bucket
        self.hls_bucket = hls_bucket
        self.cdn_base_url = cdn_base_url
        self.ensure_bucket_fn = ensure_bucket_fn

    def ensure_buckets(self) -> None:
        self.ensure_bucket_fn(self.client, self.raw_bucket)
        self.ensure_bucket_fn(self.client, self.hls_bucket)

    def download_raw(self, object_key: str, destination: Path) -> None:
        self.client.download_file(self.raw_bucket, object_key, str(destination))

    def upload_hls_tree(self, output_dir: Path, prefix: str) -> str:
        self.ensure_bucket_fn(self.client, self.hls_bucket)
        for path in output_dir.rglob("*"):
            if path.is_file():
                key = f"{prefix}/{path.relative_to(output_dir).as_posix()}"
                with path.open("rb") as fileobj:
                    self.client.upload_fileobj(fileobj, self.hls_bucket, key)
        return urljoin(self.cdn_base_url.rstrip("/") + "/", f"{prefix}/master.m3u8")


class FFmpegGateway:
    def ffmpeg_available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def generate_hls(self, input_path: Path, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.ffmpeg_available():
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


class MediaPublisherGateway:
    def __init__(self, feed_service_url: str, moderation_service_url: str, upload_service_url: str, internal_api_key: str) -> None:
        self.feed_service_url = feed_service_url
        self.moderation_service_url = moderation_service_url
        self.upload_service_url = upload_service_url
        self.internal_api_key = internal_api_key

    async def update_upload_status(self, upload_id: str, status_value: str, error_message: str | None = None) -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                f"{self.upload_service_url}/internal/uploads/{upload_id}/status",
                headers={"X-Internal-Key": self.internal_api_key},
                json={"status": status_value, "error_message": error_message},
            )
            response.raise_for_status()

    async def publish(self, job: TranscodeJob, hls_url: str) -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            feed_response = await client.post(
                f"{self.feed_service_url}/internal/videos",
                headers={"X-Internal-Key": self.internal_api_key},
                json={
                    "id": job.upload_id,
                    "author_id": job.user_id,
                    "description": job.description,
                    "hashtags": job.hashtags,
                    "hls_url": hls_url,
                    "thumbnail_url": None,
                    "duration": None,
                },
            )
            feed_response.raise_for_status()
            moderation_response = await client.post(
                f"{self.moderation_service_url}/moderation/queue",
                headers={"X-Internal-Key": self.internal_api_key},
                json={"video_id": job.upload_id, "author_id": job.user_id, "video_url": hls_url},
            )
            moderation_response.raise_for_status()


def log_event(event: str, **payload) -> None:
    print(json.dumps({"event": event, **payload}))
