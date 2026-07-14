"""Unit tests for the file schemas / list mapping (no DB required)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.files import FileListItem, FileListResponse, FileUploadResponse


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
