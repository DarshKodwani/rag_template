"""Qdrant implementation of VectorStore."""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.vectordb.base import VectorStore
from app.core.models import Chunk

if TYPE_CHECKING:
    from app.core.config import Settings

log = logging.getLogger(__name__)


class QdrantStore(VectorStore):
    def __init__(self, settings: "Settings") -> None:
        self._settings = settings
        self._client = QdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection

    # ------------------------------------------------------------------
    # VectorStore interface
    # ------------------------------------------------------------------

    def init_collection(self, dimension: int) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            log.info(
                "Created Qdrant collection '%s' (dim=%d)", self._collection, dimension
            )
        else:
            log.debug("Collection '%s' already exists", self._collection)

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        points = [
            PointStruct(
                id=_chunk_id_to_int(chunk.chunk_id),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "doc_name": chunk.doc_name,
                    "doc_rel_path": chunk.doc_rel_path,
                    "text": chunk.text,
                    "page": chunk.page,
                    "section": chunk.section,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        log.debug("Upserted %d points into '%s'", len(points), self._collection)

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filter: Optional[dict],
    ) -> list[tuple[dict, str]]:
        qdrant_filter = Filter(**filter) if filter else None
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        return [
            (point.payload or {}, (point.payload or {}).get("chunk_id", str(point.id)))
            for point in results
        ]

    def delete_by_doc_id(self, doc_id: str) -> None:
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
            )
            log.debug("Deleted points for doc_id=%s", doc_id)
        except Exception as exc:
            # Collection may not exist yet on first run — that's fine
            log.debug("delete_by_doc_id skipped (%s)", exc)

    def healthcheck(self) -> None:
        """Raise if Qdrant is unreachable."""
        self._client.get_collections()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _chunk_id_to_int(chunk_id: str) -> int:
    """Convert a hex MD5 chunk_id to an integer for Qdrant point IDs."""
    return int(chunk_id, 16) % (2**63)
