"""Abstract VectorStore interface.

To swap Qdrant for another backend (e.g. Oracle AI Vector Search):
  1. Create a new module in this package implementing VectorStore, e.g.:
       src/be/app/vectordb/oracle_store.py
     Implement all five abstract methods:
       - init_collection: create table/index with the given embedding dimension
       - upsert: insert/update vectors + payload using Oracle VECTOR type
       - search: run approximate nearest-neighbour search with cosine metric
       - delete_by_doc_id: DELETE FROM ... WHERE payload->>'doc_id' = :doc_id
       - healthcheck: run a lightweight connectivity check
  2. Instantiate your new class in app/main.py (or via dependency injection).
  3. Add Oracle connection settings to .env.example and config.py.
  4. All API, RAG, and test code remains unchanged.

# TODO: Oracle AI Vector Search adapter (oracle_store.py)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.core.models import Chunk


class VectorStore(ABC):
    """Interface for vector storage backends."""

    @abstractmethod
    def init_collection(self, dimension: int) -> None:
        """Create the collection/index if it does not already exist."""

    @abstractmethod
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Insert or update chunk vectors and their payloads."""

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filter: Optional[dict],
    ) -> list[tuple[dict, str]]:
        """
        Return the top-k results as (payload, chunk_id) pairs.
        Cosine similarity is assumed.
        """

    @abstractmethod
    def delete_by_doc_id(self, doc_id: str) -> None:
        """Remove all vectors belonging to *doc_id*."""

    @abstractmethod
    def healthcheck(self) -> None:
        """Raise an exception if the store is unreachable."""
