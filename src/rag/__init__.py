"""
RAG (Retrieval-Augmented Generation) module.

Provides vector store implementations, embeddings, and document loading
for F1 data retrieval and knowledge augmentation.
"""

from .vector_store import VectorStore, SearchResult
from .embeddings import EmbeddingsProvider
from .document_loader import Document, DocumentInfo, DocumentLoader
from .rag_manager import (
    RAGManager,
    RAGContext,
    RAGStats,
    get_rag_manager,
    reset_rag_manager,
)
from .template_generator import (
    TemplateGenerator,
    GeneratedDocument,
    get_template_generator,
    reset_template_generator,
    CIRCUIT_DATA,
    CIRCUIT_GROUPS,
)

__all__ = [
    "VectorStore",
    "SearchResult",
    "EmbeddingsProvider",
    "Document",
    "DocumentInfo",
    "DocumentLoader",
    "RAGManager",
    "RAGContext",
    "RAGStats",
    "get_rag_manager",
    "reset_rag_manager",
    "TemplateGenerator",
    "GeneratedDocument",
    "get_template_generator",
    "reset_template_generator",
    "CIRCUIT_DATA",
    "CIRCUIT_GROUPS",
]
