"""Tests for QdrantStore — uses mocks to avoid needing a live Qdrant instance."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.core.models import Chunk
from app.vectordb.qdrant_store import QdrantStore, _chunk_id_to_int


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_settings():
    settings = MagicMock()
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_collection = "test_col"
    return settings


def _make_chunk(idx: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"abc{idx:03d}",
        doc_id="doc1",
        doc_name="sample.pdf",
        doc_rel_path="documents/sample.pdf",
        text=f"chunk text {idx}",
        page=idx + 1,
        section=None,
        start_offset=idx * 100,
        end_offset=(idx + 1) * 100,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChunkIdToInt:
    def test_deterministic(self):
        assert _chunk_id_to_int("abc123") == _chunk_id_to_int("abc123")

    def test_different_ids_differ(self):
        assert _chunk_id_to_int("abc123") != _chunk_id_to_int("def456")

    def test_within_int63_range(self):
        val = _chunk_id_to_int("ffffffff")
        assert 0 <= val < 2**63


class TestQdrantStore:
    """Mock the QdrantClient at the module level where it is imported."""

    def _make_store_and_mock(self):
        """Return (store, mock_client_instance) with QdrantClient patched."""
        mock_client_instance = MagicMock()
        with patch("app.vectordb.qdrant_store.QdrantClient", return_value=mock_client_instance):
            settings = _make_settings()
            store = QdrantStore(settings)
        store._client = mock_client_instance
        return store, mock_client_instance

    def test_init_collection_creates_when_missing(self):
        store, mock_client = self._make_store_and_mock()
        mock_client.get_collections.return_value.collections = []

        store.init_collection(dimension=1536)

        mock_client.create_collection.assert_called_once()
        kwargs = mock_client.create_collection.call_args[1]
        assert kwargs["collection_name"] == "test_col"

    def test_init_collection_skips_if_exists(self):
        store, mock_client = self._make_store_and_mock()
        existing = MagicMock()
        existing.name = "test_col"
        mock_client.get_collections.return_value.collections = [existing]

        store.init_collection(dimension=1536)

        mock_client.create_collection.assert_not_called()

    def test_upsert_calls_client(self):
        store, mock_client = self._make_store_and_mock()
        chunks = [_make_chunk(i) for i in range(3)]
        vectors = [[0.1] * 4 for _ in range(3)]

        store.upsert(chunks, vectors)

        mock_client.upsert.assert_called_once()
        call_kwargs = mock_client.upsert.call_args[1]
        assert call_kwargs["collection_name"] == "test_col"
        assert len(call_kwargs["points"]) == 3

    def test_search_returns_payloads(self):
        store, mock_client = self._make_store_and_mock()

        mock_point = MagicMock()
        mock_point.payload = {
            "chunk_id": "abc001",
            "doc_name": "sample.pdf",
            "text": "hello",
        }
        mock_point.id = 1
        
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points.return_value = mock_response

        results = store.search([0.1, 0.2], top_k=5, filter=None)

        assert len(results) == 1
        payload, chunk_id = results[0]
        assert payload["doc_name"] == "sample.pdf"
        assert chunk_id == "abc001"

    def test_delete_by_doc_id_calls_client(self):
        store, mock_client = self._make_store_and_mock()

        store.delete_by_doc_id("doc1")

        mock_client.delete.assert_called_once()

    def test_delete_by_doc_id_handles_exception(self):
        store, mock_client = self._make_store_and_mock()
        mock_client.delete.side_effect = Exception("collection not found")

        # Should not raise — exception is silently caught
        store.delete_by_doc_id("doc1")

    def test_healthcheck_calls_get_collections(self):
        store, mock_client = self._make_store_and_mock()

        store.healthcheck()

        mock_client.get_collections.assert_called_once()

    def test_search_with_filter(self):
        store, mock_client = self._make_store_and_mock()

        mock_point = MagicMock()
        mock_point.payload = {"chunk_id": "abc", "doc_name": "d.pdf", "text": "t"}
        mock_point.id = 1
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points.return_value = mock_response

        filter_dict = {"must": [{"key": "doc_id", "match": {"value": "doc1"}}]}
        results = store.search([0.1], top_k=3, filter=filter_dict)

        assert len(results) == 1
        # Verify filter was passed
        call_kwargs = mock_client.query_points.call_args[1]
        assert call_kwargs["query_filter"] is not None

    def test_search_empty_payload(self):
        store, mock_client = self._make_store_and_mock()

        mock_point = MagicMock()
        mock_point.payload = None
        mock_point.id = 99
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points.return_value = mock_response

        results = store.search([0.1], top_k=1, filter=None)

        assert len(results) == 1
        payload, chunk_id = results[0]
        assert payload == {}
        assert chunk_id == "99"

    def test_upsert_large_batch_splits(self):
        store, mock_client = self._make_store_and_mock()
        chunks = [_make_chunk(i) for i in range(10)]
        vectors = [[0.1] * 4 for _ in range(10)]

        store.upsert(chunks, vectors, batch_size=3)

        # 10 items with batch_size=3 → 4 calls (3+3+3+1)
        assert mock_client.upsert.call_count == 4
