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
    content: str = Field(..., max_length=50000)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)
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


class DocumentInfo(BaseModel):
    doc_name: str
    doc_id: str
    chunks: int
    pages: Optional[int] = None
    indexed_at: str


# ---------------------------------------------------------------------------
# Feedback models
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    query: str = Field(..., max_length=5000)
    answer: str = Field(..., max_length=50000)
    rating: str = Field(..., pattern="^(up|down)$")
    suggested_answer: Optional[str] = Field(default=None, max_length=50000)
    citations: Optional[list[Citation]] = None


class FeedbackResponse(BaseModel):
    id: int
    status: str


class FeedbackListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
