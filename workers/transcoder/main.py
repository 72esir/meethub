import time

from shared.queue import TRANSCODE_QUEUE, dequeue
from workers.transcoder.container import TranscoderContainer
from workers.transcoder.contracts import TranscodeJob
from workers.transcoder.gateways import log_event
from workers.transcoder.settings import settings


def main() -> None:
    container = TranscoderContainer.build(settings)
    container.transcode_service.bootstrap()
    while True:
        raw_job = dequeue(container.redis_client, TRANSCODE_QUEUE, timeout_seconds=5)
        if not raw_job:
            time.sleep(1)
            continue
        try:
            container.transcode_service.process(TranscodeJob.from_dict(raw_job))
        except Exception as exc:  # noqa: BLE001
            try:
                import asyncio

                asyncio.run(
                    container.transcode_service.publisher_gateway.update_upload_status(
                        TranscodeJob.from_dict(raw_job).upload_id,
                        "error",
                        str(exc),
                    )
                )
            except Exception:
                pass
            log_event("transcode.job.failed", job=raw_job, error=str(exc))


if __name__ == "__main__":
    main()
