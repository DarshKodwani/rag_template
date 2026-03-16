"""Pydantic models shared across the application."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Internal chunk model
# ---------------------------------------------------------------------------


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_name: str
    doc_rel_path: str
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    doc_name: str
    doc_path: str
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: str
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class IngestResponse(BaseModel):
    status: str
    indexed: int
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    qdrant: str = "unknown"
