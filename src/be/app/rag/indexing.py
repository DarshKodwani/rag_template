"""Document indexing: load → chunk → embed → upsert into Qdrant."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.models import Chunk, IngestResponse
from app.rag.chunking import check_complex_doc, iter_chunks_with_offsets
from app.vectordb.qdrant_store import QdrantStore

if TYPE_CHECKING:
    from app.core.config import Settings

log = logging.getLogger(__name__)

_SUPPORTED = {".pdf", ".docx", ".txt"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_id(path: Path) -> str:
    return hashlib.md5(str(path).encode()).hexdigest()


def _chunk_id(doc_id: str, index: int) -> str:
    return hashlib.md5(f"{doc_id}:{index}".encode()).hexdigest()


def _get_embedding_client(settings: "Settings"):
    """Return an OpenAI-compatible client (Azure or Generic)."""
    from openai import AzureOpenAI, OpenAI

    if settings.azure_keys_present:
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def _embed(texts: list[str], settings: "Settings", *, batch_size: int = 2048) -> list[list[float]]:
    client = _get_embedding_client(settings)
    model = (
        settings.azure_openai_embedding_deployment
        if settings.azure_keys_present
        else settings.openai_embedding_model
    )
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend(item.embedding for item in response.data)
    return all_embeddings


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_file(path: Path) -> tuple[str, list[dict]]:
    """
    Return (full_text, list_of_chunk_metadata_hints).

    chunk_metadata_hints is a list of dicts that may contain:
      {'page': int} for PDFs
      {'section': str, 'para_index': int} for DOCX
    We return them alongside the full text so chunking can be done uniformly,
    while metadata is attached by mapping chunk offsets to hints.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from app.loaders.pdf_loader import load_pdf
        return load_pdf(path)
    if suffix == ".docx":
        from app.loaders.docx_loader import load_docx
        return load_docx(path)
    from app.loaders.text_loader import load_text
    return load_text(path)


# ---------------------------------------------------------------------------
# Core indexing
# ---------------------------------------------------------------------------


def _build_chunks(
    path: Path,
    rel_path: str,
    doc_id: str,
    settings: "Settings",
) -> list[Chunk]:
    full_text, page_map = _load_file(path)
    if not full_text.strip():
        log.warning("Empty document: %s", path)
        return []

    paragraphs = full_text.splitlines()
    check_complex_doc(doc_id, full_text, paragraphs, settings.data_dir)

    chunks: list[Chunk] = []
    for idx, (chunk_text, start, end) in enumerate(
        iter_chunks_with_offsets(full_text, settings.chunk_size, settings.chunk_overlap)
    ):
        # Find the best metadata hint for this chunk's start offset
        page: int | None = None
        section: str | None = None

        for hint in page_map:
            hint_start = hint.get("start_offset", 0)
            hint_end = hint.get("end_offset", len(full_text))
            if hint_start <= start < hint_end:
                page = hint.get("page")
                section = hint.get("section")
                break

        chunks.append(
            Chunk(
                chunk_id=_chunk_id(doc_id, idx),
                doc_id=doc_id,
                doc_name=path.name,
                doc_rel_path=rel_path,
                text=chunk_text,
                page=page,
                section=section,
                start_offset=start,
                end_offset=end,
            )
        )
    return chunks


def _index_chunks(chunks: list[Chunk], settings: "Settings") -> None:
    if not chunks:
        return

    texts = [c.text for c in chunks]
    vectors = _embed(texts, settings)

    store = QdrantStore(settings)
    # Infer embedding dimension from first vector; init collection if needed
    store.init_collection(dimension=len(vectors[0]))

    # Delete existing chunks for this doc then upsert fresh ones
    doc_id = chunks[0].doc_id
    store.delete_by_doc_id(doc_id)
    store.upsert(chunks, vectors)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_file(path: Path, settings: "Settings") -> IngestResponse:
    """Index a single file."""
    if not settings.any_keys_present:
        return IngestResponse(
            status="error",
            indexed=0,
            errors=["OpenAI/Azure API keys missing — cannot generate embeddings."],
        )

    doc_id = _doc_id(path)
    docs_dir = settings.documents_dir
    try:
        rel_path = str(path.relative_to(docs_dir.parent))
    except ValueError:
        rel_path = path.name

    errors: list[str] = []
    indexed = 0
    try:
        chunks = _build_chunks(path, rel_path, doc_id, settings)
        _index_chunks(chunks, settings)
        indexed = len(chunks)
        log.info("Indexed %d chunks from %s", indexed, path.name)
    except Exception as exc:
        log.exception("Failed to index %s", path)
        errors.append(f"{path.name}: {exc}")

    return IngestResponse(
        status="ok" if not errors else "partial",
        indexed=indexed,
        errors=errors,
    )


def index_directory(settings: "Settings") -> IngestResponse:
    """Index all supported documents in the documents directory."""
    if not settings.any_keys_present:
        return IngestResponse(
            status="error",
            indexed=0,
            errors=["OpenAI/Azure API keys missing — cannot generate embeddings."],
        )

    docs_dir = settings.documents_dir
    paths = [p for p in docs_dir.rglob("*") if p.suffix.lower() in _SUPPORTED]
    log.info("Found %d document(s) to index in %s", len(paths), docs_dir)

    total_indexed = 0
    all_errors: list[str] = []

    for path in paths:
        result = index_file(path, settings)
        total_indexed += result.indexed
        all_errors.extend(result.errors)

    return IngestResponse(
        status="ok" if not all_errors else "partial",
        indexed=total_indexed,
        errors=all_errors,
    )
