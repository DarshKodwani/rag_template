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
from app.rag.indexing import (
    _doc_id,
    _chunk_id,
    _get_embedding_client,
    _embed,
    _load_file,
    _build_chunks,
    _index_chunks,
    index_file,
    index_directory,
    index_directory_iter,
)


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
# Helpers / _embed / _get_embedding_client / _load_file
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_doc_id_is_deterministic(self):
        p = Path("/tmp/test.pdf")
        assert _doc_id(p) == _doc_id(p)

    def test_chunk_id_is_deterministic(self):
        assert _chunk_id("doc1", 0) == _chunk_id("doc1", 0)

    def test_chunk_id_different_for_different_index(self):
        assert _chunk_id("doc1", 0) != _chunk_id("doc1", 1)


class TestGetEmbeddingClient:
    def test_azure_client(self):
        settings = _fake_settings(Path("/tmp"))
        settings.azure_keys_present = True
        with patch("openai.AzureOpenAI") as mock_azure:
            _get_embedding_client(settings)
            mock_azure.assert_called_once()

    def test_openai_client(self):
        settings = _fake_settings(Path("/tmp"))
        settings.azure_keys_present = False
        with patch("openai.OpenAI") as mock_openai:
            _get_embedding_client(settings)
            mock_openai.assert_called_once()


class TestEmbed:
    def test_embed_single_batch(self):
        settings = _fake_settings(Path("/tmp"))
        settings.azure_keys_present = False

        mock_item = MagicMock()
        mock_item.embedding = [0.1, 0.2]
        mock_response = MagicMock()
        mock_response.data = [mock_item, mock_item]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response

        with patch("app.rag.indexing._get_embedding_client", return_value=mock_client):
            result = _embed(["text1", "text2"], settings)

        assert len(result) == 2

    def test_embed_multiple_batches(self):
        settings = _fake_settings(Path("/tmp"))
        settings.azure_keys_present = False

        mock_item = MagicMock()
        mock_item.embedding = [0.1]
        mock_response = MagicMock()
        mock_response.data = [mock_item]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response

        with patch("app.rag.indexing._get_embedding_client", return_value=mock_client):
            result = _embed(["t1", "t2", "t3"], settings, batch_size=1)

        assert len(result) == 3
        assert mock_client.embeddings.create.call_count == 3

    def test_embed_uses_azure_model(self):
        settings = _fake_settings(Path("/tmp"))
        settings.azure_keys_present = True

        mock_item = MagicMock()
        mock_item.embedding = [0.1]
        mock_response = MagicMock()
        mock_response.data = [mock_item]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response

        with patch("app.rag.indexing._get_embedding_client", return_value=mock_client):
            _embed(["text"], settings)

        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-small"


class TestLoadFile:
    def test_load_pdf_file(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()
        with patch("app.loaders.pdf_loader.load_pdf", return_value=("pdf text", [{"page": 1, "start_offset": 0, "end_offset": 8}])):
            text, meta = _load_file(pdf_path)
        assert text == "pdf text"

    def test_load_docx_file(self, tmp_path):
        docx_path = tmp_path / "test.docx"
        docx_path.touch()
        with patch("app.loaders.docx_loader.load_docx", return_value=("docx text", [])):
            text, meta = _load_file(docx_path)
        assert text == "docx text"

    def test_load_txt_file(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("hello")
        text, meta = _load_file(txt_path)
        assert text == "hello"


class TestBuildChunks:
    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        settings = _fake_settings(tmp_path)
        chunks = _build_chunks(f, "empty.txt", "doc1", settings)
        assert chunks == []

    def test_builds_chunks_with_metadata(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Some text for chunking. " * 20)
        settings = _fake_settings(tmp_path)
        chunks = _build_chunks(f, "test.txt", "doc1", settings)
        assert len(chunks) > 0
        assert chunks[0].doc_name == "test.txt"


class TestIndexChunks:
    def test_empty_chunks_does_nothing(self):
        settings = _fake_settings(Path("/tmp"))
        with patch("app.rag.indexing.QdrantStore") as mock_store_cls:
            _index_chunks([], settings)
            mock_store_cls.assert_not_called()


class TestIndexFileCoverage:
    def test_rel_path_fallback_on_value_error(self, tmp_path):
        """When path is not relative to docs_dir.parent, use path.name."""
        doc = tmp_path / "sample.txt"
        doc.write_text("test content " * 20)

        settings = _fake_settings(tmp_path)
        # Set documents_dir to a completely different path so relative_to raises
        settings.documents_dir = Path("/completely/different/path")

        fake_vector = [0.1] * 4
        with (
            patch("app.rag.indexing._embed", return_value=[fake_vector]),
            patch("app.rag.indexing.QdrantStore") as mock_store_cls,
        ):
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            result = index_file(doc, settings)

        assert result.indexed > 0

    def test_index_file_exception_handling(self, tmp_path):
        doc = tmp_path / "sample.txt"
        doc.write_text("test content " * 20)

        settings = _fake_settings(tmp_path)
        settings.documents_dir = tmp_path

        with patch("app.rag.indexing._build_chunks", side_effect=RuntimeError("chunk fail")):
            result = index_file(doc, settings)

        assert result.status == "partial"
        assert any("chunk fail" in e for e in result.errors)


class TestIndexDirectory:
    def test_index_directory_success(self, tmp_path):
        docs = tmp_path / "documents"
        docs.mkdir()
        (docs / "a.txt").write_text("hello world")
        (docs / "b.txt").write_text("goodbye world")

        settings = _fake_settings(tmp_path)
        settings.documents_dir = docs
        settings.any_keys_present = True

        fake_vector = [0.1] * 4
        with (
            patch("app.rag.indexing._embed", return_value=[fake_vector]),
            patch("app.rag.indexing.QdrantStore") as mock_store_cls,
        ):
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            result = index_directory(settings)

        assert result.status == "ok"
        assert result.indexed >= 2

    def test_index_directory_no_keys(self, tmp_path):
        settings = _fake_settings(tmp_path)
        settings.any_keys_present = False

        result = index_directory(settings)
        assert result.status == "error"

    def test_index_directory_with_errors(self, tmp_path):
        docs = tmp_path / "documents"
        docs.mkdir()
        (docs / "a.txt").write_text("hello")

        settings = _fake_settings(tmp_path)
        settings.documents_dir = docs
        settings.any_keys_present = True

        with patch("app.rag.indexing._build_chunks", side_effect=RuntimeError("fail")):
            result = index_directory(settings)

        assert result.status == "partial"


class TestIndexDirectoryIter:
    def test_yields_start_progress_done(self, tmp_path):
        docs = tmp_path / "documents"
        docs.mkdir()
        (docs / "a.txt").write_text("hello world")

        settings = _fake_settings(tmp_path)
        settings.documents_dir = docs
        settings.any_keys_present = True

        fake_vector = [0.1] * 4
        with (
            patch("app.rag.indexing._embed", return_value=[fake_vector]),
            patch("app.rag.indexing.QdrantStore") as mock_store_cls,
        ):
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            events = list(index_directory_iter(settings))

        assert events[0]["type"] == "start"
        assert events[0]["total"] == 1
        assert events[1]["type"] == "progress"
        assert events[1]["doc_name"] == "a.txt"
        assert events[-1]["type"] == "done"
        assert events[-1]["indexed"] >= 1

    def test_yields_error_when_no_keys(self, tmp_path):
        settings = _fake_settings(tmp_path)
        settings.any_keys_present = False

        events = list(index_directory_iter(settings))
        assert len(events) == 1
        assert events[0]["type"] == "error"


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
