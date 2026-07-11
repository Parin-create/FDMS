"""Azure Blob Storage service layer.

An enterprise, async wrapper around the official Azure Storage Blob SDK
(``azure-storage-blob``), used for all document/thumbnail/temp object I/O.

Design (Azure Well-Architected):
- **Security:** credentials are never hard-coded. The connection string comes from
  ``Settings`` (``.env`` locally, Key Vault in Azure). An account URL + managed
  identity (``DefaultAzureCredential``) is supported as a best-practice alternative.
- **Reliability:** the SDK's built-in exponential-backoff retry policy is configured
  via ``azure_storage_max_retries`` to absorb transient failures.
- **Performance:** async client (``azure.storage.blob.aio``) with chunked/concurrent
  transfers for large-file streaming; a single ``BlobServiceClient`` is reused for the
  process and closed at shutdown.
- **Operational excellence:** every operation emits structured logs (never content).

Container names are configurable and addressed by *logical* key ("documents",
"thumbnails", "temp"), decoupling call sites from the physical container names.
"""

from __future__ import annotations

import mimetypes
from collections.abc import AsyncIterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CONTENT_TYPE = "application/octet-stream"
# 4 MiB transfer chunking / block size for large-file streaming.
_MAX_CONCURRENCY = 4

# Accepts bytes or an (async) stream of byte chunks for large-file streaming uploads.
UploadData = bytes | AsyncIterable[bytes]


class StorageError(Exception):
    """Base class for storage-service errors."""


class StorageNotConfiguredError(StorageError):
    """Raised when no storage credentials are configured."""


def guess_content_type(filename: str, fallback: str = DEFAULT_CONTENT_TYPE) -> str:
    """Best-effort MIME type from a filename."""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or fallback


@dataclass(slots=True)
class BlobUploadResult:
    container: str
    name: str
    size: int
    content_type: str
    etag: str | None


@dataclass(slots=True)
class BlobInfo:
    name: str
    size: int | None
    content_type: str | None
    last_modified: datetime | None


class BlobStorageService:
    """Async facade over Azure Blob Storage."""

    def __init__(
        self,
        client: Any,
        containers: Mapping[str, str],
        *,
        credential: Any = None,
    ) -> None:
        self._client = client
        self._containers = dict(containers)
        self._credential = credential

    # -- construction -------------------------------------------------------
    @classmethod
    def from_settings(cls, settings: Settings) -> BlobStorageService:
        """Build a service from Settings, or raise ``StorageNotConfiguredError``."""
        from azure.storage.blob.aio import BlobServiceClient

        client_kwargs: dict[str, Any] = {"retry_total": settings.azure_storage_max_retries}

        if settings.azure_storage_connection_string:
            client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string, **client_kwargs
            )
            return cls(client, settings.blob_containers)

        if settings.azure_storage_account_url:
            from azure.identity.aio import DefaultAzureCredential

            credential = DefaultAzureCredential()
            client = BlobServiceClient(
                settings.azure_storage_account_url, credential=credential, **client_kwargs
            )
            return cls(client, settings.blob_containers, credential=credential)

        raise StorageNotConfiguredError("Azure Blob Storage is not configured")

    # -- helpers ------------------------------------------------------------
    def _blob(self, container: str, blob_name: str) -> Any:
        actual = self._containers.get(container, container)
        return self._client.get_container_client(actual).get_blob_client(blob_name)

    # -- operations ---------------------------------------------------------
    async def upload(
        self,
        container: str,
        blob_name: str,
        data: UploadData,
        *,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
        overwrite: bool = True,
    ) -> BlobUploadResult:
        """Upload bytes or a byte stream; returns the stored blob's properties."""
        from azure.storage.blob import ContentSettings

        resolved_type = content_type or guess_content_type(blob_name)
        blob = self._blob(container, blob_name)
        logger.info(
            "blob.upload_started",
            container=container,
            blob=blob_name,
            content_type=resolved_type,
        )
        try:
            await blob.upload_blob(
                data,
                overwrite=overwrite,
                content_settings=ContentSettings(content_type=resolved_type),
                metadata=dict(metadata) if metadata else None,
                max_concurrency=_MAX_CONCURRENCY,
            )
            props = await blob.get_blob_properties()
        except Exception:
            logger.exception("blob.upload_failed", container=container, blob=blob_name)
            raise
        logger.info(
            "blob.upload_succeeded", container=container, blob=blob_name, size=props.size
        )
        return BlobUploadResult(container, blob_name, props.size, resolved_type, props.etag)

    async def download_stream(self, container: str, blob_name: str) -> Any:
        """Return a ``StorageStreamDownloader`` for chunked/streamed download."""
        blob = self._blob(container, blob_name)
        logger.info("blob.download_started", container=container, blob=blob_name)
        return await blob.download_blob(max_concurrency=_MAX_CONCURRENCY)

    async def download_bytes(self, container: str, blob_name: str) -> bytes:
        """Download the whole blob into memory (small files only)."""
        downloader = await self.download_stream(container, blob_name)
        data: bytes = await downloader.readall()
        return data

    async def delete(self, container: str, blob_name: str) -> bool:
        """Delete a blob; returns False if it did not exist."""
        from azure.core.exceptions import ResourceNotFoundError

        blob = self._blob(container, blob_name)
        try:
            await blob.delete_blob()
        except ResourceNotFoundError:
            logger.info("blob.delete_missing", container=container, blob=blob_name)
            return False
        logger.info("blob.deleted", container=container, blob=blob_name)
        return True

    async def exists(self, container: str, blob_name: str) -> bool:
        """Return whether a blob exists."""
        return bool(await self._blob(container, blob_name).exists())

    async def list_blobs(
        self, container: str, *, name_starts_with: str | None = None
    ) -> list[BlobInfo]:
        """List blobs in a container, optionally filtered by name prefix."""
        actual = self._containers.get(container, container)
        container_client = self._client.get_container_client(actual)
        results: list[BlobInfo] = []
        async for item in container_client.list_blobs(name_starts_with=name_starts_with):
            content_type = (
                item.content_settings.content_type if item.content_settings else None
            )
            results.append(
                BlobInfo(item.name, item.size, content_type, item.last_modified)
            )
        return results

    async def get_metadata(self, container: str, blob_name: str) -> dict[str, str]:
        """Return a blob's user-defined metadata."""
        props = await self._blob(container, blob_name).get_blob_properties()
        return dict(props.metadata or {})

    async def set_metadata(
        self, container: str, blob_name: str, metadata: Mapping[str, str]
    ) -> None:
        """Replace a blob's user-defined metadata."""
        await self._blob(container, blob_name).set_blob_metadata(dict(metadata))
        logger.info("blob.metadata_updated", container=container, blob=blob_name)

    async def close(self) -> None:
        """Close the underlying client (and credential, if any)."""
        await self._client.close()
        if self._credential is not None:
            await self._credential.close()


# -- process-wide singleton + lifecycle ------------------------------------
_service: BlobStorageService | None = None


def get_storage_service(settings: Settings | None = None) -> BlobStorageService:
    """Return the process-wide storage service, creating it on first use."""
    global _service
    if _service is None:
        _service = BlobStorageService.from_settings(settings or get_settings())
        logger.info("blob.service_initialised")
    return _service


async def close_storage_service() -> None:
    """Dispose the storage service (call on application shutdown)."""
    global _service
    if _service is not None:
        await _service.close()
        _service = None
        logger.info("blob.service_closed")
