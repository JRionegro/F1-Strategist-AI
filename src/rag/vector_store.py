"""
Abstract base class for vector store implementations.

Defines the interface for storing and retrieving F1 data embeddings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    content: str
    metadata: dict[str, Any]
    score: float
    id: str


class VectorStore(ABC):
    """Abstract interface for vector store operations."""

    @abstractmethod
    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None
    ) -> list[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of text documents to add
            metadatas: List of metadata dicts for each document
            ids: Optional list of document IDs

        Returns:
            List of document IDs
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results ordered by similarity
        """
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """
        Delete documents by IDs.

        Args:
            ids: List of document IDs to delete
        """
        pass

    @abstractmethod
    def get_collection_stats(self) -> dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from the store."""
        pass
