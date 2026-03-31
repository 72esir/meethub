from typing import BinaryIO

import boto3


def build_s3_client(endpoint_url: str, access_key: str, secret_key: str, region: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def ensure_bucket(client, bucket_name: str) -> None:
    existing = {bucket["Name"] for bucket in client.list_buckets().get("Buckets", [])}
    if bucket_name not in existing:
        client.create_bucket(Bucket=bucket_name)


def upload_fileobj(client, bucket: str, key: str, fileobj: BinaryIO, content_type: str | None = None) -> None:
    extra_args = {"ContentType": content_type} if content_type else {}
    client.upload_fileobj(fileobj, bucket, key, ExtraArgs=extra_args)
