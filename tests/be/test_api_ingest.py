"""Tests for api/ingest.py."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.models import IngestResponse


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


class TestReindexEndpoint:
    def test_reindex_success(self, client):
        fake_settings = MagicMock()
        fake_result = IngestResponse(status="ok", indexed=10, errors=[])

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_directory", return_value=fake_result),
        ):
            resp = client.post("/ingest/reindex")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["indexed"] == 10

    def test_reindex_failure_returns_500(self, client):
        fake_settings = MagicMock()

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_directory", side_effect=RuntimeError("fail")),
        ):
            resp = client.post("/ingest/reindex")

        assert resp.status_code == 500
        assert "fail" in resp.json()["detail"]


class TestUploadEndpoint:
    def test_upload_txt_success(self, client, tmp_path):
        fake_settings = MagicMock()
        fake_settings.documents_dir = tmp_path
        fake_result = IngestResponse(status="ok", indexed=5, errors=[])

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_file", return_value=fake_result),
        ):
            resp = client.post(
                "/ingest/upload",
                files={"file": ("test.txt", BytesIO(b"hello world"), "text/plain")},
            )

        assert resp.status_code == 200
        assert resp.json()["indexed"] == 5

    def test_upload_pdf_success(self, client, tmp_path):
        fake_settings = MagicMock()
        fake_settings.documents_dir = tmp_path
        fake_result = IngestResponse(status="ok", indexed=3, errors=[])

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_file", return_value=fake_result),
        ):
            resp = client.post(
                "/ingest/upload",
                files={"file": ("doc.pdf", BytesIO(b"%PDF-fake"), "application/pdf")},
            )

        assert resp.status_code == 200

    def test_upload_unsupported_type_returns_415(self, client):
        fake_settings = MagicMock()

        with patch("app.api.ingest.get_settings", return_value=fake_settings):
            resp = client.post(
                "/ingest/upload",
                files={"file": ("image.png", BytesIO(b"\x89PNG"), "image/png")},
            )

        assert resp.status_code == 415
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_docx_success(self, client, tmp_path):
        fake_settings = MagicMock()
        fake_settings.documents_dir = tmp_path
        fake_result = IngestResponse(status="ok", indexed=1, errors=[])

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_file", return_value=fake_result),
        ):
            resp = client.post(
                "/ingest/upload",
                files={"file": ("doc.docx", BytesIO(b"fake"), "application/vnd.openxmlformats")},
            )

        assert resp.status_code == 200

    def test_upload_index_failure_returns_500(self, client, tmp_path):
        fake_settings = MagicMock()
        fake_settings.documents_dir = tmp_path

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_file", side_effect=RuntimeError("index failed")),
        ):
            resp = client.post(
                "/ingest/upload",
                files={"file": ("test.txt", BytesIO(b"data"), "text/plain")},
            )

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Upload failed"


class TestListDocumentsEndpoint:
    def test_returns_empty_list(self, client):
        fake_settings = MagicMock()
        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.load_registry", return_value=[]),
            patch("app.api.ingest.sync_registry_from_qdrant", return_value=[]),
        ):
            resp = client.get("/ingest/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_registered_docs(self, client):
        fake_settings = MagicMock()
        entries = [
            {
                "doc_name": "a.pdf",
                "doc_id": "d1",
                "chunks": 10,
                "pages": 3,
                "indexed_at": "2024-01-01T00:00:00+00:00",
            }
        ]
        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.load_registry", return_value=entries),
        ):
            resp = client.get("/ingest/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["doc_name"] == "a.pdf"
        assert body[0]["chunks"] == 10

    def test_falls_back_to_qdrant_sync(self, client):
        """When registry is empty, syncs from Qdrant."""
        fake_settings = MagicMock()
        synced = [
            {
                "doc_name": "existing.pdf",
                "doc_id": "d99",
                "chunks": 7,
                "pages": None,
                "indexed_at": "2024-06-01T00:00:00+00:00",
            }
        ]
        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.load_registry", return_value=[]),
            patch("app.api.ingest.sync_registry_from_qdrant", return_value=synced),
        ):
            resp = client.get("/ingest/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["doc_name"] == "existing.pdf"


class TestReindexStreamEndpoint:
    def test_streams_sse_events(self, client):
        fake_settings = MagicMock()

        def fake_iter(settings):
            yield {"type": "start", "total": 1}
            yield {"type": "progress", "current": 1, "total": 1, "doc_name": "a.pdf"}
            yield {"type": "done", "indexed": 5, "errors": []}

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_directory_iter", side_effect=fake_iter),
        ):
            resp = client.post("/ingest/reindex/stream")

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        lines = resp.text.strip().split("\n\n")
        events = [json.loads(line.removeprefix("data: ")) for line in lines]
        assert events[0]["type"] == "start"
        assert events[1]["type"] == "progress"
        assert events[2]["type"] == "done"

    def test_streams_error_on_exception(self, client):
        fake_settings = MagicMock()

        def exploding_iter(settings):
            raise RuntimeError("boom")

        with (
            patch("app.api.ingest.get_settings", return_value=fake_settings),
            patch("app.api.ingest.index_directory_iter", side_effect=exploding_iter),
        ):
            resp = client.post("/ingest/reindex/stream")

        assert resp.status_code == 200
        event = json.loads(resp.text.strip().removeprefix("data: "))
        assert event["type"] == "error"
        assert event["message"] == "Reindex failed"
