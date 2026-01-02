"""
Tests for RAG Manager.

Validates RAG context loading, document indexing, and search functionality.
"""

import gc
import shutil
import tempfile
import time
from pathlib import Path

import pytest

from src.rag.rag_manager import (
    RAGManager,
    RAGContext,
    RAGStats,
    get_rag_manager,
    reset_rag_manager,
)


def cleanup_temp_dir(path: str, max_retries: int = 3) -> None:
    """
    Clean up temporary directory with retries for Windows file locking.

    ChromaDB keeps file handles open on Windows, so we need to retry.
    """
    for attempt in range(max_retries):
        try:
            gc.collect()  # Force garbage collection to release handles
            time.sleep(0.1)  # Small delay for file handles to close
            shutil.rmtree(path, ignore_errors=True)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            # On last attempt, ignore errors
            shutil.rmtree(path, ignore_errors=True)


class TestRAGContext:
    """Tests for RAGContext dataclass."""

    def test_context_creation(self):
        """RAGContext should store year and circuit info."""
        context = RAGContext(
            year=2024,
            circuit="bahrain",
            document_count=5,
            chunk_count=25,
        )
        assert context.year == 2024
        assert context.circuit == "bahrain"
        assert context.document_count == 5
        assert context.chunk_count == 25

    def test_context_without_circuit(self):
        """RAGContext should work without circuit."""
        context = RAGContext(year=2024)
        assert context.year == 2024
        assert context.circuit is None
        assert context.document_count == 0


class TestRAGManagerUnit:
    """Unit tests for RAGManager with mocked dependencies."""

    @pytest.fixture
    def temp_rag_setup(self):
        """Create temporary directories for RAG testing."""
        tmpdir = tempfile.mkdtemp()
        base = Path(tmpdir)

        # Create RAG document structure
        rag_dir = base / "rag"

        # Global docs
        global_dir = rag_dir / "global"
        global_dir.mkdir(parents=True)
        (global_dir / "basics.md").write_text(
            "---\ncategory: global\n---\n\n# F1 Basics\n\n"
            "Formula 1 is the pinnacle of motorsport.",
            encoding="utf-8",
        )

        # Year docs
        year_dir = rag_dir / "2024"
        year_dir.mkdir()
        (year_dir / "regulations.md").write_text(
            "---\ncategory: fia\n---\n\n# 2024 Regulations\n\n"
            "Key regulation changes for 2024 season.",
            encoding="utf-8",
        )

        # Circuit docs
        circuit_dir = year_dir / "circuits" / "bahrain"
        circuit_dir.mkdir(parents=True)
        (circuit_dir / "strategy.md").write_text(
            "---\ncategory: strategy\ncircuit: bahrain\n---\n\n"
            "# Bahrain Strategy\n\nOptimal pit windows: lap 15-20.",
            encoding="utf-8",
        )
        (circuit_dir / "weather.md").write_text(
            "---\ncategory: weather\ncircuit: bahrain\n---\n\n"
            "# Bahrain Weather\n\nTypically hot and dry conditions.",
            encoding="utf-8",
        )

        # ChromaDB directory
        chromadb_dir = base / "chromadb"
        chromadb_dir.mkdir()

        yield {
            "rag_dir": str(rag_dir),
            "chromadb_dir": str(chromadb_dir),
            "base_dir": tmpdir,
        }

        # Manual cleanup with retry for Windows file locking
        cleanup_temp_dir(tmpdir)

    def test_manager_initialization(self, temp_rag_setup):
        """RAGManager should initialize with correct paths."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        assert manager.base_path == temp_rag_setup["rag_dir"]
        assert manager.persist_directory == temp_rag_setup["chromadb_dir"]
        assert manager.current_context is None

    def test_load_context_year_only(self, temp_rag_setup):
        """Manager should load global and year docs when no circuit specified."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        chunk_count = manager.load_context(year=2024)

        assert chunk_count > 0
        assert manager.current_context is not None
        assert manager.current_context.year == 2024
        assert manager.current_context.circuit is None

    def test_load_context_with_circuit(self, temp_rag_setup):
        """Manager should load circuit-specific docs."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        chunk_count = manager.load_context(year=2024, circuit="bahrain")

        assert chunk_count > 0
        assert manager.current_context is not None
        assert manager.current_context.year == 2024
        assert manager.current_context.circuit == "bahrain"
        # Should have docs from global, year, and circuit
        assert manager.current_context.document_count >= 3

    def test_reload_context(self, temp_rag_setup):
        """Manager should reload current context."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        # Load initial context
        manager.load_context(year=2024, circuit="bahrain")
        assert manager.current_context is not None
        initial_count = manager.current_context.chunk_count

        # Reload
        reload_count = manager.reload()

        assert reload_count == initial_count
        assert manager.current_context is not None
        assert manager.current_context.year == 2024
        assert manager.current_context.circuit == "bahrain"

    def test_clear_collection(self, temp_rag_setup):
        """Manager should clear all documents."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        # Load and then clear
        manager.load_context(year=2024)
        manager.clear_collection()

        stats = manager.get_stats()
        assert stats.total_documents == 0

    def test_search(self, temp_rag_setup):
        """Manager should search for relevant documents."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        manager.load_context(year=2024, circuit="bahrain")

        # Search for strategy content
        results = manager.search("pit stop windows", k=3)

        assert len(results) > 0
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "score" in results[0]

    def test_search_with_category_filter(self, temp_rag_setup):
        """Manager should filter search by category."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        manager.load_context(year=2024, circuit="bahrain")

        # Search only strategy category
        results = manager.search("conditions", k=3, category="strategy")

        # All results should be strategy category
        for result in results:
            if result["metadata"].get("category"):
                assert result["metadata"]["category"] == "strategy"

    def test_get_stats(self, temp_rag_setup):
        """Manager should return correct statistics."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        manager.load_context(year=2024, circuit="bahrain")

        stats = manager.get_stats()

        assert isinstance(stats, RAGStats)
        assert stats.total_documents > 0
        assert stats.collection_name == "f1_rag_documents"
        assert stats.current_context is not None
        assert stats.current_context.year == 2024

    def test_list_documents(self, temp_rag_setup):
        """Manager should list documents by category."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        manager.load_context(year=2024, circuit="bahrain")

        docs = manager.list_documents()

        assert isinstance(docs, dict)
        assert "global" in docs
        assert "strategy" in docs
        assert "weather" in docs
        assert "fia" in docs

    def test_get_context_for_agent(self, temp_rag_setup):
        """Manager should return formatted context for agents."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        manager.load_context(year=2024, circuit="bahrain")

        context = manager.get_context_for_agent(
            agent_type="strategy",
            query="What are the optimal pit windows?",
            k=2,
        )

        assert isinstance(context, str)
        assert len(context) > 0
        assert "[Source" in context

    def test_is_context_loaded(self, temp_rag_setup):
        """Manager should correctly report if context is loaded."""
        manager = RAGManager(
            base_path=temp_rag_setup["rag_dir"],
            persist_directory=temp_rag_setup["chromadb_dir"],
        )

        assert not manager.is_context_loaded()

        manager.load_context(year=2024)

        assert manager.is_context_loaded()

        manager.clear_collection()

        # Context object exists but has 0 chunks after clear
        # Need to reload to check
        manager._current_context = None
        assert not manager.is_context_loaded()


