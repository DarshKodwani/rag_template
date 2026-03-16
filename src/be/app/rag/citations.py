"""Convert Qdrant result payloads into Citation objects."""
from __future__ import annotations

from app.core.models import Citation


def payload_to_citation(payload: dict, chunk_id: str) -> Citation:
    """Build a :class:`Citation` from a Qdrant point payload."""
    snippet = payload.get("text", "")
    # Truncate to a readable length for the frontend
    if len(snippet) > 300:
        snippet = snippet[:297] + "…"

    return Citation(
        doc_name=payload.get("doc_name", ""),
        doc_path=payload.get("doc_rel_path", ""),
        page=payload.get("page"),
        section=payload.get("section"),
        snippet=snippet,
        chunk_id=chunk_id,
    )


def payloads_to_citations(
    results: list[tuple[dict, str]],
) -> list[Citation]:
    """
    Convert a list of (payload, chunk_id) pairs to Citation objects.
    Always returns a list (empty if no results).
    """
    return [payload_to_citation(payload, cid) for payload, cid in results]
