"""
Тесты для shared/storage.py: build_s3_client, ensure_bucket, upload_fileobj.
Все обращения к boto3 мокируются — реальное S3-окружение не требуется.
"""
import io
from unittest.mock import MagicMock, patch, call

import pytest

from shared.storage import build_s3_client, ensure_bucket, upload_fileobj


# ──────────────────────────────────────────────
# build_s3_client
# ──────────────────────────────────────────────

class TestBuildS3Client:
    def test_returns_boto3_client(self):
        """build_s3_client возвращает клиент boto3.client('s3', ...)."""
        fake_client = MagicMock()
        with patch("boto3.client", return_value=fake_client) as mock_boto:
            result = build_s3_client("http://localhost:9000", "key", "secret", "us-east-1")

        mock_boto.assert_called_once_with(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            region_name="us-east-1",
        )
        assert result is fake_client

    def test_passes_correct_region(self):
        with patch("boto3.client", return_value=MagicMock()) as mock_boto:
            build_s3_client("http://ep", "ak", "sk", "eu-west-1")

        _, kwargs = mock_boto.call_args
        assert kwargs["region_name"] == "eu-west-1"


# ──────────────────────────────────────────────
# ensure_bucket
# ──────────────────────────────────────────────

class TestEnsureBucket:
    def test_creates_bucket_when_missing(self):
        """Если бакета нет — вызывается create_bucket."""
        client = MagicMock()
        client.list_buckets.return_value = {"Buckets": [{"Name": "other-bucket"}]}

        ensure_bucket(client, "new-bucket")

        client.create_bucket.assert_called_once_with(Bucket="new-bucket")

    def test_skips_creation_when_bucket_exists(self):
        """Если бакет уже есть — create_bucket НЕ вызывается."""
        client = MagicMock()
        client.list_buckets.return_value = {"Buckets": [{"Name": "existing-bucket"}]}

        ensure_bucket(client, "existing-bucket")

        client.create_bucket.assert_not_called()

    def test_empty_buckets_list(self):
        """Пустой список бакетов — должен создать нужный."""
        client = MagicMock()
        client.list_buckets.return_value = {"Buckets": []}

        ensure_bucket(client, "my-bucket")

        client.create_bucket.assert_called_once_with(Bucket="my-bucket")

    def test_no_buckets_key_in_response(self):
        """list_buckets может вернуть ответ без ключа 'Buckets'."""
        client = MagicMock()
        client.list_buckets.return_value = {}

        ensure_bucket(client, "my-bucket")

        client.create_bucket.assert_called_once_with(Bucket="my-bucket")


# ──────────────────────────────────────────────
# upload_fileobj
# ──────────────────────────────────────────────

class TestUploadFileobj:
    def test_uploads_with_content_type(self):
        """Если content_type задан, он передаётся в ExtraArgs."""
        client = MagicMock()
        fileobj = io.BytesIO(b"video bytes")

        upload_fileobj(client, "my-bucket", "key/video.mp4", fileobj, "video/mp4")

        client.upload_fileobj.assert_called_once_with(
            fileobj,
            "my-bucket",
            "key/video.mp4",
            ExtraArgs={"ContentType": "video/mp4"},
        )

    def test_uploads_without_content_type(self):
        """Если content_type не задан, ExtraArgs должен быть пустым словарём."""
        client = MagicMock()
        fileobj = io.BytesIO(b"data")

        upload_fileobj(client, "bucket", "key.bin", fileobj)

        client.upload_fileobj.assert_called_once_with(
            fileobj,
            "bucket",
            "key.bin",
            ExtraArgs={},
        )

    def test_passes_correct_bucket_and_key(self):
        client = MagicMock()
        fileobj = io.BytesIO(b"x")

        upload_fileobj(client, "target-bucket", "path/to/file.mp4", fileobj, "video/mp4")

        args = client.upload_fileobj.call_args[0]
        assert args[1] == "target-bucket"
        assert args[2] == "path/to/file.mp4"
