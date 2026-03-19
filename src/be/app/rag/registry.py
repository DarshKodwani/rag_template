"""Lightweight JSON registry that tracks indexed documents."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from qdrant_client import QdrantClient

if TYPE_CHECKING:
    from app.core.config import Settings

log = logging.getLogger(__name__)

_REGISTRY_FILENAME = "doc_registry.json"


def _registry_path(data_dir: Path) -> Path:
    return data_dir / _REGISTRY_FILENAME


def load_registry(data_dir: Path) -> list[dict[str, Any]]:
    """Return the current list of registered documents."""
    path = _registry_path(data_dir)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        log.warning("Corrupt registry file — returning empty list")
        return []


def _save_registry(data_dir: Path, entries: list[dict[str, Any]]) -> None:
    path = _registry_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    tmp.replace(path)


def register_document(
    data_dir: Path,
    *,
    doc_name: str,
    doc_id: str,
    chunks: int,
    pages: int | None = None,
) -> None:
    """Add or update a document entry in the registry."""
    entries = load_registry(data_dir)
    # Remove existing entry for same doc_id (re-index case)
    entries = [e for e in entries if e.get("doc_id") != doc_id]
    entries.append(
        {
            "doc_name": doc_name,
            "doc_id": doc_id,
            "chunks": chunks,
            "pages": pages,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_registry(data_dir, entries)


def clear_registry(data_dir: Path) -> None:
    """Remove all entries (used during full reindex)."""
    _save_registry(data_dir, [])


def sync_registry_from_qdrant(settings: "Settings") -> list[dict[str, Any]]:
    """Backfill the registry from Qdrant when the JSON file is empty.

    Scrolls all points in the collection, groups by doc_id, and writes
    one registry entry per unique document.  Returns the resulting list.
    """
    try:
        client = QdrantClient(url=settings.qdrant_url)
        # Check collection exists
        names = [c.name for c in client.get_collections().collections]
        if settings.qdrant_collection not in names:
            return []

        docs: dict[str, dict[str, Any]] = {}
        offset = None
        while True:
            result = client.scroll(
                collection_name=settings.qdrant_collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = result
            for pt in points:
                payload = pt.payload or {}
                doc_id = payload.get("doc_id")
                if not doc_id:
                    continue
                if doc_id not in docs:
                    docs[doc_id] = {
                        "doc_name": payload.get("doc_name", "unknown"),
                        "doc_id": doc_id,
                        "chunks": 0,
                        "pages": None,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    }
                docs[doc_id]["chunks"] += 1
                page = payload.get("page")
                if page is not None:
                    prev = docs[doc_id].get("pages") or 0
                    docs[doc_id]["pages"] = max(prev, page)
            if next_offset is None:
                break
            offset = next_offset

        entries = list(docs.values())
        if entries:
            _save_registry(settings.data_dir, entries)
            log.info("Backfilled registry with %d document(s) from Qdrant", len(entries))
        return entries
    except Exception:
        log.warning("Could not sync registry from Qdrant", exc_info=True)
        return []
