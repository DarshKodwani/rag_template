"""Health check endpoint."""
from __future__ import annotations

import logging
from fastapi import APIRouter

from app.core.models import HealthResponse
from app.vectordb.qdrant_store import QdrantStore
from app.core.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    qdrant_status = "unreachable"
    try:
        store = QdrantStore(settings)
        store.healthcheck()
        qdrant_status = "ok"
    except Exception as exc:
        log.warning("Qdrant health check failed: %s", exc)
    return HealthResponse(status="ok", qdrant=qdrant_status)
