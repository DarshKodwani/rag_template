"""Ingest endpoints: reindex all docs or upload a single file."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.core.config import get_settings
from app.core.models import IngestResponse
from app.rag.indexing import index_directory, index_file

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/reindex", response_model=IngestResponse)
async def reindex() -> IngestResponse:
    """Re-index all documents in the documents/ directory."""
    settings = get_settings()
    try:
        result = index_directory(settings)
        return result
    except Exception as exc:
        log.exception("Reindex failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    dest = uploads_dir / (file.filename or "upload")

    try:
        with dest.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
        log.info("Saved uploaded file to %s", dest)
        result = index_file(dest, settings)
        return result
    except Exception as exc:
        log.exception("Upload/index failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
