import asyncio
import tempfile
from pathlib import Path

from workers.transcoder.contracts import TranscodeJob
from workers.transcoder.gateways import log_event


class TranscodeService:
    def __init__(self, *, s3_gateway, ffmpeg_gateway, publisher_gateway) -> None:
        self.s3_gateway = s3_gateway
        self.ffmpeg_gateway = ffmpeg_gateway
        self.publisher_gateway = publisher_gateway

    def bootstrap(self) -> None:
        self.s3_gateway.ensure_buckets()

    def process(self, job: TranscodeJob) -> None:
        log_event("transcode.job.received", upload_id=job.upload_id, user_id=job.user_id, s3_input_key=job.s3_input_key)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_path = tmpdir_path / "input.mp4"
            output_dir = tmpdir_path / "hls"

            self.s3_gateway.download_raw(job.s3_input_key, input_path)
            log_event("transcode.source.downloaded", upload_id=job.upload_id, path=str(input_path))

            self.ffmpeg_gateway.generate_hls(input_path, output_dir)
            log_event("transcode.hls.generated", upload_id=job.upload_id, output_dir=str(output_dir))

            hls_url = self.s3_gateway.upload_hls_tree(output_dir, f"hls/{job.upload_id}")
            log_event("transcode.hls.uploaded", upload_id=job.upload_id, hls_url=hls_url)

        asyncio.run(self.publisher_gateway.publish(job, hls_url))
        log_event("transcode.publish.completed", upload_id=job.upload_id, hls_url=hls_url)
