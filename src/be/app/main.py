"""Application entry point."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, health, ingest
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="RAG Demo API",
    description="Minimal RAG application with OpenAI/Azure + Qdrant",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static file serving for documents (path-traversal safe via StaticFiles)
# ---------------------------------------------------------------------------
_DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "documents"
_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/documents", StaticFiles(directory=str(_DOCUMENTS_DIR)), name="documents")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(ingest.router)
