"""
Tests for RAG DocumentLoader.

Validates document loading, chunking, and format conversion capabilities.
"""

import tempfile
from pathlib import Path

import pytest

from src.rag.document_loader import Document, DocumentInfo, DocumentLoader


class TestDocument:
    """Tests for Document dataclass."""

    def test_document_creation(self):
        """Document should store content and metadata."""
        doc = Document(
            content="Test content",
            metadata={"source": "test.md"},
        )
        assert doc.content == "Test content"
        assert doc.metadata["source"] == "test.md"
        assert doc.doc_id  # Should auto-generate

    def test_document_id_generation(self):
        """Document should generate unique ID if not provided."""
        doc1 = Document(content="Content A", metadata={"source": "a.md"})
        doc2 = Document(content="Content B", metadata={"source": "b.md"})

        assert doc1.doc_id != doc2.doc_id

    def test_document_with_explicit_id(self):
        """Document should use explicit ID when provided."""
        doc = Document(
            content="Test",
            metadata={},
            doc_id="custom-id-123",
        )
        assert doc.doc_id == "custom-id-123"


class TestDocumentLoader:
    """Tests for DocumentLoader class."""

    @pytest.fixture
    def temp_rag_dir(self):
        """Create temporary RAG directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Create global docs
            global_dir = base / "global"
            global_dir.mkdir()
            (global_dir / "basics.md").write_text(
                "# F1 Basics\n\nFormula 1 racing fundamentals.",
                encoding="utf-8",
            )

            # Create 2024 year docs
            year_dir = base / "2024"
            year_dir.mkdir()
            (year_dir / "regulations.md").write_text(
                "---\ncategory: fia\n---\n\n# 2024 Regulations\n\nKey rules.",
                encoding="utf-8",
            )

            # Create circuit docs
            circuit_dir = year_dir / "circuits" / "bahrain"
            circuit_dir.mkdir(parents=True)
            (circuit_dir / "strategy.md").write_text(
                "---\ncategory: strategy\ncircuit: bahrain\n---\n\n"
                "# Bahrain Strategy\n\nPit stop windows.",
                encoding="utf-8",
            )

            yield base

    def test_loader_initialization(self, temp_rag_dir):
        """DocumentLoader should initialize with base path."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))

        assert loader.base_path == temp_rag_dir
        assert loader.chunk_size == DocumentLoader.DEFAULT_CHUNK_SIZE
        assert loader.chunk_overlap == DocumentLoader.DEFAULT_CHUNK_OVERLAP

    def test_load_global_documents(self, temp_rag_dir):
        """Loader should load global documents."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))
        docs = loader.load_documents_for_context(year=2024)

        # Should include global and year docs
        sources = [d.metadata.get("source") for d in docs]
        assert any("global" in s for s in sources if s)
        assert any("2024" in s for s in sources if s)

    def test_load_circuit_documents(self, temp_rag_dir):
        """Loader should load circuit-specific documents."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))
        docs = loader.load_documents_for_context(year=2024, circuit="bahrain")

        # Should include circuit docs
        sources = [d.metadata.get("source") for d in docs if d.metadata]
        assert any("bahrain" in s for s in sources if s)

    def test_frontmatter_extraction(self, temp_rag_dir):
        """Loader should extract YAML frontmatter metadata."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))
        docs = loader.load_documents_for_context(year=2024, circuit="bahrain")

        # Find circuit doc with frontmatter
        circuit_docs = [
            d for d in docs
            if d.metadata.get("circuit") == "bahrain"
        ]

        assert len(circuit_docs) > 0
        assert circuit_docs[0].metadata.get("category") == "strategy"

    def test_missing_circuit(self, temp_rag_dir):
        """Loader should handle missing circuit gracefully."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))
        docs = loader.load_documents_for_context(year=2024, circuit="monaco")

        # Should still return global and year docs
        assert len(docs) > 0

    def test_chunking(self, temp_rag_dir):
        """Loader should chunk large documents."""
        # Create large document
        large_content = "# Large Doc\n\n" + ("Lorem ipsum. " * 500)
        large_file = temp_rag_dir / "global" / "large.md"
        large_file.write_text(large_content, encoding="utf-8")

        loader = DocumentLoader(
            base_path=str(temp_rag_dir),
            chunk_size=500,
            chunk_overlap=50,
        )
        docs = loader.load_documents_for_context(year=2024)

        # Large doc should produce multiple chunks
        large_chunks = [
            d for d in docs
            if d.metadata.get("filename") == "large.md"
        ]
        assert len(large_chunks) > 1

    def test_get_available_documents(self, temp_rag_dir):
        """Loader should list available documents by category."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))
        available = loader.get_available_documents(year=2024, circuit="bahrain")

        assert "global" in available
        assert "fia" in available
        assert "strategy" in available

    def test_categorize_file(self, temp_rag_dir):
        """Loader should categorize files correctly."""
        loader = DocumentLoader(base_path=str(temp_rag_dir))

        # Test filename patterns
        test_cases = [
            ("fia_regulations.md", "fia"),
            ("tire_compounds.md", "tire"),
            ("weather_forecast.md", "weather"),
            ("strategy_guide.md", "strategy"),
        ]

        for filename, expected_category in test_cases:
            test_file = temp_rag_dir / "global" / filename
            test_file.write_text("# Test", encoding="utf-8")

            category = loader._categorize_file(test_file)
            assert category == expected_category, (
                f"Expected {expected_category} for {filename}, got {category}"
            )


class TestDocumentLoaderIntegration:
    """Integration tests using actual data/rag directory."""

    @pytest.fixture
    def real_loader(self):
        """Create loader pointing to actual RAG directory."""
        return DocumentLoader(base_path="data/rag")

    @pytest.mark.skipif(
        not Path("data/rag/global").exists(),
        reason="RAG directory not populated",
    )
    def test_load_real_global_docs(self, real_loader):
        """Test loading from actual data/rag directory."""
        docs = real_loader.load_documents_for_context(year=2024)

        assert len(docs) > 0
        assert any("global" in d.metadata.get("source", "") for d in docs)

    @pytest.mark.skipif(
        not Path("data/rag/2024/circuits/abu_dhabi").exists(),
        reason="Abu Dhabi docs not available",
    )
    def test_load_abu_dhabi_docs(self, real_loader):
        """Test loading Abu Dhabi circuit documents."""
        docs = real_loader.load_documents_for_context(
            year=2024,
            circuit="abu_dhabi",
        )

        assert len(docs) > 0

        # Check for circuit-specific content
        circuit_docs = [
            d for d in docs
            if d.metadata.get("circuit") == "abu_dhabi"
        ]
        assert len(circuit_docs) > 0
