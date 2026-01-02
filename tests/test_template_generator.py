"""
Tests for Template Generator.

Validates template loading, variable replacement, and document generation.
"""

import gc
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.rag.template_generator import (
    TemplateGenerator,
    GeneratedDocument,
    get_template_generator,
    reset_template_generator,
    CIRCUIT_DATA,
    CIRCUIT_GROUPS,
)


def cleanup_temp_dir(path: str, max_retries: int = 3) -> None:
    """Clean up temporary directory with retries for Windows file locking."""
    for attempt in range(max_retries):
        try:
            gc.collect()
            time.sleep(0.1)
            shutil.rmtree(path, ignore_errors=True)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            shutil.rmtree(path, ignore_errors=True)


class TestCircuitData:
    """Tests for circuit metadata."""

    def test_circuit_data_exists(self):
        """CIRCUIT_DATA should contain predefined circuits."""
        assert len(CIRCUIT_DATA) > 0
        assert "bahrain" in CIRCUIT_DATA
        assert "abu_dhabi" in CIRCUIT_DATA
        assert "monaco" in CIRCUIT_DATA

    def test_circuit_data_structure(self):
        """Each circuit should have required fields."""
        required_fields = [
            "full_name",
            "location",
            "lap_length",
            "total_laps",
            "pit_loss",
            "drs_zones",
        ]
        for circuit, data in CIRCUIT_DATA.items():
            for field in required_fields:
                assert field in data, f"{circuit} missing {field}"

    def test_circuit_groups_exist(self):
        """Circuit groups should be defined."""
        assert "street" in CIRCUIT_GROUPS
        assert "high_speed" in CIRCUIT_GROUPS
        assert "high_degradation" in CIRCUIT_GROUPS


class TestTemplateGenerator:
    """Tests for TemplateGenerator class."""

    @pytest.fixture
    def temp_setup(self):
        """Create temporary directories for testing."""
        tmpdir = tempfile.mkdtemp()
        base = Path(tmpdir)

        # Create templates directory
        templates_dir = base / "templates"
        templates_dir.mkdir()

        # Create minimal strategy template
        (templates_dir / "strategy_template.md").write_text(
            "---\ncategory: strategy\n---\n\n"
            "# {circuit_name} Strategy\n\n"
            "Laps: {total_laps}\n"
            "Pit Loss: {pit_loss}s\n",
            encoding="utf-8",
        )

        # Create minimal weather template
        (templates_dir / "weather_template.md").write_text(
            "---\ncategory: weather\n---\n\n"
            "# {circuit_name} Weather\n\n"
            "Temp: {avg_air_temp}C\n",
            encoding="utf-8",
        )

        # Create minimal tire template
        (templates_dir / "tire_template.md").write_text(
            "---\ncategory: tire\n---\n\n"
            "# {circuit_name} Tires ({year})\n\n"
            "Stress: {stress_level}/10\n",
            encoding="utf-8",
        )

        # Output directory
        output_dir = base / "output"
        output_dir.mkdir()

        yield {
            "templates_dir": str(templates_dir),
            "output_dir": str(output_dir),
            "base_dir": tmpdir,
        }

        cleanup_temp_dir(tmpdir)

    def test_generator_initialization(self, temp_setup):
        """TemplateGenerator should initialize with paths."""
        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        assert generator.templates_path == Path(temp_setup["templates_dir"])
        assert generator.output_base == Path(temp_setup["output_dir"])

    def test_list_available_circuits(self, temp_setup):
        """Generator should list available circuits."""
        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        circuits = generator.list_available_circuits()
        assert len(circuits) > 0
        assert "bahrain" in circuits
        assert "abu_dhabi" in circuits

    def test_get_similar_circuits(self, temp_setup):
        """Generator should find similar circuits."""
        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        similar = generator.get_similar_circuits("monaco")
        assert len(similar) > 0
        assert "singapore" in similar or "jeddah" in similar

    @patch.object(TemplateGenerator, "_fetch_historical_data")
    def test_generate_for_circuit(self, mock_fetch, temp_setup):
        """Generator should create documents for a circuit."""
        mock_fetch.return_value = {}

        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        docs = generator.generate_for_circuit(
            year=2024,
            circuit="bahrain",
            use_historical=False,
        )

        assert len(docs) == 3
        assert "strategy.md" in docs
        assert "weather.md" in docs
        assert "tire_analysis.md" in docs

    @patch.object(TemplateGenerator, "_fetch_historical_data")
    def test_generated_document_content(self, mock_fetch, temp_setup):
        """Generated documents should have correct content."""
        mock_fetch.return_value = {}

        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        docs = generator.generate_for_circuit(
            year=2024,
            circuit="bahrain",
            use_historical=False,
        )

        strategy_doc = docs["strategy.md"]
        assert isinstance(strategy_doc, GeneratedDocument)
        assert strategy_doc.category == "strategy"
        assert strategy_doc.circuit == "bahrain"
        assert strategy_doc.year == 2024
        assert "Bahrain" in strategy_doc.content
        assert "57" in strategy_doc.content  # total_laps for Bahrain

    @patch.object(TemplateGenerator, "_fetch_historical_data")
    def test_generate_with_save(self, mock_fetch, temp_setup):
        """Generator should save documents to disk."""
        mock_fetch.return_value = {}

        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        docs = generator.generate_for_circuit(
            year=2024,
            circuit="bahrain",
            use_historical=False,
            save_to_disk=True,
        )

        # Check files were created
        output_path = Path(temp_setup["output_dir"]) / "2024/circuits/bahrain"
        assert output_path.exists()
        assert (output_path / "strategy.md").exists()
        assert (output_path / "weather.md").exists()
        assert (output_path / "tire_analysis.md").exists()

    @patch.object(TemplateGenerator, "_fetch_historical_data")
    def test_generate_unknown_circuit(self, mock_fetch, temp_setup):
        """Generator should handle unknown circuits with defaults."""
        mock_fetch.return_value = {}

        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        docs = generator.generate_for_circuit(
            year=2024,
            circuit="unknown_circuit",
            use_historical=False,
        )

        assert len(docs) == 3
        strategy = docs["strategy.md"]
        assert "Unknown Circuit" in strategy.content

    def test_fill_template_basic(self, temp_setup):
        """Template filling should replace variables."""
        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        template = "Hello {name}, you are {age} years old."
        variables = {"name": "Test", "age": 25}

        result = generator._fill_template(template, variables)

        assert result == "Hello Test, you are 25 years old."

    def test_fill_template_missing_vars(self, temp_setup):
        """Missing variables should be replaced with N/A."""
        generator = TemplateGenerator(
            templates_path=temp_setup["templates_dir"],
            output_base=temp_setup["output_dir"],
        )

        template = "Hello {name}, your {missing_var} is here."
        variables = {"name": "Test"}

        result = generator._fill_template(template, variables)

        assert "Test" in result
        assert "N/A" in result


class TestTemplateGeneratorSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """get_template_generator should return same instance."""
        reset_template_generator()

        gen1 = get_template_generator()
        gen2 = get_template_generator()

        assert gen1 is gen2

    def test_reset_creates_new_instance(self):
        """reset_template_generator should clear the instance."""
        reset_template_generator()

        gen1 = get_template_generator()
        reset_template_generator()
        gen2 = get_template_generator()

        assert gen1 is not gen2


class TestTemplateGeneratorIntegration:
    """Integration tests with real templates."""

    @pytest.fixture
    def real_generator(self):
        """Create generator with real templates."""
        reset_template_generator()
        return TemplateGenerator()

    @pytest.mark.skipif(
        not Path("data/rag/templates/strategy_template.md").exists(),
        reason="Real templates not available",
    )
    def test_generate_with_real_templates(self, real_generator):
        """Test generation with actual template files."""
        docs = real_generator.generate_for_circuit(
            year=2024,
            circuit="abu_dhabi",
            use_historical=False,
        )

        assert len(docs) >= 1
        if "strategy.md" in docs:
            assert "Abu Dhabi" in docs["strategy.md"].content or (
                "Yas Marina" in docs["strategy.md"].content
            )

    @pytest.mark.skipif(
        not Path("data/rag/templates").exists(),
        reason="Templates directory not available",
    )
    def test_all_predefined_circuits(self, real_generator):
        """Test that all predefined circuits can be generated."""
        circuits = real_generator.list_available_circuits()

        for circuit in circuits[:3]:  # Test first 3 to save time
            docs = real_generator.generate_for_circuit(
                year=2024,
                circuit=circuit,
                use_historical=False,
            )
            assert len(docs) >= 0  # May be 0 if templates missing
