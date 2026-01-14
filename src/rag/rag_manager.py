"""
RAG Manager for F1 Strategist AI.

Orchestrates document loading, ChromaDB indexing, and context management
for the RAG system. Provides a high-level API for loading and querying
F1-related documents organized by year and circuit.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .chromadb_store import ChromaDBStore
from .document_loader import DocumentLoader, Document
from src.utils.logging_config import get_logger, LogCategory

# Use categorized logger for RAG operations
logger = get_logger(LogCategory.RAG)


@dataclass
class RAGContext:
    """Current RAG context information."""

    year: int
    circuit: Optional[str] = None
    document_count: int = 0
    chunk_count: int = 0
    categories: dict[str, int] = field(default_factory=dict)


@dataclass
class RAGStats:
    """RAG system statistics."""

    total_documents: int
    total_chunks: int
    collection_name: str
    persist_directory: str
    embeddings_model: str
    current_context: Optional[RAGContext] = None


class RAGManager:
    """
    Orchestrate RAG document loading and ChromaDB management.

    This manager handles:
    - Loading documents from the data/rag/ directory structure
    - Chunking and indexing documents into ChromaDB
    - Context switching when year/circuit changes
    - Querying relevant documents for agent prompts
    """

    # Collection name for RAG documents
    COLLECTION_NAME = "f1_rag_documents"

    def __init__(
        self,
        base_path: str = "data/rag",
        persist_directory: str = "./data/chromadb",
        embeddings_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize RAG Manager.

        Args:
            base_path: Base directory for RAG documents
            persist_directory: ChromaDB persistence directory
            embeddings_model: Sentence-transformers model name
            chunk_size: Target chunk size for document splitting
            chunk_overlap: Overlap between chunks
        """
        self.base_path = base_path
        self.persist_directory = persist_directory

        # Initialize components
        self.document_loader = DocumentLoader(
            base_path=base_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        self.vector_store = ChromaDBStore(
            collection_name=self.COLLECTION_NAME,
            persist_directory=persist_directory,
            embeddings_model=embeddings_model,
        )

        # Current context
        self._current_context: Optional[RAGContext] = None

        logger.info(
            f"RAGManager initialized: base_path={base_path}, "
            f"persist_directory={persist_directory}"
        )

    @property
    def current_context(self) -> Optional[RAGContext]:
        """Get current RAG context."""
        return self._current_context

    def load_context(
        self,
        year: int,
        circuit: Optional[str] = None,
        clear_existing: bool = True,
    ) -> int:
        """
        Load documents for a specific year and optionally circuit.

        This clears the existing collection and loads fresh documents
        based on the year/circuit context.

        Args:
            year: Target year (e.g., 2024)
            circuit: Optional circuit name (e.g., "bahrain", "abu_dhabi")
            clear_existing: Whether to clear existing documents first

        Returns:
            Number of chunks indexed
        """
        logger.info(f"Loading RAG context: year={year}, circuit={circuit}")

        # Clear existing documents if requested
        if clear_existing:
            self.clear_collection()

        # Load documents from filesystem
        documents = self.document_loader.load_documents_for_context(
            year=year,
            circuit=circuit,
        )

        if not documents:
            logger.warning(f"No documents found for year={year}, circuit={circuit}")
            self._current_context = RAGContext(
                year=year,
                circuit=circuit,
                document_count=0,
                chunk_count=0,
            )
            return 0

        # Index documents into ChromaDB
        chunk_count = self._index_documents(documents)

        # Count documents by category
        categories: dict[str, int] = {}
        for doc in documents:
            category = doc.metadata.get("category", "other")
            categories[category] = categories.get(category, 0) + 1

        # Update current context
        unique_sources = set(doc.metadata.get("source", "") for doc in documents)
        self._current_context = RAGContext(
            year=year,
            circuit=circuit,
            document_count=len(unique_sources),
            chunk_count=chunk_count,
            categories=categories,
        )

        logger.info(
            f"RAG context loaded: {chunk_count} chunks from "
            f"{len(unique_sources)} documents"
        )

        return chunk_count

    def _index_documents(self, documents: list[Document]) -> int:
        """
        Index documents into ChromaDB.

        Args:
            documents: List of Document objects to index

        Returns:
            Number of documents indexed
        """
        if not documents:
            return 0

        # Prepare for ChromaDB
        texts = [doc.content for doc in documents]
        ids = [doc.doc_id for doc in documents]

        # ChromaDB only accepts str, int, float, bool, or None as metadata
        # Convert list values (like keywords) to JSON strings
        metadatas = []
        for doc in documents:
            clean_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, list):
                    # Convert lists to comma-separated string
                    clean_metadata[key] = ",".join(str(v) for v in value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    clean_metadata[key] = value
                else:
                    # Convert other types to string
                    clean_metadata[key] = str(value)
            metadatas.append(clean_metadata)

        # Add to vector store
        self.vector_store.add_documents(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        return len(documents)

    def reload(self) -> int:
        """
        Reload current context.

        Useful after editing documents to refresh the index.

        Returns:
            Number of chunks indexed
        """
        if not self._current_context:
            logger.warning("No context to reload")
            return 0

        return self.load_context(
            year=self._current_context.year,
            circuit=self._current_context.circuit,
            clear_existing=True,
        )

    def clear_collection(self) -> None:
        """Clear all documents from ChromaDB collection."""
        self.vector_store.clear()
        logger.info("RAG collection cleared")

    def _build_filters(self, *, category: Optional[str], year: Optional[int], circuit: Optional[str]) -> list[dict]:
        """Build a list of Chroma filters to cover global/year + circuit scope.

        Chroma's filters are AND-only. To include both global/year docs and
        circuit docs, we issue multiple queries (one per filter) and merge.
        """
        filters: list[dict] = []

        # Base filter for category if provided
        base = {"category": category} if category else {}

        def _where(clause: dict[str, Any]) -> dict[str, Any]:
            """Convert a flat dict into a valid Chroma where clause.

            Chroma requires exactly one operator. If multiple fields are present,
            wrap them into an $and array. If only one, return as-is.
            """
            if len(clause) <= 1:
                return clause
            return {"$and": [{k: v} for k, v in clause.items()]}

        # Always include global docs (no year/circuit)
        filters.append(_where({**base, "scope": "global"}))

        # Year-level docs when a year is set
        if year is not None:
            filters.append(_where({**base, "scope": "year", "year": year}))

        # Circuit-specific docs when circuit is set
        if circuit:
            filters.append(
                _where({**base, "scope": "circuit", "circuit": circuit.lower()})
            )

        return filters

    def search(
        self,
        query: str,
        k: int = 5,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for relevant documents.

        Args:
            query: Search query text
            k: Number of results to return
            category: Optional category filter (strategy, weather, tire, fia)

        Returns:
            List of search results with content, metadata, and score
        """
        year = self._current_context.year if self._current_context else None
        circuit = self._current_context.circuit if self._current_context else None

        # If no context loaded, fall back to global-only filter
        if year is None and circuit is None:
            results = self.vector_store.search(
                query=query,
                k=k,
                filter_metadata={"category": category} if category else None,
            )
            return [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "score": r.score,
                    "id": r.id,
                }
                for r in results
            ]

        filters = self._build_filters(category=category, year=year, circuit=circuit)

        merged: list[dict] = []
        seen_ids: set[str] = set()

        for flt in filters:
            results = self.vector_store.search(
                query=query,
                k=k,
                filter_metadata=flt,
            )

            for r in results:
                if r.id in seen_ids:
                    continue
                seen_ids.add(r.id)
                merged.append(
                    {
                        "content": r.content,
                        "metadata": r.metadata,
                        "score": r.score,
                        "id": r.id,
                    }
                )

        # Sort by score desc to stabilize
        merged.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Trim to k overall
        return merged[:k]

    def get_stats(self) -> RAGStats:
        """
        Get RAG system statistics.

        Returns:
            RAGStats object with current system information
        """
        collection_stats = self.vector_store.get_collection_stats()

        return RAGStats(
            total_documents=collection_stats.get("document_count", 0),
            total_chunks=collection_stats.get("document_count", 0),
            collection_name=collection_stats.get("collection_name", ""),
            persist_directory=collection_stats.get("persist_directory", ""),
            embeddings_model=collection_stats.get("embeddings", {}).get(
                "model_name", ""
            ),
            current_context=self._current_context,
        )

    def list_documents(
        self,
        *,
        year: Optional[int] = None,
        circuit: Optional[str] = None,
    ) -> dict[str, list[dict]]:
        """
        List loaded documents organized by category.

        Args:
            year: Optional filter; when provided, only documents whose metadata.year
                matches (or global docs without a year) are returned.
            circuit: Optional filter; when provided, only circuit-scoped documents
                matching the circuit are returned, while global/year docs remain.

        Returns:
            Dict mapping category to list of document info dicts
        """
        from pathlib import Path

        all_docs = self.vector_store.get_all_documents()

        # Organize by category
        by_category: dict[str, list[dict]] = {
            "global": [],
            "fia": [],
            "strategy": [],
            "weather": [],
            "performance": [],
            "race_control": [],
            "race_position": [],
            "other": [],
        }

        # Track unique sources to avoid duplicates
        seen_sources: set[str] = set()

        # Get base path for constructing absolute paths
        base_path = Path(self.document_loader.base_path).resolve()

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "unknown")

            # Filter by year (skip circuit/year docs from other years; keep global)
            if year is not None:
                meta_year = metadata.get("year")
                if meta_year is not None and meta_year != year:
                    continue

            # Filter by circuit for circuit-scoped docs only
            if circuit:
                meta_circuit = str(metadata.get("circuit", "")).lower()
                meta_scope = metadata.get("scope")
                if meta_scope == "circuit" and meta_circuit != str(circuit).lower():
                    continue

            # Skip if already seen (multiple chunks from same doc)
            if source in seen_sources:
                continue
            seen_sources.add(source)

            category = metadata.get("category", "other")

            # Build absolute filepath from relative source
            filepath = str(base_path / source)

            doc_info = {
                "source": source,
                "filename": metadata.get("filename", ""),
                "filepath": filepath,
                "year": metadata.get("year"),
                "circuit": metadata.get("circuit"),
                "scope": metadata.get("scope", ""),
            }

            if category in by_category:
                by_category[category].append(doc_info)
            else:
                by_category["other"].append(doc_info)

        return by_category

    def get_context_for_agent(
        self,
        agent_type: str,
        query: str,
        k: int = 3,
    ) -> str:
        """
        Get relevant context for a specific agent.

        This is the main method agents use to retrieve RAG context.

        Args:
            agent_type: Type of agent (strategy, weather, tire, performance)
            query: The question or context being asked
            k: Number of relevant chunks to retrieve

        Returns:
            Formatted context string for the agent prompt
        """
        # Map agent type to category
        category_map = {
            "strategy": "strategy",
            "weather": "weather",
            "performance": "performance",
            "race_control": "race_control",
            "race_position": "race_position",
        }

        category = category_map.get(agent_type)

        # Search for relevant documents
        results = self.search(query=query, k=k, category=category)

        if not results:
            return ""

        # Format context
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "unknown")
            content = result["content"]
            context_parts.append(
                f"[Source {i}: {source}]\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    def is_context_loaded(self) -> bool:
        """Check if any context is currently loaded."""
        return self._current_context is not None and self._current_context.chunk_count > 0


# Singleton instance for app-wide use
_rag_manager_instance: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """
    Get the singleton RAGManager instance.

    Creates the instance on first call.

    Returns:
        RAGManager singleton instance
    """
    global _rag_manager_instance

    if _rag_manager_instance is None:
        _rag_manager_instance = RAGManager()

    return _rag_manager_instance


def reset_rag_manager() -> None:
    """Reset the singleton RAGManager instance."""
    global _rag_manager_instance
    _rag_manager_instance = None