class TestRAGManagerSingleton:
    """Tests for singleton pattern."""

    def test_get_rag_manager_singleton(self):
        """get_rag_manager should return same instance."""
        reset_rag_manager()

        manager1 = get_rag_manager()
        manager2 = get_rag_manager()

        assert manager1 is manager2

    def test_reset_rag_manager(self):
        """reset_rag_manager should clear singleton."""
        manager1 = get_rag_manager()
        reset_rag_manager()
        manager2 = get_rag_manager()

        assert manager1 is not manager2


class TestRAGManagerIntegration:
    """Integration tests using actual data/rag directory."""

    @pytest.fixture
    def real_manager(self):
        """Create manager with actual data directory."""
        reset_rag_manager()
        return RAGManager()

    @pytest.mark.skipif(
        not Path("data/rag/global").exists(),
        reason="RAG directory not populated",
    )
    def test_load_real_context(self, real_manager):
        """Test loading from actual data/rag directory."""
        chunk_count = real_manager.load_context(year=2024)

        assert chunk_count > 0
        assert real_manager.current_context is not None

    @pytest.mark.skipif(
        not Path("data/rag/2024/circuits/abu_dhabi").exists(),
        reason="Abu Dhabi docs not available",
    )
    def test_load_abu_dhabi_context(self, real_manager):
        """Test loading Abu Dhabi specific context."""
        chunk_count = real_manager.load_context(
            year=2024,
            circuit="abu_dhabi",
        )

        assert chunk_count > 0

        # Search for Abu Dhabi specific content
        results = real_manager.search("DRS zones", k=3)
        assert len(results) > 0
