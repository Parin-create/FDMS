"""Unit tests for the file schemas / list mapping / detail logic (no DB required)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.auth.principal import Principal
from app.models.file import StoredFile
from app.schemas.files import (
    FileDetailResponse,
    FileListItem,
    FileListResponse,
    FileUploadResponse,
)
from app.services.file_service import (
    FileService,
    StoredFileForbiddenError,
    StoredFileNotFoundError,
)


def _fake_stored_file() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        original_filename="report.pdf",
        content_type="application/pdf",
        size_bytes=482913,
        blob_name="deadbeef.pdf",
        etag='"0x8DC"',
        uploaded_by_id=uuid4(),
        created_at=datetime.now(tz=timezone.utc),
    )


def test_file_list_item_maps_from_stored_file() -> None:
    item = FileListItem.model_validate(_fake_stored_file())
    assert item.original_filename == "report.pdf"
    assert item.size_bytes == 482913
    assert item.etag == '"0x8DC"'


def test_file_list_response_echoes_pagination() -> None:
    response = FileListResponse(
        items=[FileListItem.model_validate(_fake_stored_file())],
        total=1,
        limit=20,
        offset=0,
    )
    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
    assert len(response.items) == 1


def test_upload_response_requires_id_and_created_at() -> None:
    now = datetime.now(tz=timezone.utc)
    resp = FileUploadResponse(
        id=uuid4(),
        container="documents",
        blob_name="deadbeef.pdf",
        original_filename="report.pdf",
        size=123,
        content_type="application/pdf",
        etag=None,
        created_at=now,
    )
    assert resp.container == "documents"
    assert resp.created_at == now


def test_file_detail_response_includes_status() -> None:
    now = datetime.now(tz=timezone.utc)
    detail = FileDetailResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        original_filename="report.pdf",
        content_type="application/pdf",
        size_bytes=123,
        blob_container="documents",
        blob_name="deadbeef.pdf",
        uploaded_by="user@example.com",
        status="available",
        created_at=now,
        updated_at=now,
    )
    assert detail.status == "available"
    assert detail.uploaded_by == "user@example.com"


class _FakeRepo:
    """Stub FileRepository returning a preset row from get_by_id."""

    def __init__(self, result: StoredFile | None) -> None:
        self._result = result

    async def get_by_id(self, _file_id: object) -> StoredFile | None:
        return self._result


def _principal(tenant_id: object) -> Principal:
    return cast(Principal, SimpleNamespace(tenant_id=tenant_id))


def _service_with(repo_result: StoredFile | None) -> FileService:
    service = FileService(cast(Any, SimpleNamespace()))
    service._repo = cast(Any, _FakeRepo(repo_result))
    return service


def test_get_file_missing_raises_not_found() -> None:
    service = _service_with(None)
    with pytest.raises(StoredFileNotFoundError):
        asyncio.run(service.get_file(_principal(uuid4()), uuid4()))


def test_get_file_other_tenant_raises_forbidden() -> None:
    stored = StoredFile(id=uuid4(), tenant_id=uuid4())  # belongs to a different tenant
    service = _service_with(stored)
    with pytest.raises(StoredFileForbiddenError):
        asyncio.run(service.get_file(_principal(uuid4()), stored.id))
