"""
Integration tests for ChromaDB vector store.

These tests require chromadb and sentence-transformers to be installed.
"""

import pytest
import tempfile

from src.rag.chromadb_store import ChromaDBStore


@pytest.fixture
def temp_chromadb_dir():
    """Create temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_documents():
    """Sample F1 documents for testing."""
    return [
        "Max Verstappen won the 2023 Formula 1 World Championship.",
        "Lewis Hamilton has won 7 World Championships.",
        "Ferrari is the oldest team in Formula 1 history."
    ]


@pytest.fixture
def sample_metadatas():
    """Sample metadata for documents."""
    return [
        {"year": 2023, "driver": "Verstappen", "category": "championship"},
        {"year": 2020, "driver": "Hamilton", "category": "championship"},
        {"year": 2024, "team": "Ferrari", "category": "team_info"}
    ]


class TestChromaDBIntegration:
    """Integration tests with real ChromaDB."""

    def test_full_workflow(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test complete workflow: add, search, delete."""
        # Create store
        store = ChromaDBStore(
            collection_name="test_integration",
            persist_directory=temp_chromadb_dir,
            embeddings_model="all-MiniLM-L6-v2",
            embeddings_device="cpu"
        )

        # Verify empty initially
        stats = store.get_collection_stats()
        assert stats["document_count"] == 0

        # Add documents
        ids = store.add_documents(sample_documents, sample_metadatas)
        assert len(ids) == 3

        # Verify count
        stats = store.get_collection_stats()
        assert stats["document_count"] == 3

        # Search for World Championship
        results = store.search("World Championship wins", k=2)
        assert len(results) == 2
        assert results[0].score > 0
        assert "Championship" in results[0].content

        # Search with metadata filter
        results = store.search(
            "driver information",
            k=5,
            filter_metadata={"category": "championship"}
        )
        assert len(results) == 2  # Only championship docs

        # Delete one document
        store.delete([ids[0]])
        stats = store.get_collection_stats()
        assert stats["document_count"] == 2

        # Clear all
        store.clear()
        stats = store.get_collection_stats()
        assert stats["document_count"] == 0

    def test_embeddings_quality(self, temp_chromadb_dir):
        """Test that embeddings produce meaningful similarities."""
        store = ChromaDBStore(
            collection_name="test_embeddings",
            persist_directory=temp_chromadb_dir
        )

        # Add F1-related documents
        documents = [
            "Max Verstappen drives for Red Bull Racing",
            "Lewis Hamilton is a Mercedes driver",
            "The Monaco Grand Prix is a street circuit",
            "DRS improves overtaking in Formula 1"
        ]
        metadatas = [{"id": i} for i in range(len(documents))]
        store.add_documents(documents, metadatas)

        # Search for driver-related content
        results = store.search("Red Bull driver", k=2)
        assert len(results) == 2
        # Should return Verstappen doc first
        assert "Verstappen" in results[0].content

        # Search for circuit-related content
        results = store.search("race track", k=2)
        assert len(results) == 2
        # Should prioritize Monaco circuit doc
        assert "circuit" in results[0].content.lower()

        store.clear()

    def test_persistence(self, temp_chromadb_dir, sample_documents):
        """Test that data persists across store instances."""
        metadatas = [{"id": i} for i in range(len(sample_documents))]

        # Create store and add documents
        store1 = ChromaDBStore(
            collection_name="test_persist",
            persist_directory=temp_chromadb_dir
        )
        ids = store1.add_documents(sample_documents, metadatas)
        count1 = store1.get_collection_stats()["document_count"]

        # Create new store instance with same directory
        store2 = ChromaDBStore(
            collection_name="test_persist",
            persist_directory=temp_chromadb_dir
        )
        count2 = store2.get_collection_stats()["document_count"]

        # Data should persist
        assert count1 == count2 == len(sample_documents)

        # Search should work in new instance
        results = store2.search("Verstappen", k=1)
        assert len(results) == 1

        store2.clear()
