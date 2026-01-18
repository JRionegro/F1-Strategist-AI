"""
Unit and integration tests for RAG vector store implementations.

Tests cover embeddings generation, ChromaDB operations, and search.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.rag.vector_store import VectorStore, SearchResult
from src.rag.embeddings import EmbeddingsProvider
from src.rag.config import get_chromadb_config, get_vector_store_provider

# Import ChromaDBStore directly - use real ChromaDB for all tests
# Python 3.13 + ChromaDB 1.3.7 has strict type validation that rejects mocks
from src.rag.chromadb_store import ChromaDBStore


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def temp_chromadb_dir():
    """Create temporary directory for ChromaDB."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_embeddings():
    """Mock embeddings provider."""
    mock = Mock(spec=EmbeddingsProvider)
    mock.embed_documents.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9]
    ]
    mock.embed_query.return_value = [0.1, 0.2, 0.3]
    mock.get_embedding_dimension.return_value = 3
    mock.get_model_info.return_value = {
        "model_name": "test-model",
        "device": "cpu",
        "dimension": 3,
        "max_seq_length": 512
    }
    return mock


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


# ============================================
# Embeddings Tests
# ============================================

class TestEmbeddingsProvider:
    """Test embeddings provider."""

    @patch("src.rag.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("src.rag.embeddings.SentenceTransformer")
    def test_initialization(self, mock_transformer):
        """Test embeddings provider initialization."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        provider = EmbeddingsProvider(
            model_name="all-MiniLM-L6-v2",
            device="cpu"
        )

        assert provider.model_name == "all-MiniLM-L6-v2"
        assert provider.device == "cpu"
        mock_transformer.assert_called_once_with(
            "all-MiniLM-L6-v2",
            device="cpu"
        )

    @patch("src.rag.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", False)
    def test_import_error(self):
        """Test error when sentence-transformers not installed."""
        with pytest.raises(ImportError, match="sentence-transformers"):
            EmbeddingsProvider()

    @patch("src.rag.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("src.rag.embeddings.SentenceTransformer")
    def test_embed_documents(self, mock_transformer):
        """Test embedding multiple documents."""
        mock_model = Mock()
        mock_model.encode.return_value = Mock(
            tolist=lambda: [[0.1, 0.2], [0.3, 0.4]]
        )
        mock_transformer.return_value = mock_model

        provider = EmbeddingsProvider()
        texts = ["text1", "text2"]
        embeddings = provider.embed_documents(texts)

        assert len(embeddings) == 2
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode.assert_called_once()

    @patch("src.rag.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("src.rag.embeddings.SentenceTransformer")
    def test_embed_query(self, mock_transformer):
        """Test embedding single query."""
        mock_model = Mock()
        mock_model.encode.return_value = Mock(
            tolist=lambda: [0.5, 0.6]
        )
        mock_transformer.return_value = mock_model

        provider = EmbeddingsProvider()
        embedding = provider.embed_query("test query")

        assert embedding == [0.5, 0.6]
        mock_model.encode.assert_called_once()

    @patch("src.rag.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("src.rag.embeddings.SentenceTransformer")
    def test_get_embedding_dimension(self, mock_transformer):
        """Test getting embedding dimension."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_transformer.return_value = mock_model

        provider = EmbeddingsProvider()
        dimension = provider.get_embedding_dimension()

        assert dimension == 384


# ============================================
# ChromaDB Store Tests (Real ChromaDB Only)
# ============================================
# Note: Python 3.13 + ChromaDB 1.3.7 has strict type validation
# that rejects MagicMocks. All ChromaDB tests use real instances
# with temporary directories instead of mocks.

class TestChromaDBStore:
    """Test ChromaDB store with real ChromaDB instances."""

    def test_initialization(self, temp_chromadb_dir):
        """Test ChromaDB store initialization."""
        store = ChromaDBStore(
            collection_name="test_collection",
            persist_directory=temp_chromadb_dir,
            embeddings_model="all-MiniLM-L6-v2",
            embeddings_device="cpu"
        )

        assert store.collection_name == "test_collection"
        assert Path(store.persist_directory) == Path(temp_chromadb_dir)
        assert store.collection is not None

        # Clean up
        store.clear()

    @patch("src.rag.chromadb_store.CHROMADB_AVAILABLE", False)
    def test_import_error(self):
        """Test error when chromadb not installed."""
        with pytest.raises(ImportError, match="chromadb"):
            ChromaDBStore()

    def test_add_documents(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test adding documents to ChromaDB."""
        store = ChromaDBStore(
            collection_name="test_add",
            persist_directory=temp_chromadb_dir
        )

        ids = store.add_documents(sample_documents, sample_metadatas)

        assert len(ids) == 3
        stats = store.get_collection_stats()
        assert stats["document_count"] == 3

        # Clean up
        store.clear()

    def test_add_documents_validation(self, temp_chromadb_dir):
        """Test validation when adding documents."""
        store = ChromaDBStore(
            collection_name="test_validation",
            persist_directory=temp_chromadb_dir
        )

        # Test mismatched lengths
        with pytest.raises(ValueError, match="must have same length"):
            store.add_documents(
                documents=["doc1", "doc2"],
                metadatas=[{"key": "value"}]
            )

        # Clean up
        store.clear()

    def test_search(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test searching for similar documents."""
        store = ChromaDBStore(
            collection_name="test_search",
            persist_directory=temp_chromadb_dir
        )

        # Add documents first
        store.add_documents(sample_documents, sample_metadatas)

        # Search
        results = store.search("World Championship", k=2)

        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert "Championship" in results[0].content
        assert results[0].score > 0

        # Clean up
        store.clear()

    def test_delete(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test deleting documents."""
        store = ChromaDBStore(
            collection_name="test_delete",
            persist_directory=temp_chromadb_dir
        )

        # Add documents
        ids = store.add_documents(sample_documents, sample_metadatas)
        assert store.get_collection_stats()["document_count"] == 3

        # Delete one
        store.delete([ids[0]])
        assert store.get_collection_stats()["document_count"] == 2

        # Clean up
        store.clear()

    def test_get_collection_stats(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test getting collection statistics."""
        store = ChromaDBStore(
            collection_name="test_stats",
            persist_directory=temp_chromadb_dir
        )

        # Initially empty
        stats = store.get_collection_stats()
        assert stats["document_count"] == 0
        assert "collection_name" in stats
        assert "embeddings" in stats

        # Add documents
        store.add_documents(sample_documents, sample_metadatas)
        stats = store.get_collection_stats()
        assert stats["document_count"] == 3

        # Clean up
        store.clear()

    def test_clear(
        self,
        temp_chromadb_dir,
        sample_documents,
        sample_metadatas
    ):
        """Test clearing collection."""
        store = ChromaDBStore(
            collection_name="test_clear",
            persist_directory=temp_chromadb_dir
        )

        # Add documents
        store.add_documents(sample_documents, sample_metadatas)
        assert store.get_collection_stats()["document_count"] == 3

        # Clear
        store.clear()
        stats = store.get_collection_stats()
        assert stats["document_count"] == 0


# ============================================
# Configuration Tests
# ============================================

class TestConfig:
    """Test configuration loading."""

    def test_get_chromadb_config(self):
        """Test loading ChromaDB config."""
        config = get_chromadb_config()

        assert "persist_directory" in config
        assert "embeddings_model" in config
        assert "embeddings_device" in config
        assert "collection_name" in config

    def test_get_vector_store_provider(self):
        """Test getting vector store provider."""
        provider = get_vector_store_provider()
        assert provider in ["chromadb", "pinecone"]


# ============================================
# Integration Tests (Require ChromaDB)
# ============================================

@pytest.mark.integration
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
