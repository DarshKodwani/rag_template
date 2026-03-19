"""Feedback API endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.core.models import FeedbackRequest, FeedbackResponse, FeedbackListResponse
from app.feedback.db import save_feedback, list_feedback, count_feedback

log = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    row_id = save_feedback(
        query=request.query,
        answer=request.answer,
        rating=request.rating,
        suggested_answer=request.suggested_answer,
        citations=[c.model_dump() for c in request.citations] if request.citations else None,
    )
    log.info("Feedback #%d saved (rating=%s) for query '%.60s…'", row_id, request.rating, request.query)
    return FeedbackResponse(id=row_id, status="saved")


@router.get("", response_model=FeedbackListResponse)
async def get_feedback(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    rating: Optional[str] = Query(default=None, pattern="^(up|down)$"),
) -> FeedbackListResponse:
    items = list_feedback(limit=limit, offset=offset, rating=rating)
    total = count_feedback(rating=rating)
    return FeedbackListResponse(items=items, total=total)
