import asyncio
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from sadu.shared.config import Settings, get_settings

PRESIGNED_URL_TTL_S = 300


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    def presigned_url(self, key: str) -> str: ...


def new_object_key(prefix: str, extension: str) -> str:
    """Random keys only: visitor file names never reach storage."""
    return f"{prefix}/{uuid4().hex}.{extension}"


class S3ObjectStore:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = _s3_client(settings, settings.s3_endpoint_url)
        self._signing_client = _s3_client(
            settings, settings.s3_public_endpoint_url or settings.s3_endpoint_url
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        body: bytes = await asyncio.to_thread(response["Body"].read)
        return body

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str) -> str:
        url: str = self._signing_client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=PRESIGNED_URL_TTL_S
        )
        return url

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
        except ClientError:
            await asyncio.to_thread(self._client.create_bucket, Bucket=self._bucket)


def _s3_client(settings: Settings, endpoint_url: str):  # type: ignore[no-untyped-def]  # boto3 ships no types
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4", connect_timeout=5, read_timeout=10, retries={"max_attempts": 2}
        ),
    )


@lru_cache
def get_object_store() -> S3ObjectStore:
    return S3ObjectStore(get_settings())
