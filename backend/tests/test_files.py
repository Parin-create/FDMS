"""Unit tests for the file schemas / list mapping / detail logic (no DB required)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.auth.principal import Principal
from app.models.file import StoredFile
from app.schemas.files import (
    FileDetailResponse,
    FileDownloadResponse,
    FileListItem,
    FileListResponse,
    FileUploadResponse,
)
from app.services.file_service import (
    FileService,
    StoredFileAlreadyDeletedError,
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
        created_at=datetime.now(tz=UTC),
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
    now = datetime.now(tz=UTC)
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
    now = datetime.now(tz=UTC)
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


def _service_with_storage(repo_result: StoredFile | None) -> FileService:
    # A non-None storage so get_download passes the storage guard.
    service = FileService(cast(Any, SimpleNamespace()), storage=cast(Any, SimpleNamespace()))
    service._repo = cast(Any, _FakeRepo(repo_result))
    return service


def test_get_download_missing_raises_not_found() -> None:
    service = _service_with_storage(None)
    with pytest.raises(StoredFileNotFoundError):
        asyncio.run(service.get_download(_principal(uuid4()), uuid4()))


def test_get_download_other_tenant_raises_forbidden() -> None:
    stored = StoredFile(id=uuid4(), tenant_id=uuid4())
    service = _service_with_storage(stored)
    with pytest.raises(StoredFileForbiddenError):
        asyncio.run(service.get_download(_principal(uuid4()), stored.id))


def test_file_download_response_shape() -> None:
    now = datetime.now(tz=UTC)
    resp = FileDownloadResponse(
        download_url="https://acct.blob.core.windows.net/documents/x.pdf?sig=redacted",
        expires_at=now,
        filename="report.pdf",
    )
    assert resp.filename == "report.pdf"
    assert resp.expires_at == now


# -- Soft delete (Sprint 4.4.3) --------------------------------------------


class _RecordingRepo:
    """Stub repo that returns a preset row and records mark_deleted calls."""

    def __init__(self, result: StoredFile | None) -> None:
        self._result = result
        self.marked: tuple[StoredFile, datetime] | None = None

    async def get_by_id(self, _file_id: object) -> StoredFile | None:
        return self._result

    async def mark_deleted(self, stored: StoredFile, when: datetime) -> None:
        stored.deleted_at = when
        self.marked = (stored, when)


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class _RecordingStorage:
    def __init__(self) -> None:
        self.deleted: tuple[str, str] | None = None

    async def delete(self, container: str, blob_name: str) -> bool:
        self.deleted = (container, blob_name)
        return True


def _delete_service(
    repo: _RecordingRepo, db: _FakeDb, storage: _RecordingStorage
) -> FileService:
    service = FileService(cast(Any, db), storage=cast(Any, storage))
    service._repo = cast(Any, repo)
    return service


def test_delete_missing_raises_not_found() -> None:
    service = _service_with_storage(None)
    with pytest.raises(StoredFileNotFoundError):
        asyncio.run(service.delete_file(_principal(uuid4()), uuid4()))


def test_delete_other_tenant_raises_forbidden() -> None:
    stored = StoredFile(id=uuid4(), tenant_id=uuid4())
    service = _service_with_storage(stored)
    with pytest.raises(StoredFileForbiddenError):
        asyncio.run(service.delete_file(_principal(uuid4()), stored.id))


def test_delete_already_deleted_raises_conflict() -> None:
    tenant = uuid4()
    stored = StoredFile(id=uuid4(), tenant_id=tenant)
    stored.deleted_at = datetime.now(tz=UTC)
    service = _service_with_storage(stored)
    with pytest.raises(StoredFileAlreadyDeletedError):
        asyncio.run(service.delete_file(_principal(tenant), stored.id))


def test_delete_soft_deletes_row_and_removes_blob() -> None:
    tenant = uuid4()
    stored = StoredFile(
        id=uuid4(),
        tenant_id=tenant,
        blob_container="documents",
        blob_name="deadbeef.pdf",
    )
    repo = _RecordingRepo(stored)
    db = _FakeDb()
    storage = _RecordingStorage()
    service = _delete_service(repo, db, storage)

    asyncio.run(service.delete_file(_principal(tenant), stored.id))

    assert stored.deleted_at is not None  # row stamped
    assert db.committed is True  # metadata committed (source of truth)
    assert storage.deleted == ("documents", "deadbeef.pdf")  # blob removed


def test_get_file_soft_deleted_raises_not_found() -> None:
    tenant = uuid4()
    stored = StoredFile(id=uuid4(), tenant_id=tenant)
    stored.deleted_at = datetime.now(tz=UTC)
    service = _service_with(stored)
    with pytest.raises(StoredFileNotFoundError):
        asyncio.run(service.get_file(_principal(tenant), stored.id))


# -- Search / filter / sort (Sprint 4.4.4) ---------------------------------


def test_escape_like_escapes_wildcards() -> None:
    from app.repositories.file_repository import _escape_like

    # Backslash first, then % and _ so literal wildcards can't be injected.
    assert _escape_like("a%b_c\\d") == "a\\%b\\_c\\\\d"


class _CapturingRepo:
    """Records the kwargs list_for_tenant is called with."""

    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    async def list_for_tenant(
        self, tenant_id: object, **kwargs: object
    ) -> tuple[list[object], int]:
        self.kwargs = {"tenant_id": tenant_id, **kwargs}
        return [], 0


def test_list_files_forwards_filters_and_sort_to_repo() -> None:
    repo = _CapturingRepo()
    service = FileService(cast(Any, SimpleNamespace()))
    service._repo = cast(Any, repo)
    tenant = uuid4()

    asyncio.run(
        service.list_files(
            _principal(tenant),
            limit=10,
            offset=20,
            descending=False,
            search="report",
            content_type="image/",
        )
    )

    assert repo.kwargs == {
        "tenant_id": tenant,
        "limit": 10,
        "offset": 20,
        "descending": False,
        "search": "report",
        "content_type": "image/",
    }
