"""Tests for app.rag.registry module."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.rag.registry import (
    clear_registry,
    load_registry,
    register_document,
    sync_registry_from_qdrant,
)


class TestLoadRegistry:
    def test_returns_empty_when_no_file(self, tmp_path):
        assert load_registry(tmp_path) == []

    def test_returns_entries_from_file(self, tmp_path):
        path = tmp_path / "doc_registry.json"
        path.write_text(json.dumps([{"doc_name": "a.pdf", "doc_id": "x"}]))
        entries = load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["doc_name"] == "a.pdf"

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        path = tmp_path / "doc_registry.json"
        path.write_text("not json!!!")
        assert load_registry(tmp_path) == []


class TestRegisterDocument:
    def test_adds_new_entry(self, tmp_path):
        register_document(tmp_path, doc_name="a.pdf", doc_id="d1", chunks=10)
        entries = load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["doc_name"] == "a.pdf"
        assert entries[0]["chunks"] == 10
        assert "indexed_at" in entries[0]

    def test_replaces_existing_entry_by_doc_id(self, tmp_path):
        register_document(tmp_path, doc_name="a.pdf", doc_id="d1", chunks=10)
        register_document(tmp_path, doc_name="a.pdf", doc_id="d1", chunks=20)
        entries = load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["chunks"] == 20

    def test_adds_pages_when_provided(self, tmp_path):
        register_document(
            tmp_path, doc_name="b.pdf", doc_id="d2", chunks=5, pages=12
        )
        entries = load_registry(tmp_path)
        assert entries[0]["pages"] == 12

    def test_creates_data_dir_if_missing(self, tmp_path):
        sub = tmp_path / "nested" / "dir"
        register_document(sub, doc_name="c.pdf", doc_id="d3", chunks=1)
        assert (sub / "doc_registry.json").exists()


class TestClearRegistry:
    def test_clears_all_entries(self, tmp_path):
        register_document(tmp_path, doc_name="a.pdf", doc_id="d1", chunks=10)
        register_document(tmp_path, doc_name="b.pdf", doc_id="d2", chunks=5)
        assert len(load_registry(tmp_path)) == 2

        clear_registry(tmp_path)
        assert load_registry(tmp_path) == []


def _fake_settings(tmp_path):
    s = MagicMock()
    s.qdrant_url = "http://localhost:6333"
    s.qdrant_collection = "documents"
    s.data_dir = tmp_path
    return s


class TestSyncRegistryFromQdrant:
    def test_backfills_from_qdrant(self, tmp_path):
        settings = _fake_settings(tmp_path)

        point1 = MagicMock()
        point1.payload = {"doc_id": "d1", "doc_name": "a.pdf", "page": 2}
        point2 = MagicMock()
        point2.payload = {"doc_id": "d1", "doc_name": "a.pdf", "page": 5}
        point3 = MagicMock()
        point3.payload = {"doc_id": "d2", "doc_name": "b.txt"}

        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            SimpleNamespace(name="documents")
        ]
        mock_client.scroll.return_value = ([point1, point2, point3], None)

        with patch("app.rag.registry.QdrantClient", return_value=mock_client):
            entries = sync_registry_from_qdrant(settings)

        assert len(entries) == 2
        by_id = {e["doc_id"]: e for e in entries}
        assert by_id["d1"]["chunks"] == 2
        assert by_id["d1"]["pages"] == 5
        assert by_id["d2"]["chunks"] == 1
        # also persisted to file
        assert len(load_registry(tmp_path)) == 2

    def test_returns_empty_when_collection_missing(self, tmp_path):
        settings = _fake_settings(tmp_path)
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = []

        with patch("app.rag.registry.QdrantClient", return_value=mock_client):
            entries = sync_registry_from_qdrant(settings)

        assert entries == []

    def test_returns_empty_on_connection_error(self, tmp_path):
        settings = _fake_settings(tmp_path)

        with patch("app.rag.registry.QdrantClient", side_effect=Exception("down")):
            entries = sync_registry_from_qdrant(settings)

        assert entries == []

    def test_handles_pagination(self, tmp_path):
        settings = _fake_settings(tmp_path)

        p1 = MagicMock()
        p1.payload = {"doc_id": "d1", "doc_name": "a.pdf"}
        p2 = MagicMock()
        p2.payload = {"doc_id": "d2", "doc_name": "b.pdf"}

        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            SimpleNamespace(name="documents")
        ]
        # First call returns page 1 with next_offset, second returns page 2
        mock_client.scroll.side_effect = [
            ([p1], "offset1"),
            ([p2], None),
        ]

        with patch("app.rag.registry.QdrantClient", return_value=mock_client):
            entries = sync_registry_from_qdrant(settings)

        assert len(entries) == 2
        assert mock_client.scroll.call_count == 2

    def test_skips_points_without_doc_id(self, tmp_path):
        settings = _fake_settings(tmp_path)

        p1 = MagicMock()
        p1.payload = {"doc_name": "orphan.pdf"}  # no doc_id
        p2 = MagicMock()
        p2.payload = {"doc_id": "d1", "doc_name": "a.pdf"}

        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [
            SimpleNamespace(name="documents")
        ]
        mock_client.scroll.return_value = ([p1, p2], None)

        with patch("app.rag.registry.QdrantClient", return_value=mock_client):
            entries = sync_registry_from_qdrant(settings)

        assert len(entries) == 1
        assert entries[0]["doc_id"] == "d1"
