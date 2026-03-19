"""Ingest endpoints: reindex all docs or upload a single file."""
from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.models import DocumentInfo, IngestResponse
from app.rag.indexing import index_directory, index_directory_iter, index_file
from app.rag.registry import load_registry, sync_registry_from_qdrant

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    """Return the list of currently indexed documents."""
    settings = get_settings()
    entries = load_registry(settings.data_dir)
    if not entries:
        entries = sync_registry_from_qdrant(settings)
    return [DocumentInfo(**e) for e in entries]


@router.post("/reindex", response_model=IngestResponse)
async def reindex() -> IngestResponse:
    """Re-index all documents in the documents/ directory."""
    settings = get_settings()
    try:
        result = index_directory(settings)
        return result
    except Exception as exc:
        log.exception("Reindex failed")
        raise HTTPException(status_code=500, detail="Reindex failed") from exc


@router.post("/reindex/stream")
async def reindex_stream() -> StreamingResponse:
    """Re-index with SSE progress updates."""
    settings = get_settings()

    def event_generator():
        try:
            for event in index_directory_iter(settings):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            log.exception("Streaming reindex failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Reindex failed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/upload", response_model=IngestResponse)
async def upload(file: UploadFile = File(...)) -> IngestResponse:
    """Upload a document, save it, and index it."""
    settings = get_settings()
    allowed_suffixes = {".pdf", ".docx", ".txt"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {allowed_suffixes}",
        )

    uploads_dir = settings.documents_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Sanitise filename to prevent path-traversal
    raw_name = file.filename or "upload"
    safe_name = re.sub(r'[^\w.\-]', '_', Path(raw_name).name)
    if not safe_name or safe_name.startswith('.'):
        safe_name = "upload" + suffix
    dest = uploads_dir / safe_name

    # Enforce max upload size (50 MB)
    max_bytes = 50 * 1024 * 1024
    try:
        size = 0
        with dest.open("wb") as fh:
            while chunk := file.file.read(8192):
                size += len(chunk)
                if size > max_bytes:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
                fh.write(chunk)
        log.info("Saved uploaded file to %s", dest)
        result = index_file(dest, settings)
        return result
    except Exception as exc:
        log.exception("Upload/index failed")
        raise HTTPException(status_code=500, detail="Upload failed") from exc
