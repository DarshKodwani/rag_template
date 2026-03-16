"""Chat endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.models import ChatRequest, ChatResponse
from app.rag.search import answer_query

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    if not settings.azure_keys_present:
        raise HTTPException(
            status_code=503,
            detail=(
                "Azure OpenAI keys missing. "
                "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env."
            ),
        )
    try:
        return answer_query(request, settings)
    except Exception as exc:
        log.exception("Chat query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
