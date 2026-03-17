"""Tests for api/ingest.py."""
from __future__ import annotations

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
        assert "index failed" in resp.json()["detail"]
