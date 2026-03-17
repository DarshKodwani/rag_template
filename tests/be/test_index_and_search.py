"""Integration tests for the full index → search flow.

These tests require a running Qdrant instance (docker compose up -d).
They are marked with @pytest.mark.integration and skipped automatically
when Qdrant is unavailable.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.core.models import Chunk


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _fake_settings(tmp_path: Path):
    settings = MagicMock()
    settings.azure_openai_endpoint = "https://fake.openai.azure.com/"
    settings.azure_openai_api_key = "fake-key"
    settings.azure_openai_api_version = "2024-02-01"
    settings.azure_openai_chat_deployment = "gpt-4o"
    settings.azure_openai_embedding_deployment = "text-embedding-3-small"
    
    settings.openai_api_key = "fake-openai-key"
    settings.openai_base_url = "https://api.openai.com/v1"
    settings.openai_chat_model = "gpt-4o"
    settings.openai_embedding_model = "text-embedding-3-small"

    settings.qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    settings.qdrant_collection = "test_integration"
    settings.chunk_size = 200
    settings.chunk_overlap = 30
    settings.top_k = 3
    settings.documents_dir = tmp_path / "documents"
    settings.data_dir = tmp_path / "data"
    
    settings.azure_keys_present = True
    settings.openai_keys_present = True
    settings.any_keys_present = True
    return settings


def _qdrant_available(url: str) -> bool:
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=url)
        client.get_collections()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Unit-level test (no Qdrant, mocked embeddings)
# ---------------------------------------------------------------------------


class TestIndexFileUnit:
    """Unit tests for indexing a file with all external calls mocked."""

    def test_index_txt_file(self, tmp_path):
        from app.rag.indexing import index_file

        # Create a sample text document
        doc = tmp_path / "sample.txt"
        doc.write_text("This is a test document.\n" * 20, encoding="utf-8")

        settings = _fake_settings(tmp_path)
        settings.documents_dir = tmp_path

        fake_vector = [0.1] * 1536
        with (
            patch("app.rag.indexing._embed", return_value=[fake_vector]),
            patch("app.rag.indexing.QdrantStore") as mock_store_cls,
        ):
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store

            result = index_file(doc, settings)

        assert result.indexed > 0
        assert result.status == "ok"
        mock_store.upsert.assert_called_once()

    def test_index_empty_file_returns_zero(self, tmp_path):
        from app.rag.indexing import index_file

        doc = tmp_path / "empty.txt"
        doc.write_text("", encoding="utf-8")

        settings = _fake_settings(tmp_path)
        settings.documents_dir = tmp_path

        with (
            patch("app.rag.indexing._embed", return_value=[]),
            patch("app.rag.indexing.QdrantStore"),
        ):
            result = index_file(doc, settings)

        assert result.indexed == 0

    def test_missing_keys_returns_error(self, tmp_path):
        from app.rag.indexing import index_file

        doc = tmp_path / "sample.txt"
        doc.write_text("hello world", encoding="utf-8")

        settings = _fake_settings(tmp_path)
        settings.any_keys_present = False

        result = index_file(doc, settings)
        assert result.status == "error"
        assert any("OpenAI/Azure" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Integration test (requires live Qdrant)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIndexAndSearchIntegration:
    @pytest.fixture(autouse=True)
    def skip_if_no_qdrant(self):
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        if not _qdrant_available(qdrant_url):
            pytest.skip("Qdrant not available at " + qdrant_url)

    def test_roundtrip(self, tmp_path):
        """Index a text file, then search for it."""
        from app.vectordb.qdrant_store import QdrantStore

        settings = _fake_settings(tmp_path)

        doc = tmp_path / "hello.txt"
        doc.write_text("The quick brown fox jumps over the lazy dog. " * 10)

        fake_vector = [0.5] * 1536

        with patch("app.rag.indexing._embed", return_value=[fake_vector] * 20):
            from app.rag.indexing import index_file
            result = index_file(doc, settings)

        assert result.indexed > 0

        # Now search
        store = QdrantStore(settings)
        results = store.search(fake_vector, top_k=3, filter=None)
        assert len(results) > 0
        payload, chunk_id = results[0]
        assert payload["doc_name"] == "hello.txt"
