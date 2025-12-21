"""
RAG (Retrieval-Augmented Generation) module.

Provides vector store implementations and embeddings for F1 data retrieval.
"""

from .vector_store import VectorStore, SearchResult
from .embeddings import EmbeddingsProvider

__all__ = [
    "VectorStore",
    "SearchResult",
    "EmbeddingsProvider",
]
