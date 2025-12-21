"""
ChromaDB vector store implementation.

Local, persistent vector store using ChromaDB for F1 data retrieval.
"""

import logging
import uuid
from pathlib import Path
from typing import Any

try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .vector_store import VectorStore, SearchResult
from .embeddings import EmbeddingsProvider

logger = logging.getLogger(__name__)


class ChromaDBStore(VectorStore):
    """ChromaDB implementation of vector store."""

    def __init__(
        self,
        collection_name: str = "f1_data",
        persist_directory: str = "./data/chromadb",
        embeddings_model: str = "all-MiniLM-L6-v2",
        embeddings_device: str = "cpu"
    ):
        """
        Initialize ChromaDB store.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist data
            embeddings_model: Sentence-transformers model name
            embeddings_device: Device for embeddings ('cpu' or 'cuda')

        Raises:
            ImportError: If chromadb not installed
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb not installed. "
                "Install with: pip install chromadb"
            )

        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize embeddings provider
        self.embeddings = EmbeddingsProvider(
            model_name=embeddings_model,
            device=embeddings_device
        )

        # Initialize ChromaDB client
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(  # type: ignore
            path=str(self.persist_directory),
            settings=Settings(  # type: ignore
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(
            f"ChromaDB initialized: collection='{collection_name}', "
            f"path={persist_directory}"
        )

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None
    ) -> list[str]:
        """
        Add documents to ChromaDB.

        Args:
            documents: List of text documents
            metadatas: List of metadata dicts
            ids: Optional list of document IDs

        Returns:
            List of document IDs
        """
        if not documents:
            logger.warning("No documents to add")
            return []

        if len(documents) != len(metadatas):
            raise ValueError(
                f"Documents ({len(documents)}) and metadatas "
                f"({len(metadatas)}) must have same length"
            )

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        elif len(ids) != len(documents):
            raise ValueError(
                f"IDs ({len(ids)}) must match documents "
                f"({len(documents)})"
            )

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} documents")
        embeddings = self.embeddings.embed_documents(documents)

        # Add to collection
        self.collection.add(
            embeddings=embeddings,  # type: ignore
            documents=documents,
            metadatas=metadatas,  # type: ignore
            ids=ids
        )

        logger.info(f"Added {len(documents)} documents to ChromaDB")
        return ids

    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """
        Search for similar documents in ChromaDB.

        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )

        # Convert to SearchResult objects
        search_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                # ChromaDB returns distances (lower is better)
                # Convert to similarity score (higher is better)
                distance = results["distances"][0][i]  # type: ignore
                score = 1.0 / (1.0 + distance)

                search_results.append(SearchResult(
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],  # type: ignore
                    score=score,
                    id=results["ids"][0][i]
                ))

        logger.info(f"Search returned {len(search_results)} results")
        return search_results

    def delete(self, ids: list[str]) -> None:
        """
        Delete documents from ChromaDB.

        Args:
            ids: List of document IDs to delete
        """
        if not ids:
            logger.warning("No IDs provided for deletion")
            return

        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents from ChromaDB")

    def get_collection_stats(self) -> dict[str, Any]:
        """
        Get ChromaDB collection statistics.

        Returns:
            Dictionary with collection stats
        """
        count = self.collection.count()
        embeddings_info = self.embeddings.get_model_info()

        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": str(self.persist_directory),
            "embeddings": embeddings_info
        }

    def clear(self) -> None:
        """Clear all documents from the collection."""
        # Delete the collection and recreate it
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Cleared collection: {self.collection_name}")

    def get_all_documents(self) -> list[dict[str, Any]]:
        """
        Get all documents from the collection.

        Returns:
            List of documents with metadata
        """
        count = self.collection.count()
        if count == 0:
            return []

        results = self.collection.get(
            include=["documents", "metadatas"]
        )

        documents = []
        for i in range(len(results["ids"])):
            documents.append({
                "id": results["ids"][i],
                "content": results["documents"][i],  # type: ignore
                "metadata": results["metadatas"][i]  # type: ignore
            })

        return documents
