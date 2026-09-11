from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any

from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import S3Settings


logger = logging.getLogger(__name__)


class S3Client:
    def __init__(
            self,
            settings: S3Settings
    ) -> None:
        self._client_config = {
            "aws_access_key_id": settings.access_key,
            "aws_secret_access_key": settings.secret_key,
            "region_name": settings.region_name,
        }
        self._session = get_session()
        self._settings = settings

    @asynccontextmanager
    async def _get_client(self, endpoint_url: str) -> AsyncIterator[Any]:
        async with self._session.create_client(
                self._settings.service_name,
                endpoint_url=endpoint_url,
                **self._client_config,
        ) as client:
            yield client

    async def ensure_bucket(self) -> None:
        """Create the configured bucket when it does not exist yet."""
        logger.info("Checking S3 bucket availability: bucket=%s", self._settings.bucket_name)
        async with self._get_client(self._settings.endpoint_url) as client:
            try:
                await client.head_bucket(Bucket=self._settings.bucket_name)
            except ClientError as error:
                error_code = error.response.get("Error", {}).get("Code")
                if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                await client.create_bucket(Bucket=self._settings.bucket_name)
                logger.info("S3 bucket created: bucket=%s", self._settings.bucket_name)

    async def upload_file(
            self,
            content: bytes,
            key: str,
            content_type: str,
    ) -> None:
        """Upload raw file content under the supplied object key."""
        async with self._get_client(self._settings.endpoint_url) as client:
            await client.put_object(
                Bucket=self._settings.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
            )

    async def generate_presigned_image_url(
            self,
            key: str,
            expire_seconds: int | None = None,
    ) -> str | None:
        """Generate a temporary browser-facing URL for an object."""

        try:
            async with self._get_client(self._settings.public_endpoint_url) as client:
                url = await client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": self._settings.bucket_name,
                        "Key": key,
                    },
                    ExpiresIn=(
                        expire_seconds
                        or self._settings.presigned_url_expire_seconds
                    ),
                )
                return url
        except (BotoCoreError, ClientError, OSError):
            logger.warning("Failed to generate an S3 image URL key=%s", key, exc_info=True)
            return None

    async def delete_file(self, key: str) -> None:
        """Delete an object without failing an already completed DB operation."""
        try:
            async with self._get_client(self._settings.endpoint_url) as client:
                await client.delete_object(
                    Bucket=self._settings.bucket_name,
                    Key=key,
                )
        except (BotoCoreError, ClientError, OSError):
            logger.warning("Failed to delete S3 object key=%s", key, exc_info=True)
