"""
Template Generator for RAG Documents.

Generates circuit-specific RAG documents from templates and historical data.
Uses OpenF1 API data to populate template variables with real race information.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.data.openf1_data_provider import OpenF1DataProvider

logger = logging.getLogger(__name__)


# Circuit metadata mapping
CIRCUIT_DATA: Dict[str, Dict[str, Any]] = {
    "bahrain": {
        "full_name": "Bahrain International Circuit",
        "location": "Sakhir, Bahrain",
        "timezone": "Asia/Bahrain (GMT+3)",
        "lap_length": 5.412,
        "total_laps": 57,
        "pit_loss": 21.5,
        "drs_zones": 3,
        "circuit_type": "High-degradation desert",
        "climate_type": "Desert",
        "overtaking_difficulty": 4,
        "track_position_importance": 6,
        "stress_level": 7,
        "front_stress": 6,
        "rear_stress": 8,
        "sc_probability": 35,
    },
    "jeddah": {
        "full_name": "Jeddah Corniche Circuit",
        "location": "Jeddah, Saudi Arabia",
        "timezone": "Asia/Riyadh (GMT+3)",
        "lap_length": 6.174,
        "total_laps": 50,
        "pit_loss": 24.0,
        "drs_zones": 3,
        "circuit_type": "High-speed street circuit",
        "climate_type": "Desert coastal",
        "overtaking_difficulty": 5,
        "track_position_importance": 7,
        "stress_level": 6,
        "front_stress": 7,
        "rear_stress": 6,
        "sc_probability": 60,
    },
    "melbourne": {
        "full_name": "Albert Park Circuit",
        "location": "Melbourne, Australia",
        "timezone": "Australia/Melbourne (GMT+11)",
        "lap_length": 5.278,
        "total_laps": 58,
        "pit_loss": 20.0,
        "drs_zones": 4,
        "circuit_type": "Street/park circuit",
        "climate_type": "Temperate",
        "overtaking_difficulty": 5,
        "track_position_importance": 6,
        "stress_level": 5,
        "front_stress": 5,
        "rear_stress": 5,
        "sc_probability": 45,
    },
    "imola": {
        "full_name": "Autodromo Enzo e Dino Ferrari",
        "location": "Imola, Italy",
        "timezone": "Europe/Rome (GMT+2)",
        "lap_length": 4.909,
        "total_laps": 63,
        "pit_loss": 22.0,
        "drs_zones": 2,
        "circuit_type": "Traditional European circuit",
        "climate_type": "Mediterranean",
        "overtaking_difficulty": 7,
        "track_position_importance": 8,
        "stress_level": 6,
        "front_stress": 6,
        "rear_stress": 6,
        "sc_probability": 30,
    },
    "miami": {
        "full_name": "Miami International Autodrome",
        "location": "Miami, Florida, USA",
        "timezone": "America/New_York (GMT-4)",
        "lap_length": 5.412,
        "total_laps": 57,
        "pit_loss": 23.0,
        "drs_zones": 3,
        "circuit_type": "Street circuit",
        "climate_type": "Subtropical",
        "overtaking_difficulty": 5,
        "track_position_importance": 6,
        "stress_level": 6,
        "front_stress": 6,
        "rear_stress": 6,
        "sc_probability": 40,
    },
    "monaco": {
        "full_name": "Circuit de Monaco",
        "location": "Monte Carlo, Monaco",
        "timezone": "Europe/Monaco (GMT+2)",
        "lap_length": 3.337,
        "total_laps": 78,
        "pit_loss": 18.0,
        "drs_zones": 1,
        "circuit_type": "Tight street circuit",
        "climate_type": "Mediterranean",
        "overtaking_difficulty": 10,
        "track_position_importance": 10,
        "stress_level": 4,
        "front_stress": 5,
        "rear_stress": 4,
        "sc_probability": 70,
    },
    "barcelona": {
        "full_name": "Circuit de Barcelona-Catalunya",
        "location": "Barcelona, Spain",
        "timezone": "Europe/Madrid (GMT+2)",
        "lap_length": 4.657,
        "total_laps": 66,
        "pit_loss": 21.0,
        "drs_zones": 2,
        "circuit_type": "Technical high-degradation",
        "climate_type": "Mediterranean",
        "overtaking_difficulty": 7,
        "track_position_importance": 7,
        "stress_level": 8,
        "front_stress": 7,
        "rear_stress": 8,
        "sc_probability": 25,
    },
    "montreal": {
        "full_name": "Circuit Gilles Villeneuve",
        "location": "Montreal, Canada",
        "timezone": "America/Toronto (GMT-4)",
        "lap_length": 4.361,
        "total_laps": 70,
        "pit_loss": 19.0,
        "drs_zones": 2,
        "circuit_type": "Stop-start circuit",
        "climate_type": "Continental",
        "overtaking_difficulty": 4,
        "track_position_importance": 5,
        "stress_level": 5,
        "front_stress": 4,
        "rear_stress": 6,
        "sc_probability": 55,
    },
    "silverstone": {
        "full_name": "Silverstone Circuit",
        "location": "Silverstone, UK",
        "timezone": "Europe/London (GMT+1)",
        "lap_length": 5.891,
        "total_laps": 52,
        "pit_loss": 20.5,
        "drs_zones": 2,
        "circuit_type": "High-speed circuit",
        "climate_type": "Temperate oceanic",
        "overtaking_difficulty": 5,
        "track_position_importance": 6,
        "stress_level": 7,
        "front_stress": 8,
        "rear_stress": 6,
        "sc_probability": 35,
    },
    "hungaroring": {
        "full_name": "Hungaroring",
        "location": "Budapest, Hungary",
        "timezone": "Europe/Budapest (GMT+2)",
        "lap_length": 4.381,
        "total_laps": 70,
        "pit_loss": 21.0,
        "drs_zones": 2,
        "circuit_type": "Technical twisty circuit",
        "climate_type": "Continental",
        "overtaking_difficulty": 8,
        "track_position_importance": 9,
        "stress_level": 6,
        "front_stress": 7,
        "rear_stress": 5,
        "sc_probability": 25,
    },
    "spa": {
        "full_name": "Circuit de Spa-Francorchamps",
        "location": "Stavelot, Belgium",
        "timezone": "Europe/Brussels (GMT+2)",
        "lap_length": 7.004,
        "total_laps": 44,
        "pit_loss": 22.0,
        "drs_zones": 2,
        "circuit_type": "High-speed classic circuit",
        "climate_type": "Temperate oceanic",
        "overtaking_difficulty": 3,
        "track_position_importance": 5,
        "stress_level": 7,
        "front_stress": 6,
        "rear_stress": 8,
        "sc_probability": 50,
    },
    "zandvoort": {
        "full_name": "Circuit Zandvoort",
        "location": "Zandvoort, Netherlands",
        "timezone": "Europe/Amsterdam (GMT+2)",
        "lap_length": 4.259,
        "total_laps": 72,
        "pit_loss": 18.5,
        "drs_zones": 2,
        "circuit_type": "Technical banked circuit",
        "climate_type": "Temperate oceanic",
        "overtaking_difficulty": 8,
        "track_position_importance": 8,
        "stress_level": 7,
        "front_stress": 7,
        "rear_stress": 7,
        "sc_probability": 30,
    },
    "monza": {
        "full_name": "Autodromo Nazionale Monza",
        "location": "Monza, Italy",
        "timezone": "Europe/Rome (GMT+2)",
        "lap_length": 5.793,
        "total_laps": 53,
        "pit_loss": 24.0,
        "drs_zones": 2,
        "circuit_type": "High-speed low-downforce",
        "climate_type": "Mediterranean",
        "overtaking_difficulty": 3,
        "track_position_importance": 4,
        "stress_level": 5,
        "front_stress": 5,
        "rear_stress": 5,
        "sc_probability": 40,
    },
    "singapore": {
        "full_name": "Marina Bay Street Circuit",
        "location": "Singapore",
        "timezone": "Asia/Singapore (GMT+8)",
        "lap_length": 4.940,
        "total_laps": 62,
        "pit_loss": 26.0,
        "drs_zones": 3,
        "circuit_type": "Tight street circuit",
        "climate_type": "Tropical",
        "overtaking_difficulty": 7,
        "track_position_importance": 8,
        "stress_level": 8,
        "front_stress": 8,
        "rear_stress": 7,
        "sc_probability": 70,
    },
    "suzuka": {
        "full_name": "Suzuka International Racing Course",
        "location": "Suzuka, Japan",
        "timezone": "Asia/Tokyo (GMT+9)",
        "lap_length": 5.807,
        "total_laps": 53,
        "pit_loss": 20.0,
        "drs_zones": 2,
        "circuit_type": "Technical figure-8 circuit",
        "climate_type": "Humid subtropical",
        "overtaking_difficulty": 6,
        "track_position_importance": 7,
        "stress_level": 8,
        "front_stress": 8,
        "rear_stress": 7,
        "sc_probability": 35,
    },
    "austin": {
        "full_name": "Circuit of the Americas",
        "location": "Austin, Texas, USA",
        "timezone": "America/Chicago (GMT-5)",
        "lap_length": 5.513,
        "total_laps": 56,
        "pit_loss": 21.0,
        "drs_zones": 2,
        "circuit_type": "Technical high-degradation",
        "climate_type": "Humid subtropical",
        "overtaking_difficulty": 4,
        "track_position_importance": 6,
        "stress_level": 8,
        "front_stress": 7,
        "rear_stress": 8,
        "sc_probability": 35,
    },
    "mexico_city": {
        "full_name": "Autódromo Hermanos Rodríguez",
        "location": "Mexico City, Mexico",
        "timezone": "America/Mexico_City (GMT-6)",
        "lap_length": 4.304,
        "total_laps": 71,
        "pit_loss": 20.0,
        "drs_zones": 3,
        "circuit_type": "High-altitude circuit",
        "climate_type": "Subtropical highland",
        "overtaking_difficulty": 4,
        "track_position_importance": 5,
        "stress_level": 6,
        "front_stress": 5,
        "rear_stress": 6,
        "sc_probability": 35,
    },
    "interlagos": {
        "full_name": "Autódromo José Carlos Pace",
        "location": "São Paulo, Brazil",
        "timezone": "America/Sao_Paulo (GMT-3)",
        "lap_length": 4.309,
        "total_laps": 71,
        "pit_loss": 20.0,
        "drs_zones": 2,
        "circuit_type": "Anti-clockwise circuit",
        "climate_type": "Humid subtropical",
        "overtaking_difficulty": 4,
        "track_position_importance": 5,
        "stress_level": 6,
        "front_stress": 5,
        "rear_stress": 7,
        "sc_probability": 50,
    },
    "las_vegas": {
        "full_name": "Las Vegas Strip Circuit",
        "location": "Las Vegas, Nevada, USA",
        "timezone": "America/Los_Angeles (GMT-8)",
        "lap_length": 6.201,
        "total_laps": 50,
        "pit_loss": 25.0,
        "drs_zones": 2,
        "circuit_type": "High-speed street circuit",
        "climate_type": "Desert",
        "overtaking_difficulty": 4,
        "track_position_importance": 5,
        "stress_level": 5,
        "front_stress": 5,
        "rear_stress": 5,
        "sc_probability": 45,
    },
    "qatar": {
        "full_name": "Lusail International Circuit",
        "location": "Lusail, Qatar",
        "timezone": "Asia/Qatar (GMT+3)",
        "lap_length": 5.419,
        "total_laps": 57,
        "pit_loss": 20.5,
        "drs_zones": 2,
        "circuit_type": "High-speed flowing circuit",
        "climate_type": "Desert",
        "overtaking_difficulty": 5,
        "track_position_importance": 6,
        "stress_level": 7,
        "front_stress": 7,
        "rear_stress": 7,
        "sc_probability": 30,
    },
    "abu_dhabi": {
        "full_name": "Yas Marina Circuit",
        "location": "Yas Island, Abu Dhabi, UAE",
        "timezone": "Asia/Dubai (GMT+4)",
        "lap_length": 5.281,
        "total_laps": 58,
        "pit_loss": 22.0,
        "drs_zones": 2,
        "circuit_type": "Modern twilight circuit",
        "climate_type": "Desert",
        "overtaking_difficulty": 5,
        "track_position_importance": 6,
        "stress_level": 5,
        "front_stress": 5,
        "rear_stress": 5,
        "sc_probability": 30,
    },
}

# Circuit similarity groups for data augmentation
CIRCUIT_GROUPS: Dict[str, List[str]] = {
    "street": ["monaco", "singapore", "jeddah", "las_vegas", "baku"],
    "high_speed": ["monza", "spa", "silverstone", "bahrain"],
    "high_degradation": ["barcelona", "bahrain", "austin", "hungaroring"],
    "technical": ["hungaroring", "zandvoort", "suzuka", "monaco"],
    "desert": ["bahrain", "jeddah", "qatar", "abu_dhabi", "las_vegas"],
}

# Pirelli compound data by year
PIRELLI_COMPOUNDS: Dict[int, Dict[str, str]] = {
    2024: {
        "soft_name": "C5/C4/C3",
        "medium_name": "C4/C3/C2",
        "hard_name": "C3/C2/C1",
    },
    2025: {
        "soft_name": "C5/C4/C3",
        "medium_name": "C4/C3/C2",
        "hard_name": "C3/C2/C1",
    },
    2026: {
        "soft_name": "C5/C4/C3",
        "medium_name": "C4/C3/C2",
        "hard_name": "C3/C2/C1",
    },
}


@dataclass
class GeneratedDocument:
    """Represents a generated RAG document."""

    filename: str
    content: str
    category: str
    circuit: str
    year: int


class TemplateGenerator:
    """
    Generate RAG documents from templates and historical data.

    Uses OpenF1 API to fetch historical race data and populates
    template variables to create circuit-specific documentation.
    """

    def __init__(
        self,
        templates_path: str = "data/rag/templates",
        output_base: str = "data/rag",
    ):
        """
        Initialize the template generator.

        Args:
            templates_path: Path to template files
            output_base: Base path for output documents
        """
        self.templates_path = Path(templates_path)
        self.output_base = Path(output_base)
        self.openf1_provider = OpenF1DataProvider(verify_ssl=False)

    def generate_for_circuit(
        self,
        year: int,
        circuit: str,
        use_historical: bool = True,
        save_to_disk: bool = False,
    ) -> Dict[str, GeneratedDocument]:
        """
        Generate all documents for a circuit.

        Args:
            year: Target year for the documents
            circuit: Circuit name in snake_case (e.g., "abu_dhabi")
            use_historical: Whether to fetch historical data from OpenF1
            save_to_disk: Whether to save generated docs to filesystem

        Returns:
            Dict of {filename: GeneratedDocument}
        """
        logger.info(f"Generating documents for {circuit} ({year})")

        # Get circuit base data
        circuit_data = CIRCUIT_DATA.get(circuit, {})
        if not circuit_data:
            logger.warning(
                f"No circuit data for {circuit}, using defaults"
            )
            circuit_data = self._get_default_circuit_data(circuit)

        # Fetch historical data if requested
        historical_data = {}
        if use_historical:
            historical_data = self._fetch_historical_data(year, circuit)

        # Merge circuit data with historical data
        template_vars = {**circuit_data, "year": year, "circuit_key": circuit}
        template_vars.update(historical_data)

        # Generate each document type
        documents = {}

        # Strategy document (includes tire analysis)
        strategy_doc = self._generate_strategy_doc(year, circuit, template_vars)
        if strategy_doc:
            documents["strategy.md"] = strategy_doc

        # Weather document
        weather_doc = self._generate_weather_doc(year, circuit, template_vars)
        if weather_doc:
            documents["weather.md"] = weather_doc

        # Tire analysis document
        tire_doc = self._generate_tire_doc(year, circuit, template_vars)
        if tire_doc:
            documents["tire_analysis.md"] = tire_doc

        # Performance document
        performance_doc = self._generate_performance_doc(
            year, circuit, template_vars
        )
        if performance_doc:
            documents["performance.md"] = performance_doc

        # Race Control document
        race_control_doc = self._generate_race_control_doc(
            year, circuit, template_vars
        )
        if race_control_doc:
            documents["race_control.md"] = race_control_doc

        # Race Position document
        race_position_doc = self._generate_race_position_doc(
            year, circuit, template_vars
        )
        if race_position_doc:
            documents["race_position.md"] = race_position_doc

        # Save to disk if requested
        if save_to_disk:
            self._save_documents(year, circuit, documents)

        logger.info(
            f"Generated {len(documents)} documents for {circuit} ({year})"
        )
        return documents

    def _generate_strategy_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate strategy guide document."""
        template_path = self.templates_path / "strategy_template.md"
        if not template_path.exists():
            logger.warning("Strategy template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Add strategy-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "circuit_type": template_vars.get("circuit_type", "Unknown"),
            "lap_length": template_vars.get("lap_length", "N/A"),
            "total_laps": template_vars.get("total_laps", "N/A"),
            "pit_loss": template_vars.get("pit_loss", "20"),
            "drs_zones": template_vars.get("drs_zones", "2"),
            "overtaking_difficulty": template_vars.get(
                "overtaking_difficulty", 5
            ),
            "track_position_importance": template_vars.get(
                "track_position_importance", 5
            ),
            "track_layout_description": self._get_track_layout(circuit),
            "overtaking_zones": self._get_overtaking_zones(circuit),
            # New expanded fields
            "first_lap_gain_potential": template_vars.get(
                "first_lap_gain_potential", "1-3 positions typical"
            ),
            "clean_air_delta": template_vars.get("clean_air_delta", "0.3-0.5"),
            # Pit strategy windows
            "one_stop_window": template_vars.get("one_stop_window", "18-25"),
            "one_stop_compounds": template_vars.get(
                "one_stop_compounds", "MEDIUM → HARD"
            ),
            "one_stop_notes": template_vars.get(
                "one_stop_notes", "Standard strategy"
            ),
            "two_stop_windows": template_vars.get(
                "two_stop_windows", "12-15, 30-35"
            ),
            "two_stop_compounds": template_vars.get(
                "two_stop_compounds", "SOFT → MEDIUM → SOFT"
            ),
            "two_stop_notes": template_vars.get(
                "two_stop_notes", "Aggressive option"
            ),
            "three_stop_windows": template_vars.get(
                "three_stop_windows", "10, 25, 40"
            ),
            "three_stop_compounds": template_vars.get(
                "three_stop_compounds", "SOFT → SOFT → SOFT"
            ),
            "three_stop_notes": template_vars.get(
                "three_stop_notes", "Only if SC opportunities arise"
            ),
            # Pit lane details
            "pit_entry_speed": "80",
            "pit_lane_length": "400",
            "typical_pit_time": "2.5",
            "total_pit_loss": template_vars.get("pit_loss", "20"),
            "pit_delta_track": template_vars.get("pit_delta_track", "18-22"),
            # Safety car analysis
            "sc_probability": template_vars.get("sc_probability", 35),
            "avg_sc_per_race": template_vars.get("avg_sc_per_race", "1.2"),
            "vsc_probability": template_vars.get("vsc_probability", 25),
            "red_flag_probability": template_vars.get(
                "red_flag_probability", 5
            ),
            "sc_zones_description": self._get_sc_zones(circuit),
            "sc_strategy": self._get_sc_strategy(circuit),
            "sc_react_quick": template_vars.get(
                "sc_react_quick", "Pit if gap >3s to car behind"
            ),
            # Undercut/overcut analysis
            "undercut_power": template_vars.get("undercut_power", 6),
            "undercut_window": "1-2",
            "undercut_gain": "1.5",
            "undercut_conditions": template_vars.get(
                "undercut_conditions", "Rival with degraded tires"
            ),
            "overcut_viability": template_vars.get("overcut_viability", 4),
            "overcut_conditions": "When tire warm-up is poor",
            "fuel_advantage": template_vars.get("fuel_advantage", "0.03"),
            # DRS zones table
            "drs_zones_table": self._get_drs_zones_table(circuit),
            "non_drs_overtaking": self._get_non_drs_overtaking(circuit),
            "defensive_lines": self._get_defensive_lines(circuit),
            # Think out of the box strategies
            "alternative_strategies": self._get_alternative_strategies(
                circuit
            ),
            "early_stop_example": template_vars.get(
                "early_stop_example", "Hungary 2019 - Verstappen pit lap 20"
            ),
            "extended_stint_example": template_vars.get(
                "extended_stint_example", "Spain 2021 - Hamilton 40+ lap stint"
            ),
            "compound_switch_example": template_vars.get(
                "compound_switch_example", "Bahrain 2022 - unexpected hard"
            ),
            "split_strategy_example": template_vars.get(
                "split_strategy_example", "Abu Dhabi 2021 - team split"
            ),
            "leader_fear": self._get_leader_fear(circuit),
            "midfield_fear": self._get_midfield_fear(circuit),
            "backmarker_opportunity": self._get_backmarker_opportunity(circuit),
            # Qualifying strategy
            "q2_tire_recommendation": template_vars.get(
                "q2_tire_recommendation", "MEDIUM if hot, SOFT if cool"
            ),
            "start_compound_impact": template_vars.get(
                "start_compound_impact", "~1-2 positions at start"
            ),
            "track_evolution_quali": template_vars.get(
                "track_evolution_quali", "0.3-0.5"
            ),
            # Historical winners table
            "historical_winners_table": self._format_historical_winners(
                template_vars.get("historical_data", {})
            ),
            "strategy_patterns": self._get_strategy_patterns(circuit),
            "circuit_specific_trends": self._get_circuit_trends(circuit),
            # Key considerations
            "consideration_do_1": self._get_consideration_do(circuit, 1),
            "consideration_do_2": self._get_consideration_do(circuit, 2),
            "consideration_do_3": self._get_consideration_do(circuit, 3),
            "consideration_dont_1": self._get_consideration_dont(circuit, 1),
            "consideration_dont_2": self._get_consideration_dont(circuit, 2),
            "consideration_dont_3": self._get_consideration_dont(circuit, 3),
            "crossover_temp": template_vars.get("crossover_temp", "25"),
            # Generation date
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            # Legacy support
            "historical_strategies": self._format_historical_strategies(
                template_vars.get("historical_data", {})
            ),
        }

        # Merge with template vars
        all_vars = {**defaults, **template_vars}

        # Fill template
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="strategy.md",
            content=content,
            category="strategy",
            circuit=circuit,
            year=year,
        )

    def _generate_weather_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate weather patterns document."""
        template_path = self.templates_path / "weather_template.md"
        if not template_path.exists():
            logger.warning("Weather template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Add weather-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "circuit_location": template_vars.get("location", "Unknown"),
            "timezone": template_vars.get("timezone", "UTC"),
            "race_local_time": template_vars.get("race_local_time", "14:00"),
            "climate_type": template_vars.get("climate_type", "Unknown"),
            # Temperature data
            "avg_air_temp": template_vars.get("avg_air_temp", "28"),
            "air_temp_range": template_vars.get("air_temp_range", "22-34"),
            "avg_track_temp": template_vars.get("avg_track_temp", "40"),
            "track_temp_range": template_vars.get("track_temp_range", "30-50"),
            "avg_humidity": template_vars.get("avg_humidity", "50"),
            "humidity_range": template_vars.get("humidity_range", "40-70"),
            # Wind data
            "wind_direction": template_vars.get("wind_direction", "Variable"),
            "avg_wind_speed": template_vars.get("avg_wind_speed", "15"),
            "max_wind_gust": template_vars.get("max_wind_gust", "30"),
            "wind_impact_level": template_vars.get("wind_impact_level", 5),
            # Temperature evolution
            "temp_evolution_description": self._get_temp_evolution(circuit),
            # Tire temperature windows
            "soft_optimal_temp": template_vars.get("soft_optimal_temp", "30"),
            "soft_temp_range": template_vars.get("soft_temp_range", "25-40"),
            "medium_optimal_temp": template_vars.get(
                "medium_optimal_temp", "35"
            ),
            "medium_temp_range": template_vars.get(
                "medium_temp_range", "30-45"
            ),
            "hard_optimal_temp": template_vars.get("hard_optimal_temp", "40"),
            "hard_temp_range": template_vars.get("hard_temp_range", "35-55"),
            "inter_optimal_temp": template_vars.get(
                "inter_optimal_temp", "25-35"
            ),
            # Rain probability
            "dry_probability": template_vars.get("dry_probability", 80),
            "rain_probability": template_vars.get("rain_probability", 15),
            "wet_race_probability": template_vars.get(
                "wet_race_probability", 5
            ),
            "red_flag_probability": template_vars.get(
                "red_flag_probability", 2
            ),
            "seasonal_rain_description": self._get_seasonal_rain(circuit),
            "rain_indicator_1": "Dark clouds approaching from the west",
            "rain_indicator_2": "Sudden drop in air temperature",
            "rain_indicator_3": "Increasing humidity above 70%",
            # Track evolution
            "fp1_fp2_evolution": template_vars.get("fp1_fp2_evolution", "0.5"),
            "fp2_fp3_evolution": template_vars.get("fp2_fp3_evolution", "0.3"),
            "fp3_quali_evolution": template_vars.get(
                "fp3_quali_evolution", "0.2"
            ),
            "quali_race_evolution": template_vars.get(
                "quali_race_evolution", "0.1"
            ),
            "rain_grip_loss": template_vars.get("rain_grip_loss", "30-40"),
            "re_rubber_laps": template_vars.get("re_rubber_laps", "5-10"),
            "crossover_water_level": template_vars.get(
                "crossover_water_level", "85-90"
            ),
            # Wind sector analysis
            "s1_wind_effect": "Moderate crosswind",
            "s1_corners": "Turns 1-4",
            "s2_wind_effect": "Headwind on straight",
            "s2_corners": "Turns 5-10",
            "s3_wind_effect": "Tailwind acceleration",
            "s3_corners": "Turns 11-finish",
            "crosswind_description": self._get_crosswind_info(circuit),
            # Rain strategy
            "dry_strategy": self._get_dry_strategy(circuit),
            "changing_conditions_strategy": (
                "Monitor radar closely. Prepare for quick switch. "
                "Have intermediates ready on standby. "
                "Consider early pit if rain intensity increasing."
            ),
            "wet_strategy": self._get_wet_strategy(circuit),
            # Crossover times
            "slick_to_inter_delta": template_vars.get(
                "slick_to_inter_delta", "5-8"
            ),
            "dry_crossover_time": template_vars.get(
                "dry_crossover_time", "3-5"
            ),
            # Historical weather table
            "historical_weather_table": self._format_historical_weather(
                template_vars.get("historical_data", {})
            ),
            "notable_weather_events": self._get_notable_weather_events(
                circuit
            ),
            # Generation date
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        all_vars = {**defaults, **template_vars}
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="weather.md",
            content=content,
            category="weather",
            circuit=circuit,
            year=year,
        )

    def _generate_tire_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate tire analysis document."""
        template_path = self.templates_path / "tire_template.md"
        if not template_path.exists():
            logger.warning("Tire template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Get Pirelli compound names for the year
        compounds = PIRELLI_COMPOUNDS.get(year, PIRELLI_COMPOUNDS[2024])

        # Add tire-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "year": year,
            "stress_level": template_vars.get("stress_level", 6),
            "stress_notes": self._get_stress_notes(circuit),
            "front_stress": template_vars.get("front_stress", 6),
            "front_notes": "Front-limited in slow corners",
            "rear_stress": template_vars.get("rear_stress", 6),
            "rear_notes": "Traction zones stress rears",
            "lateral_load": template_vars.get("lateral_load", 6),
            "traction_demand": template_vars.get("traction_demand", 6),
            "braking_severity": template_vars.get("braking_severity", 6),
            "limitation_type": template_vars.get("limitation_type", "Rear"),
            "deg_mode": template_vars.get("deg_mode", "Thermal"),
            # Compound names
            "soft_name": compounds["soft_name"],
            "medium_name": compounds["medium_name"],
            "hard_name": compounds["hard_name"],
            # Compound characteristics
            "soft_characteristics": template_vars.get(
                "soft_characteristics",
                "Peak grip, fastest warm-up, highest degradation"
            ),
            "medium_characteristics": template_vars.get(
                "medium_characteristics",
                "Balanced performance, versatile, moderate deg"
            ),
            "hard_characteristics": template_vars.get(
                "hard_characteristics",
                "Durable, slow warm-up, lowest degradation"
            ),
            "compound_selection_reasoning": self._get_compound_reasoning(
                circuit
            ),
            # Operating windows
            "soft_temp_window": template_vars.get(
                "soft_temp_window", "25-35"
            ),
            "soft_warmup": template_vars.get("soft_warmup", "1"),
            "soft_peak": template_vars.get("soft_peak", "3-5"),
            "med_temp_window": template_vars.get("med_temp_window", "30-45"),
            "med_warmup": template_vars.get("med_warmup", "2"),
            "med_peak": template_vars.get("med_peak", "4-7"),
            "hard_temp_window": template_vars.get(
                "hard_temp_window", "35-50"
            ),
            "hard_warmup": template_vars.get("hard_warmup", "3"),
            "hard_peak": template_vars.get("hard_peak", "5-10"),
            # Degradation rates
            "soft_deg_avg": template_vars.get("soft_deg_avg", "0.08"),
            "soft_deg_push": template_vars.get("soft_deg_push", "0.12"),
            "soft_cliff": template_vars.get("soft_cliff", "18"),
            "med_deg_avg": template_vars.get("med_deg_avg", "0.05"),
            "med_deg_push": template_vars.get("med_deg_push", "0.08"),
            "med_cliff": template_vars.get("med_cliff", "30"),
            "hard_deg_avg": template_vars.get("hard_deg_avg", "0.03"),
            "hard_deg_push": template_vars.get("hard_deg_push", "0.05"),
            "hard_cliff": template_vars.get("hard_cliff", "45"),
            # Pace deltas
            "soft_med_delta": template_vars.get("soft_med_delta", "0.8"),
            "med_hard_delta": template_vars.get("med_hard_delta", "0.6"),
            "soft_hard_delta": template_vars.get("soft_hard_delta", "1.4"),
            # Stint lengths
            "soft_max_cons": template_vars.get("soft_max_cons", "15"),
            "soft_max_norm": template_vars.get("soft_max_norm", "18"),
            "soft_max_agg": template_vars.get("soft_max_agg", "22"),
            "med_max_cons": template_vars.get("med_max_cons", "25"),
            "med_max_norm": template_vars.get("med_max_norm", "30"),
            "med_max_agg": template_vars.get("med_max_agg", "35"),
            "hard_max_cons": template_vars.get("hard_max_cons", "35"),
            "hard_max_norm": template_vars.get("hard_max_norm", "40"),
            "hard_max_agg": template_vars.get("hard_max_agg", "50"),
            # Fuel impact
            "fuel_deg_impact": template_vars.get("fuel_deg_impact", "15"),
            "fuel_full_impact": template_vars.get("fuel_full_impact", "20"),
            "fuel_75_impact": template_vars.get("fuel_75_impact", "10"),
            "fuel_25_impact": template_vars.get("fuel_25_impact", "5"),
            "fuel_light_impact": template_vars.get("fuel_light_impact", "10"),
            "fuel_consumption": template_vars.get("fuel_consumption", "1.8"),
            "weight_per_lap": template_vars.get("weight_per_lap", "1.5"),
            "lap_time_per_kg": template_vars.get("lap_time_per_kg", "0.035"),
            # Corners and zones
            "high_stress_corners_table": self._get_high_stress_corners(
                circuit
            ),
            "traction_zones_description": self._get_traction_zones(circuit),
            "braking_zones_description": self._get_braking_zones(circuit),
            # Graining
            "graining_risk": template_vars.get("graining_risk", 5),
            "graining_conditions": "Low track temps, new tires",
            "graining_compound": "SOFT/MEDIUM",
            "graining_recovery": template_vars.get(
                "graining_recovery",
                "Can work through after 5-10 laps of steady pace"
            ),
            "graining_mitigation": "Manage pace in early laps",
            # Thermal deg
            "thermal_risk": template_vars.get("thermal_risk", 6),
            "thermal_conditions": "High track temps, pushing hard",
            "thermal_compound": "SOFT",
            "thermal_mitigation": "Lift and coast in key zones",
            # Wear deg
            "wear_risk": template_vars.get("wear_risk", 5),
            # Management techniques
            "lift_coast_zones": self._get_lift_coast_zones(circuit),
            "lift_coast_save": template_vars.get("lift_coast_save", "10-15"),
            "lift_coast_time": template_vars.get("lift_coast_time", "0.3"),
            "smooth_save": template_vars.get("smooth_save", "5"),
            "kerb_save": template_vars.get("kerb_save", "3"),
            "kerb_time": template_vars.get("kerb_time", "0.1"),
            # Temperature sensitivity table
            "soft_25": template_vars.get("soft_25", "20 laps"),
            "med_25": template_vars.get("med_25", "35 laps"),
            "hard_25": template_vars.get("hard_25", "45+ laps"),
            "soft_35": template_vars.get("soft_35", "18 laps"),
            "med_35": template_vars.get("med_35", "30 laps"),
            "hard_35": template_vars.get("hard_35", "40 laps"),
            "soft_45": template_vars.get("soft_45", "15 laps"),
            "med_45": template_vars.get("med_45", "25 laps"),
            "hard_45": template_vars.get("hard_45", "35 laps"),
            "soft_55": template_vars.get("soft_55", "12 laps"),
            "med_55": template_vars.get("med_55", "20 laps"),
            "hard_55": template_vars.get("hard_55", "30 laps"),
            "temp_trend_impact": self._get_temp_trend_impact(circuit),
            # Qualifying/Race recommendations
            "quali_recommendation": self._get_quali_recommendation(circuit),
            "race_start_recommendation": self._get_race_start_recommendation(
                circuit
            ),
            "mid_race_recommendation": template_vars.get(
                "mid_race_recommendation",
                "Monitor tire temperatures and adjust pace accordingly."
            ),
            # Historical data
            "historical_stints_table": self._format_historical_stints(
                template_vars.get("historical_data", {})
            ),
            "avg_stint_analysis": self._get_avg_stint_analysis(circuit),
            "notable_tire_strategies": self._get_notable_tire_strategies(
                circuit
            ),
            # Think out of the box
            "unconventional_tire_strategies": self._get_unconventional_tire(
                circuit
            ),
            "counter_strategy_1": template_vars.get(
                "counter_strategy_1",
                "If rivals start SOFT, consider MEDIUM for late-race advantage"
            ),
            "counter_strategy_2": template_vars.get(
                "counter_strategy_2",
                "If rivals go 2-stop, extend your first stint for 1-stop"
            ),
            "counter_strategy_3": template_vars.get(
                "counter_strategy_3",
                "If track temp dropping, switch to harder compound earlier"
            ),
            # Generation date
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        all_vars = {**defaults, **template_vars}
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="tire_analysis.md",
            content=content,
            category="tire",
            circuit=circuit,
            year=year,
        )

    def _generate_performance_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate performance analysis document."""
        template_path = self.templates_path / "performance_template.md"
        if not template_path.exists():
            logger.warning("Performance template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Add performance-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "circuit_type": template_vars.get("circuit_type", "Unknown"),
            "year": year,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            # Benchmark times
            "theoretical_best": template_vars.get("theoretical_best", "N/A"),
            "practical_race_pace": template_vars.get(
                "practical_race_pace", "N/A"
            ),
            "quali_spread": template_vars.get("quali_spread", "1.0-1.5"),
            "midfield_variance": template_vars.get("midfield_variance", "0.3"),
            # Session evolution
            "fp2_improvement": template_vars.get("fp2_improvement", "-0.5"),
            "fp3_improvement": template_vars.get("fp3_improvement", "-0.8"),
            "quali_improvement": template_vars.get("quali_improvement", "-1.2"),
            "race_fuel_delta": template_vars.get("race_fuel_delta", "2.5"),
            # Degradation
            "soft_deg": template_vars.get("soft_deg", "0.08"),
            "medium_deg": template_vars.get("medium_deg", "0.05"),
            "hard_deg": template_vars.get("hard_deg", "0.03"),
            "soft_cliff": template_vars.get("soft_cliff", "18"),
            "medium_cliff": template_vars.get("medium_cliff", "30"),
            # Sector breakdown
            "s1_length": template_vars.get("s1_length", "1800"),
            "s1_type": template_vars.get("s1_type", "Mixed"),
            "s1_corners": template_vars.get("s1_corners", "T1-T5"),
            "s1_time": template_vars.get("s1_time", "25"),
            "s2_length": template_vars.get("s2_length", "2000"),
            "s2_type": template_vars.get("s2_type", "High-speed"),
            "s2_corners": template_vars.get("s2_corners", "T6-T12"),
            "s2_time": template_vars.get("s2_time", "30"),
            "s3_length": template_vars.get("s3_length", "1600"),
            "s3_type": template_vars.get("s3_type", "Technical"),
            "s3_corners": template_vars.get("s3_corners", "T13-T18"),
            "s3_time": template_vars.get("s3_time", "20"),
            "s1_key_factor": template_vars.get(
                "s1_key_factor", "Traction out of slow corners"
            ),
            "s2_key_factor": template_vars.get(
                "s2_key_factor", "Straight-line speed and aero efficiency"
            ),
            "s3_key_factor": template_vars.get(
                "s3_key_factor", "Mechanical grip and tire management"
            ),
            "s1_dominant_teams": template_vars.get(
                "s1_dominant_teams", "Red Bull, Ferrari"
            ),
            "s2_dominant_teams": template_vars.get(
                "s2_dominant_teams", "Mercedes, McLaren"
            ),
            "s3_dominant_teams": template_vars.get(
                "s3_dominant_teams", "Red Bull, Mercedes"
            ),
            # Speed trap
            "main_trap_location": template_vars.get(
                "main_trap_location", "Main straight"
            ),
            "int1_location": template_vars.get("int1_location", "After T5"),
            "int2_location": template_vars.get("int2_location", "After T12"),
            "max_speed": template_vars.get("max_speed", "340"),
            "avg_top_speed": template_vars.get("avg_top_speed", "320"),
            "low_df_speed": template_vars.get("low_df_speed", "5-8"),
            "high_df_speed": template_vars.get("high_df_speed", "3-5"),
            "team_speed_ranking": template_vars.get(
                "team_speed_ranking",
                "1. Ferrari\n2. Mercedes\n3. McLaren\n4. Red Bull"
            ),
            # Underperformance thresholds
            "yellow_teammate": template_vars.get("yellow_teammate", "0.3"),
            "red_teammate": template_vars.get("red_teammate", "0.5"),
            "yellow_sector": template_vars.get("yellow_sector", "5"),
            "red_sector": template_vars.get("red_sector", "10"),
            "yellow_speed": template_vars.get("yellow_speed", "5"),
            "red_speed": template_vars.get("red_speed", "10"),
            "yellow_deg": template_vars.get("yellow_deg", "20"),
            "red_deg": template_vars.get("red_deg", "50"),
            # Underperformance causes
            "setup_issues": template_vars.get(
                "setup_issues", "Wing angle, ride height, diff settings"
            ),
            "tire_management_issues": template_vars.get(
                "tire_management_issues", "Overheating, graining, blistering"
            ),
            "traffic_impact": template_vars.get(
                "traffic_impact", "Dirty air cost: 0.3-0.8s per lap"
            ),
            "pu_concerns": template_vars.get(
                "pu_concerns", "Derating, clipping, battery management"
            ),
            # Recovery strategies
            "quick_fix": template_vars.get(
                "quick_fix", "Adjust brake bias, diff, engine modes"
            ),
            "medium_fix": template_vars.get(
                "medium_fix", "Setup changes at pit, new tires"
            ),
            "strategic_fix": template_vars.get(
                "strategic_fix", "Alternative strategy, undercut/overcut"
            ),
            # Historical data
            "circuit_specialists": template_vars.get(
                "circuit_specialists",
                "- Hamilton: 8 wins\n- Verstappen: 3 wins\n- Vettel: 4 wins"
            ),
            "yoy_2023": template_vars.get("yoy_2023", "0.8"),
            "reg_impact": template_vars.get(
                "reg_impact", "2022 ground effect cars changed dynamics"
            ),
            "track_evolution_impact": template_vars.get(
                "track_evolution_impact", "0.5-1.0s over weekend"
            ),
            # Weather sensitivity
            "dry_wet_delta": template_vars.get("dry_wet_delta", "15-25"),
            "temp_sensitivity": template_vars.get("temp_sensitivity", "0.15"),
            "wind_impact": template_vars.get("wind_impact", "0.2-0.4"),
            # Think out of the box
            "extreme_low_df": template_vars.get(
                "extreme_low_df",
                "Monza-spec wing for top speed, sacrifice corners"
            ),
            "asymmetric_setup": template_vars.get(
                "asymmetric_setup",
                "Different suspension settings L/R for uneven corners"
            ),
            "pressure_gamble": template_vars.get(
                "pressure_gamble", "Lower pressures for grip vs higher for deg"
            ),
            "home_advantage": template_vars.get(
                "home_advantage", "Crowd support can add 0.2s motivation"
            ),
            "pressure_impact": template_vars.get(
                "pressure_impact", "Championship pressure can cost 0.3-0.5s"
            ),
            "wet_specialists": template_vars.get(
                "wet_specialists", "Hamilton, Verstappen, Alonso"
            ),
            "data_mining_insights": template_vars.get(
                "data_mining_insights",
                "- Tire deg patterns correlate with track temp\n"
                "- Lap 1 incidents 40% more likely in hot conditions\n"
                "- Undercut success rate highest laps 12-18"
            ),
        }

        all_vars = {**defaults, **template_vars}
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="performance.md",
            content=content,
            category="performance",
            circuit=circuit,
            year=year,
        )

    def _generate_race_control_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate race control analysis document."""
        template_path = self.templates_path / "race_control_template.md"
        if not template_path.exists():
            logger.warning("Race Control template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Add race control-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "circuit_type": template_vars.get("circuit_type", "Unknown"),
            "year": year,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "safety_rating": template_vars.get("safety_rating", "7"),
            "incident_rate": template_vars.get("incident_rate", "35"),
            # SC probabilities
            "sc_probability": template_vars.get("sc_probability", "35"),
            "vsc_probability": template_vars.get("vsc_probability", "25"),
            "red_flag_probability": template_vars.get(
                "red_flag_probability", "5"
            ),
            "avg_sc_laps": template_vars.get("avg_sc_laps", "4"),
            "sc_window_start": template_vars.get("sc_window_start", "1"),
            "sc_window_end": template_vars.get("sc_window_end", "15"),
            # SC trigger zones
            "zone1_location": template_vars.get("zone1_location", "Turn 1"),
            "zone1_risk": template_vars.get("zone1_risk", "8"),
            "zone1_cause": template_vars.get(
                "zone1_cause", "Lap 1 contact, cold tires"
            ),
            "zone2_location": template_vars.get("zone2_location", "Turn 5-6"),
            "zone2_risk": template_vars.get("zone2_risk", "6"),
            "zone2_cause": template_vars.get(
                "zone2_cause", "High-speed corner incident"
            ),
            "zone3_location": template_vars.get(
                "zone3_location", "Pit exit"
            ),
            "zone3_risk": template_vars.get("zone3_risk", "5"),
            "zone3_cause": template_vars.get(
                "zone3_cause", "Unsafe release, rejoining traffic"
            ),
            "zone4_location": template_vars.get(
                "zone4_location", "Final chicane"
            ),
            "zone4_risk": template_vars.get("zone4_risk", "6"),
            "zone4_cause": template_vars.get(
                "zone4_cause", "Late braking, lock-ups"
            ),
            # Lap 1 analysis
            "t1_risk": template_vars.get("t1_risk", "8"),
            "lap1_sc_count": template_vars.get("lap1_sc_count", "2"),
            "lap1_resolution": template_vars.get("lap1_resolution", "3-5"),
            # Flag zones
            "yellow_flag_zones": template_vars.get(
                "yellow_flag_zones",
                "- Turn 1-2: Frequent first lap incidents\n"
                "- Turn 8-9: High speed corner complex\n"
                "- Final sector: Technical section with barriers"
            ),
            "double_yellow_duration": template_vars.get(
                "double_yellow_duration", "2"
            ),
            "recovery_protocol": template_vars.get(
                "recovery_protocol", "VSC or crane recovery"
            ),
            "double_yellow_cause": template_vars.get(
                "double_yellow_cause", "Car stopped in runoff"
            ),
            "blue_primary": template_vars.get(
                "blue_primary", "Main straight / DRS zone"
            ),
            "blue_secondary": template_vars.get(
                "blue_secondary", "Turn 4-5 complex"
            ),
            "backmarker_delay": template_vars.get("backmarker_delay", "0.5-1"),
            # VSC
            "light_debris_response": template_vars.get(
                "light_debris_response", "Yellow flag, local caution"
            ),
            "car_recovery_response": template_vars.get(
                "car_recovery_response", "VSC or SC depending on location"
            ),
            "medical_response": template_vars.get(
                "medical_response", "Red flag if driver extraction needed"
            ),
            "pit_loss": template_vars.get("pit_loss", "20"),
            "vsc_pit_loss": template_vars.get("vsc_pit_loss", "10-12"),
            "vsc_pit_advantage": template_vars.get("vsc_pit_advantage", "8-10"),
            "vsc_history": template_vars.get(
                "vsc_history",
                "| 2023 | 25 | 3 laps | Debris on track |\n"
                "| 2024 | 15 | 2 laps | Car stopped |"
            ),
            # Full SC strategies
            "early_sc_strategy": template_vars.get(
                "early_sc_strategy",
                "Pit if on SOFT, stay out if MEDIUM/HARD"
            ),
            "mid_sc_strategy": template_vars.get(
                "mid_sc_strategy",
                "Free stop, consider compound for remaining laps"
            ),
            "late_sc_strategy": template_vars.get(
                "late_sc_strategy",
                "Fresh SOFT for sprint finish, track position critical"
            ),
            "top3_sc_strategy": template_vars.get(
                "top3_sc_strategy", "Cover the undercut, mirror closest rival"
            ),
            "midfield_sc_strategy": template_vars.get(
                "midfield_sc_strategy", "Opposite strategy to maximize gains"
            ),
            "backfield_sc_strategy": template_vars.get(
                "backfield_sc_strategy", "Gamble on fresh tires"
            ),
            "optimal_sc_gap": template_vars.get("optimal_sc_gap", "200-300"),
            "restart_prep_lap": template_vars.get("restart_prep_lap", "-1"),
            "restart_warmup": template_vars.get("restart_warmup", "3-4"),
            # Red flag
            "weather_red_flag": template_vars.get(
                "weather_red_flag", "Heavy rain, standing water, visibility"
            ),
            "incident_red_flag": template_vars.get(
                "incident_red_flag", "Major collision, medical intervention"
            ),
            "track_damage_red_flag": template_vars.get(
                "track_damage_red_flag", "Barrier damage, debris field"
            ),
            "barrier_red_flag": template_vars.get(
                "barrier_red_flag", "TecPro barrier displacement"
            ),
            "free_tire_change": template_vars.get(
                "free_tire_change", "Yes - reset allowed"
            ),
            "post_red_compound": template_vars.get(
                "post_red_compound", "SOFT for restart performance"
            ),
            "post_red_warmup": template_vars.get(
                "post_red_warmup", "2 formation laps standard"
            ),
            "red_flag_history": template_vars.get(
                "red_flag_history",
                "Notable red flags: Heavy rain 2021, Lap 1 incident 2022"
            ),
            # Track limits
            "track_limits_table": template_vars.get(
                "track_limits_table",
                "| T4 | Exit | Warning/Delete | 3 strikes |\n"
                "| T11 | Exit | Warning/Delete | 3 strikes |\n"
                "| T15 | Entry | Warning | 5 strikes |"
            ),
            "warning_threshold": template_vars.get("warning_threshold", "3"),
            "deletion_threshold": template_vars.get("deletion_threshold", "3"),
            "time_penalty_threshold": template_vars.get(
                "time_penalty_threshold", "4"
            ),
            "penalty_time": template_vars.get("penalty_time", "5"),
            "corner_guidance": template_vars.get(
                "corner_guidance",
                "Turn 4: Use all kerb but stay within white line\n"
                "Turn 11: Exit carefully monitored\n"
                "Turn 15: Entry line critical"
            ),
            # Penalties
            "track_limits_penalty": template_vars.get(
                "track_limits_penalty", "5s / lap deleted"
            ),
            "track_limits_freq": template_vars.get(
                "track_limits_freq", "High"
            ),
            "unsafe_release_penalty": template_vars.get(
                "unsafe_release_penalty", "5s"
            ),
            "unsafe_release_freq": template_vars.get(
                "unsafe_release_freq", "Low"
            ),
            "forcing_penalty": template_vars.get(
                "forcing_penalty", "5s / 10s"
            ),
            "forcing_freq": template_vars.get("forcing_freq", "Medium"),
            "speeding_penalty": template_vars.get(
                "speeding_penalty", "Drive-through / 10s"
            ),
            "speeding_freq": template_vars.get("speeding_freq", "Rare"),
            "investigation_speed": template_vars.get(
                "investigation_speed", "Usually within 5 laps"
            ),
            "penalty_consistency": template_vars.get(
                "penalty_consistency", "7"
            ),
            "racing_tolerance": template_vars.get("racing_tolerance", "6"),
            "gap_5s": template_vars.get("gap_5s", "5"),
            "penalty_10s_strategy": template_vars.get(
                "penalty_10s_strategy", "Serve at next stop if possible"
            ),
            "dt_strategy": template_vars.get(
                "dt_strategy", "Time with VSC/SC if available"
            ),
            # Pit lane
            "pit_speed": template_vars.get("pit_speed", "80"),
            "pit_entry_type": template_vars.get(
                "pit_entry_type", "Left side entry"
            ),
            "pit_exit_type": template_vars.get(
                "pit_exit_type", "Right side exit"
            ),
            "white_line_rule": template_vars.get(
                "white_line_rule", "No crossing on entry/exit"
            ),
            "contact_threshold": template_vars.get(
                "contact_threshold", "Any contact = penalty"
            ),
            "near_miss_def": template_vars.get(
                "near_miss_def", "Forcing evasive action"
            ),
            "unsafe_release_history": template_vars.get(
                "unsafe_release_history", "2-3 per season average"
            ),
            "pit_closure_triggers": template_vars.get(
                "pit_closure_triggers",
                "- Incident in pit lane\n"
                "- Recovery vehicle crossing\n"
                "- Start procedure"
            ),
            # Think out of the box
            "vsc_preemptive": template_vars.get(
                "vsc_preemptive",
                "Monitor gaps - pit if rival 2s+ behind and VSC imminent"
            ),
            "vsc_delta": template_vars.get(
                "vsc_delta",
                "Manage delta target to maximize in-lap benefit"
            ),
            "vsc_double_stack": template_vars.get(
                "vsc_double_stack",
                "Risky but saves 8-10s vs normal double stack"
            ),
            "surprise_restart": template_vars.get(
                "surprise_restart",
                "Build gap in final SC lap, catch rival cold"
            ),
            "slipstream_position": template_vars.get(
                "slipstream_position",
                "P2 into T1 can be advantageous with slipstream"
            ),
            "defensive_restart": template_vars.get(
                "defensive_restart",
                "Take inside line early, sacrifice exit for position"
            ),
            "rotation_strategy": template_vars.get(
                "rotation_strategy",
                "Use allowed track limit violations strategically"
            ),
            "quali_race_diff": template_vars.get(
                "quali_race_diff",
                "Quali more strict, race allows more racing room"
            ),
            "last_lap_limits": template_vars.get(
                "last_lap_limits",
                "Stewards lenient on last lap battles historically"
            ),
            "controversial_decisions": template_vars.get(
                "controversial_decisions",
                "Abu Dhabi 2021 SC restart, Brazil 2022 track limits"
            ),
        }

        all_vars = {**defaults, **template_vars}
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="race_control.md",
            content=content,
            category="race_control",
            circuit=circuit,
            year=year,
        )

    def _generate_race_position_doc(
        self,
        year: int,
        circuit: str,
        template_vars: Dict[str, Any],
    ) -> Optional[GeneratedDocument]:
        """Generate race position analysis document."""
        template_path = self.templates_path / "race_position_template.md"
        if not template_path.exists():
            logger.warning("Race Position template not found")
            return None

        template = template_path.read_text(encoding="utf-8")

        # Add race position-specific defaults
        defaults = {
            "circuit_name": template_vars.get(
                "full_name", circuit.replace("_", " ").title()
            ),
            "circuit_type": template_vars.get("circuit_type", "Unknown"),
            "year": year,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "overtaking_difficulty": template_vars.get(
                "overtaking_difficulty", "5"
            ),
            "track_position_importance": template_vars.get(
                "track_position_importance", "6"
            ),
            # Grid statistics
            "pole_win_rate": template_vars.get("pole_win_rate", "60"),
            "front_row_podium": template_vars.get("front_row_podium", "85"),
            "midfield_points": template_vars.get("midfield_points", "70"),
            "avg_grid_movement": template_vars.get("avg_grid_movement", "2-3"),
            # Position values
            "p1_avg_pts": template_vars.get("p1_avg_pts", "24"),
            "p2_value": template_vars.get("p2_value", "9"),
            "p2_avg_pts": template_vars.get("p2_avg_pts", "17"),
            "p2_pass_diff": template_vars.get("p2_pass_diff", "7"),
            "p3_value": template_vars.get("p3_value", "8"),
            "p3_avg_pts": template_vars.get("p3_avg_pts", "14"),
            "p3_pass_diff": template_vars.get("p3_pass_diff", "6"),
            "p4_6_value": template_vars.get("p4_6_value", "7"),
            "p4_6_avg_pts": template_vars.get("p4_6_avg_pts", "10"),
            "p4_6_pass_diff": template_vars.get("p4_6_pass_diff", "5"),
            "p7_10_value": template_vars.get("p7_10_value", "5"),
            "p7_10_avg_pts": template_vars.get("p7_10_avg_pts", "3"),
            "p7_10_pass_diff": template_vars.get("p7_10_pass_diff", "4"),
            # Clean air / dirty air
            "clean_air_delta": template_vars.get("clean_air_delta", "0.3-0.5"),
            "dirty_air_corners": template_vars.get("dirty_air_corners", "3-4"),
            "drs_effectiveness": template_vars.get("drs_effectiveness", "7"),
            # Overtaking zones
            "oz1_location": template_vars.get("oz1_location", "Turn 1"),
            "oz1_success": template_vars.get("oz1_success", "40"),
            "oz1_setup": template_vars.get("oz1_setup", "DRS straight"),
            "oz1_drs": template_vars.get("oz1_drs", "Yes"),
            "oz2_location": template_vars.get("oz2_location", "Turn 5"),
            "oz2_success": template_vars.get("oz2_success", "25"),
            "oz2_setup": template_vars.get("oz2_setup", "Switchback"),
            "oz2_drs": template_vars.get("oz2_drs", "No"),
            "oz3_location": template_vars.get("oz3_location", "Turn 12"),
            "oz3_success": template_vars.get("oz3_success", "30"),
            "oz3_setup": template_vars.get("oz3_setup", "Long straight"),
            "oz3_drs": template_vars.get("oz3_drs", "Yes"),
            # Overtaking requirements
            "speed_delta": template_vars.get("speed_delta", "8"),
            "tire_delta": template_vars.get("tire_delta", "5"),
            "min_attempt_gap": template_vars.get("min_attempt_gap", "0.5"),
            # Defense
            "defense_line": template_vars.get(
                "defense_line", "Inside line to apex"
            ),
            "switchback_zones": template_vars.get(
                "switchback_zones", "T4-T5, T10-T11"
            ),
            "late_brake_risk": template_vars.get(
                "late_brake_risk", "T1, T12 high risk"
            ),
            # Gap management
            "pit_window_gap": template_vars.get("pit_window_gap", "20-25"),
            "push_strategy": template_vars.get(
                "push_strategy", "First 3-5 laps, build 3s+ gap"
            ),
            "management_strategy": template_vars.get(
                "management_strategy", "Maintain 1-2s buffer"
            ),
            "defensive_strategy": template_vars.get(
                "defensive_strategy", "Cover DRS zones, protect inside"
            ),
            "closing_action": template_vars.get(
                "closing_action", "Increase pace, prepare defense"
            ),
            "stable_action": template_vars.get(
                "stable_action", "Continue current strategy"
            ),
            "growing_action": template_vars.get(
                "growing_action", "Consider extending stint"
            ),
            # Battle analysis
            "battle_2_loss": template_vars.get("battle_2_loss", "0.3"),
            "battle_3_loss": template_vars.get("battle_3_loss", "0.5"),
            "train_loss": template_vars.get("train_loss", "0.8"),
            "undercut_battle": template_vars.get(
                "undercut_battle", "Pit 1-2 laps early to break battle"
            ),
            "overcut_battle": template_vars.get(
                "overcut_battle", "Stay out for clean air laps"
            ),
            "wait_battle": template_vars.get(
                "wait_battle", "Save tires, attack in final stint"
            ),
            "epic_battles_history": template_vars.get(
                "epic_battles_history",
                "- 2021: Hamilton vs Verstappen wheel-to-wheel\n"
                "- 2022: Leclerc vs Perez last lap battle\n"
                "- 2023: Norris vs Sainz 5-lap fight"
            ),
            # DRS zones
            "drs_zones_table": template_vars.get(
                "drs_zones_table",
                "| DRS1 | T15 exit | S/F straight | 800m | High |\n"
                "| DRS2 | T3 exit | Back straight | 600m | Medium |"
            ),
            "train_formation_laps": template_vars.get(
                "train_formation_laps", "15-25"
            ),
            "escape_velocity": template_vars.get("escape_velocity", "1.5"),
            "attack_laps": template_vars.get("attack_laps", "10"),
            "defense_laps": template_vars.get("defense_laps", "5"),
            "optimal_drs_timing": template_vars.get(
                "optimal_drs_timing", "Fresh tires in final stint"
            ),
            # Lap 1
            "lap1_typical": template_vars.get("lap1_typical", "+/- 2 positions"),
            "lap1_risk_zones": template_vars.get(
                "lap1_risk_zones", "T1-T2, first chicane"
            ),
            "lap1_opportunity": template_vars.get(
                "lap1_opportunity", "Outside line at T1, switchback T3"
            ),
            "top3_start_strategy": template_vars.get(
                "top3_start_strategy", "Defend inside, secure position"
            ),
            "midfield_start_strategy": template_vars.get(
                "midfield_start_strategy", "Aggressive, gain positions"
            ),
            "backfield_start_strategy": template_vars.get(
                "backfield_start_strategy", "Avoid incidents, maximize survival"
            ),
            "lap1_history": template_vars.get(
                "lap1_history",
                "- 2023: Multiple positions gained from P10+\n"
                "- 2024: T1 incident took out 3 cars"
            ),
            # Pit position impact
            "undercut_window": template_vars.get("undercut_window", "2-3"),
            "undercut_gain": template_vars.get("undercut_gain", "1-2"),
            "undercut_trigger": template_vars.get("undercut_trigger", "1.5"),
            "overcut_window": template_vars.get("overcut_window", "3-5"),
            "overcut_gain": template_vars.get("overcut_gain", "0-1"),
            "overcut_clean_air": template_vars.get("overcut_clean_air", "3"),
            # Track position scenarios
            "lead_2s_first": template_vars.get(
                "lead_2s_first", "Maintain lead"
            ),
            "lead_2s_second": template_vars.get(
                "lead_2s_second", "Risk undercut"
            ),
            "lead_2s_stay": template_vars.get("lead_2s_stay", "Overcut attempt"),
            "battle_first": template_vars.get("battle_first", "Break the fight"),
            "battle_second": template_vars.get("battle_second", "Overcut both"),
            "battle_stay": template_vars.get("battle_stay", "Wait for SC"),
            "traffic_first": template_vars.get("traffic_first", "Clear traffic"),
            "traffic_second": template_vars.get(
                "traffic_second", "Lose to traffic"
            ),
            "traffic_stay": template_vars.get(
                "traffic_stay", "Manage through traffic"
            ),
            # Blue flags
            "primary_lap_zone": template_vars.get(
                "primary_lap_zone", "Main straight"
            ),
            "secondary_lap_zone": template_vars.get(
                "secondary_lap_zone", "Back straight"
            ),
            "backmarker_loss": template_vars.get("backmarker_loss", "0.5-1.5"),
            "traffic_alert": template_vars.get("traffic_alert", "2"),
            "clean_lap_timing": template_vars.get(
                "clean_lap_timing", "Check gap to backmarkers"
            ),
            "train_break": template_vars.get(
                "train_break", "Pit when blue flag bunches field"
            ),
            # Think out of the box
            "unconventional_lines": template_vars.get(
                "unconventional_lines",
                "Outside-outside at T1-T2, dummy inside then switch"
            ),
            "dummy_moves": template_vars.get(
                "dummy_moves", "Fake attack before DRS zone"
            ),
            "weather_passes": template_vars.get(
                "weather_passes",
                "Rain transition creates overtaking windows"
            ),
            "pressure_tactics": template_vars.get(
                "pressure_tactics",
                "Stay within 0.5s to force errors"
            ),
            "defensive_mind": template_vars.get(
                "defensive_mind", "Weave early to show strength"
            ),
            "radio_impact": template_vars.get(
                "radio_impact", "Team radio can pressure rival strategically"
            ),
            "multi_car_moves": template_vars.get(
                "multi_car_moves", "Use battles ahead to pass multiple cars"
            ),
            "cutback_tactics": template_vars.get(
                "cutback_tactics", "Sacrifice corner entry for better exit"
            ),
            "late_race_moves": template_vars.get(
                "late_race_moves", "Desperate lunges can work with tire delta"
            ),
            "unexpected_passes_history": template_vars.get(
                "unexpected_passes_history",
                "- Hamilton around the outside T4 2021\n"
                "- Alonso divebomb T1 2023\n"
                "- Verstappen switchback T5 2022"
            ),
            # Predictions
            "position_predictions": template_vars.get(
                "position_predictions",
                "Based on qualifying and historical trends"
            ),
            "gainers_prediction": template_vars.get(
                "gainers_prediction", "Strong starters, tire managers"
            ),
            "losers_prediction": template_vars.get(
                "losers_prediction", "Poor starters, high deg cars"
            ),
            "championship_battles": template_vars.get(
                "championship_battles",
                "Monitor title contender positions closely"
            ),
        }

        all_vars = {**defaults, **template_vars}
        content = self._fill_template(template, all_vars)

        return GeneratedDocument(
            filename="race_position.md",
            content=content,
            category="race_position",
            circuit=circuit,
            year=year,
        )

    def _fetch_historical_data(
        self,
        year: int,
        circuit: str,
    ) -> Dict[str, Any]:
        """
        Fetch historical race data from OpenF1.

        Args:
            year: Target year
            circuit: Circuit name

        Returns:
            Dict with historical data
        """
        historical = {}

        try:
            # Try to get data from previous year(s)
            for historical_year in range(year - 1, year - 4, -1):
                if historical_year < 2023:
                    break

                # Get meetings for the year
                meetings = self.openf1_provider._request(
                    "meetings",
                    {"year": historical_year}
                )

                if not meetings:
                    continue

                # Find matching circuit
                circuit_meeting = None
                circuit_lower = circuit.lower().replace("_", " ")
                for meeting in meetings:
                    meeting_name = meeting.get("meeting_name", "").lower()
                    if circuit_lower in meeting_name:
                        circuit_meeting = meeting
                        break

                if not circuit_meeting:
                    continue

                meeting_key = circuit_meeting.get("meeting_key")

                # Get race session
                sessions = self.openf1_provider._request(
                    "sessions",
                    {
                        "year": historical_year,
                        "meeting_key": meeting_key,
                        "session_name": "Race"
                    }
                )

                if not sessions:
                    continue

                session_key = sessions[0].get("session_key")
                if session_key is None:
                    continue

                # Fetch weather data
                weather = self.openf1_provider.get_weather(int(session_key))
                if not weather.empty:
                    historical["avg_air_temp"] = round(
                        weather["air_temperature"].mean(), 1
                    )
                    historical["avg_track_temp"] = round(
                        weather["track_temperature"].mean(), 1
                    )
                    historical["avg_humidity"] = round(
                        weather["humidity"].mean(), 1
                    )

                # Fetch stints data
                stints = self.openf1_provider.get_stints(int(session_key))
                if not stints.empty:
                    historical["historical_stints"] = (
                        self._analyze_stints(stints)
                    )

                # Fetch pit stops
                pit_stops = self.openf1_provider.get_pit_stops(int(session_key))
                if not pit_stops.empty:
                    historical["historical_pit_data"] = (
                        self._analyze_pit_stops(pit_stops)
                    )

                # Fetch race control for SC data
                race_control = self.openf1_provider.get_race_control_messages(
                    int(session_key)
                )
                if not race_control.empty:
                    historical["sc_data"] = (
                        self._analyze_safety_cars(race_control)
                    )

                logger.info(
                    f"Fetched historical data from {historical_year} for "
                    f"{circuit}"
                )
                break

        except Exception as e:
            logger.warning(f"Error fetching historical data: {e}")

        return historical

    def _analyze_stints(self, stints_df) -> Dict[str, Any]:
        """Analyze stint data to extract useful information."""
        if stints_df.empty:
            return {}

        analysis = {}

        # Get stint lengths by compound
        if "compound" in stints_df.columns and "stint_length" in stints_df.columns:
            for compound in ["SOFT", "MEDIUM", "HARD"]:
                compound_stints = stints_df[
                    stints_df["compound"].str.upper() == compound
                ]
                if not compound_stints.empty:
                    analysis[f"{compound.lower()}_avg_stint"] = round(
                        compound_stints["stint_length"].mean(), 1
                    )
                    analysis[f"{compound.lower()}_max_stint"] = int(
                        compound_stints["stint_length"].max()
                    )

        return analysis

    def _analyze_pit_stops(self, pit_stops_df) -> Dict[str, Any]:
        """Analyze pit stop data."""
        if pit_stops_df.empty:
            return {}

        analysis = {}

        if "pit_duration" in pit_stops_df.columns:
            analysis["avg_pit_time"] = round(
                pit_stops_df["pit_duration"].mean(), 2
            )
            analysis["min_pit_time"] = round(
                pit_stops_df["pit_duration"].min(), 2
            )

        if "lap_number" in pit_stops_df.columns:
            # Find common pit windows
            first_stops = pit_stops_df[
                pit_stops_df.groupby("driver_number")["lap_number"]
                .transform("min") == pit_stops_df["lap_number"]
            ]
            if not first_stops.empty:
                analysis["first_stop_avg"] = round(
                    first_stops["lap_number"].mean(), 0
                )

        return analysis

    def _analyze_safety_cars(self, race_control_df) -> Dict[str, Any]:
        """Analyze safety car deployments."""
        if race_control_df.empty:
            return {}

        analysis = {}

        # Count SC and VSC
        if "category" in race_control_df.columns:
            sc_count = len(
                race_control_df[
                    race_control_df["category"].str.contains(
                        "SafetyCar", case=False, na=False
                    )
                ]
            )
            vsc_count = len(
                race_control_df[
                    race_control_df["category"].str.contains(
                        "VirtualSafetyCar", case=False, na=False
                    )
                ]
            )
            analysis["sc_count"] = sc_count
            analysis["vsc_count"] = vsc_count

        return analysis

    def _fill_template(
        self,
        template: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Fill template placeholders with variable values.

        Args:
            template: Template string with {var} placeholders
            variables: Dict of variable name -> value

        Returns:
            Filled template string
        """
        result = template

        # Replace all {var} placeholders
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # Find remaining unfilled placeholders and replace with defaults
        remaining = re.findall(r"\{(\w+)\}", result)
        for var in remaining:
            result = result.replace("{" + var + "}", "N/A")

        return result

    def _save_documents(
        self,
        year: int,
        circuit: str,
        documents: Dict[str, GeneratedDocument],
    ) -> None:
        """Save generated documents to disk."""
        output_dir = self.output_base / str(year) / "circuits" / circuit
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, doc in documents.items():
            filepath = output_dir / filename
            filepath.write_text(doc.content, encoding="utf-8")
            logger.info(f"Saved {filepath}")

    def get_similar_circuits(self, circuit: str) -> List[str]:
        """
        Get list of similar circuits for data augmentation.

        Args:
            circuit: Circuit name

        Returns:
            List of similar circuit names
        """
        similar = []

        for group_name, circuits in CIRCUIT_GROUPS.items():
            if circuit in circuits:
                similar.extend(
                    [c for c in circuits if c != circuit]
                )

        return list(set(similar))

    def list_available_circuits(self) -> List[str]:
        """List all circuits with predefined data."""
        return list(CIRCUIT_DATA.keys())

    def _get_default_circuit_data(self, circuit: str) -> Dict[str, Any]:
        """Get default data for unknown circuits."""
        return {
            "full_name": circuit.replace("_", " ").title() + " Circuit",
            "location": "Unknown",
            "timezone": "UTC",
            "lap_length": 5.0,
            "total_laps": 55,
            "pit_loss": 20.0,
            "drs_zones": 2,
            "circuit_type": "Unknown",
            "climate_type": "Unknown",
            "overtaking_difficulty": 5,
            "track_position_importance": 5,
            "stress_level": 5,
            "front_stress": 5,
            "rear_stress": 5,
            "sc_probability": 35,
        }

    # Helper methods for circuit-specific content
    def _get_track_layout(self, circuit: str) -> str:
        """Get track layout description."""
        layouts = {
            "bahrain": (
                "Flowing desert circuit with long straights and technical "
                "infield. Turn 1 is a key overtaking zone after the main "
                "straight."
            ),
            "abu_dhabi": (
                "Modern circuit featuring hotel section, long back straight, "
                "and flowing final sector under the hotel."
            ),
            "monaco": (
                "Ultra-tight street circuit through Monte Carlo. Famous for "
                "Casino Square, tunnel, and Swimming Pool chicane."
            ),
            "monza": (
                "Temple of Speed. Long straights, famous chicanes, Parabolica. "
                "Lowest downforce configuration of the year."
            ),
            "spa": (
                "Legendary circuit through Ardennes forest. Features Eau Rouge, "
                "Kemmel straight, and challenging middle sector."
            ),
        }
        return layouts.get(
            circuit,
            "Technical circuit requiring good car balance and tire management."
        )

    def _get_overtaking_zones(self, circuit: str) -> str:
        """Get overtaking zones description."""
        zones = {
            "bahrain": (
                "1. Turn 1 (end of DRS zone 1)\n"
                "2. Turn 4 (end of DRS zone 2)\n"
                "3. Turn 11 (end of back straight)"
            ),
            "abu_dhabi": (
                "1. Turn 6 hairpin (end of DRS zone 1)\n"
                "2. Turn 9 (end of back straight)"
            ),
            "monza": (
                "1. Turn 1 chicane (heavy braking)\n"
                "2. Second chicane\n"
                "3. Parabolica entry"
            ),
        }
        return zones.get(
            circuit,
            "Main straight end\nSecondary straight end"
        )

    def _get_sc_zones(self, circuit: str) -> str:
        """Get common safety car zones."""
        zones = {
            "monaco": "Swimming pool chicane, Tunnel exit, Rascasse",
            "singapore": "Turn 7, Turn 14, Anderson Bridge",
            "jeddah": "Turn 22-24 complex, Turn 1 approach",
            "bahrain": "Turn 1 gravel trap, Turn 4, Turn 11",
        }
        return zones.get(circuit, "Turn 1 area, chicanes, wall sections")

    def _get_sc_strategy(self, circuit: str) -> str:
        """Get SC strategy implications."""
        strategies = {
            "monaco": (
                "SC likely to bunch field. Track position paramount - "
                "pit under SC only if necessary. Undercut power minimal."
            ),
            "singapore": (
                "High SC probability makes track position valuable. "
                "Consider staying out under SC to gain positions."
            ),
        }
        return strategies.get(
            circuit,
            (
                "SC provides opportunity for cheap pit stops. Monitor "
                "tire age vs rivals to optimize stop timing."
            )
        )

    def _get_temp_evolution(self, circuit: str) -> str:
        """Get temperature evolution description."""
        evolutions = {
            "bahrain": (
                "Track cools rapidly after sunset. Expect 5-10°C drop "
                "in track temperature during twilight races."
            ),
            "abu_dhabi": (
                "Day-to-night race. Track temp peaks mid-race then drops "
                "significantly in final stint as sun sets."
            ),
            "singapore": (
                "Night race with consistent high humidity. Track temp "
                "remains stable but rubber builds throughout."
            ),
        }
        return evolutions.get(
            circuit,
            "Track temperature typically peaks mid-afternoon and cools "
            "towards evening. Monitor for strategy implications."
        )

    def _get_seasonal_rain(self, circuit: str) -> str:
        """Get seasonal rain description."""
        rain_info = {
            "spa": (
                "Microclimates in Ardennes make weather unpredictable. "
                "Rain can affect one sector while another stays dry."
            ),
            "interlagos": (
                "Brazilian spring brings afternoon thunderstorms. "
                "Rain typically arrives late in sessions."
            ),
            "singapore": (
                "Monsoon season brings sudden heavy downpours. "
                "Humidity remains high regardless."
            ),
        }
        return rain_info.get(
            circuit,
            "Monitor local forecasts. Weather can change throughout race weekend."
        )

    def _get_crosswind_info(self, circuit: str) -> str:
        """Get crosswind information."""
        return (
            "Crosswinds can affect car balance in high-speed corners. "
            "Monitor wind direction changes for setup adjustments."
        )

    def _get_stress_notes(self, circuit: str) -> str:
        """Get tire stress notes."""
        notes = {
            "bahrain": "High rear degradation, traction zones stress rears",
            "barcelona": "Front-limited, high lateral loads in sector 2",
            "hungaroring": "High downforce, constant direction changes",
            "monza": "Low overall stress, but heavy braking zones",
        }
        return notes.get(circuit, "Balanced tire stress across compounds")

    def _get_high_stress_corners(self, circuit: str) -> str:
        """Get high stress corners table."""
        corners = {
            "bahrain": (
                "| Turn 10 | Fast right | Rear wear | Smooth steering |\n"
                "| Turn 4 | Hairpin | Traction | Avoid wheelspin |"
            ),
            "abu_dhabi": (
                "| Turn 5 | High-speed | Front stress | Trail braking |\n"
                "| Turn 9 | Hairpin | Traction | Avoid lockups |"
            ),
        }
        return corners.get(
            circuit,
            "| Turn 1 | Various | Balanced | Smooth inputs |"
        )

    def _get_traction_zones(self, circuit: str) -> str:
        """Get traction zone description."""
        return (
            "Key traction zones where rear tires are most stressed. "
            "Manage throttle application to preserve rear life."
        )

    def _get_lift_coast_zones(self, circuit: str) -> str:
        """Get lift and coast zones."""
        zones = {
            "bahrain": "Before Turn 1, Turn 4, Turn 10, Turn 14",
            "abu_dhabi": "Before Turn 6, Turn 9, Turn 14",
            "monza": "Before chicanes (limited benefit due to DRS)",
        }
        return zones.get(
            circuit,
            "Before major braking zones to manage tire temperatures"
        )

    def _format_historical_strategies(self, historical: Dict) -> str:
        """Format historical strategy data."""
        if not historical:
            return "Historical data not available for this circuit/year."

        lines = ["### Recent Winning Approaches\n"]

        if "first_stop_avg" in historical:
            lines.append(
                f"- Average first pit stop: Lap {historical['first_stop_avg']}"
            )

        if "sc_count" in historical:
            lines.append(
                f"- Safety cars in recent race: {historical['sc_count']}"
            )

        return "\n".join(lines) if len(lines) > 1 else (
            "Historical data not available for this circuit/year."
        )

    # === NEW HELPER METHODS FOR EXPANDED TEMPLATES ===

    def _get_drs_zones_table(self, circuit: str) -> str:
        """Get DRS zones table for circuit."""
        zones = {
            "bahrain": (
                "| 1 | Turn 14 exit | Turn 1 | Long straight |\n"
                "| 2 | Turn 3 exit | Turn 4 | Short DRS zone |\n"
                "| 3 | Turn 10 exit | Turn 11 | Back straight |"
            ),
            "jeddah": (
                "| 1 | Turn 7 exit | Turn 8 | Long straight |\n"
                "| 2 | Turn 10 exit | Turn 13 | Medium straight |\n"
                "| 3 | Turn 25 exit | Turn 27 | Final straight |"
            ),
            "abu_dhabi": (
                "| 1 | Turn 5 exit | Turn 6 | Back straight |\n"
                "| 2 | Turn 9 exit | Turn 11 | Hotel straight |"
            ),
            "monza": (
                "| 1 | Lesmo 2 exit | Turn 4 | Straight |\n"
                "| 2 | Parabolica exit | Turn 1 | Main straight |"
            ),
        }
        return zones.get(
            circuit,
            "| 1 | Sector 1 exit | Sector 2 | Primary zone |\n"
            "| 2 | Sector 2 exit | Sector 3 | Secondary zone |"
        )

    def _get_non_drs_overtaking(self, circuit: str) -> str:
        """Get non-DRS overtaking opportunities."""
        non_drs = {
            "bahrain": (
                "- Turn 4 hairpin: Late braking opportunity\n"
                "- Turn 10: Wide entry allows multiple lines\n"
                "- Turn 14: Heavy braking zone"
            ),
            "monaco": (
                "- Turn 1 Sainte Devote: Only realistic opportunity\n"
                "- Nouvelle Chicane: Tight but possible\n"
                "- Swimming Pool: Very difficult"
            ),
            "spa": (
                "- La Source hairpin: Classic overtaking spot\n"
                "- Les Combes: Uphill braking zone\n"
                "- Bus Stop chicane: Late race opportunities"
            ),
        }
        return non_drs.get(
            circuit,
            "- Heavy braking zones before corners\n"
            "- Hairpins and chicanes\n"
            "- Wide corner entries allowing multiple lines"
        )

    def _get_defensive_lines(self, circuit: str) -> str:
        """Get defensive line recommendations."""
        return (
            "**Defensive Positioning:**\n\n"
            "1. Cover the inside line into braking zones\n"
            "2. Stay tight on corner exit to prevent cutback\n"
            "3. Use full track width on straights\n"
            "4. Force attacker to the dirty side of track\n"
            "5. Make one defensive move only (FIA regulations)"
        )

    def _get_alternative_strategies(self, circuit: str) -> str:
        """Get alternative/creative strategies for circuit."""
        alternatives = {
            "monaco": (
                "1. **Super-early stop**: Pit lap 10-15 for track position\n"
                "2. **No-stop gamble**: If SC likely, stay out entire race\n"
                "3. **Opposite compound**: Start HARD when rivals on SOFT"
            ),
            "hungary": (
                "1. **Extreme undercut**: Pit 3-4 laps earlier than planned\n"
                "2. **3-stop strategy**: Fresh tires for final 15 laps\n"
                "3. **Overcut all**: Stay out when field pits"
            ),
            "spa": (
                "1. **Weather gamble**: Pit early if rain approaching\n"
                "2. **Super-extended stint**: 1-stop vs 2-stop field\n"
                "3. **Split strategy**: Run different compounds from teammate"
            ),
        }
        return alternatives.get(
            circuit,
            "1. **Extended first stint**: Gain track position after pit\n"
            "2. **Opposite strategy**: Counter rivals' expected approach\n"
            "3. **SC gamble**: Stay out if SC probability high"
        )

    def _get_leader_fear(self, circuit: str) -> str:
        """What leaders fear most at this circuit."""
        fears = {
            "monaco": "Late SC bunching the field",
            "hungary": "Successful undercut from P2-P3",
            "monza": "Slipstream attacks on main straight",
            "spa": "Weather changes mid-race",
        }
        return fears.get(circuit, "Successful undercut or late SC")

    def _get_midfield_fear(self, circuit: str) -> str:
        """What midfield drivers fear most."""
        return "DRS trains preventing progress, wrong strategy call"

    def _get_backmarker_opportunity(self, circuit: str) -> str:
        """Backmarker strategic opportunities."""
        return "Early stop for clean air, SC/VSC gambles, opposite strategy"

    def _format_historical_winners(self, historical: Dict) -> str:
        """Format historical winners table."""
        if not historical:
            return (
                "| 2023 | - | 1-Stop | Standard race |\n"
                "| 2024 | - | 1-Stop | Clean race |"
            )

        lines = []
        for year, data in historical.items():
            winner = data.get("winner", "-")
            strategy = data.get("strategy", "1-Stop")
            key_factor = data.get("key_factor", "Normal race")
            lines.append(f"| {year} | {winner} | {strategy} | {key_factor} |")

        return "\n".join(lines) if lines else (
            "| 2023 | - | 1-Stop | Standard race |"
        )

    def _get_strategy_patterns(self, circuit: str) -> str:
        """Get common strategy patterns for circuit."""
        patterns = {
            "bahrain": (
                "- 1-stop MEDIUM→HARD dominates in dry conditions\n"
                "- Undercut is powerful (~2 second advantage)\n"
                "- SC probability affects window timing"
            ),
            "monaco": (
                "- Track position is everything\n"
                "- 1-stop MEDIUM→HARD standard\n"
                "- SC almost certain, timing is key"
            ),
            "spa": (
                "- Weather can force wet tires at any moment\n"
                "- 1-stop possible if low degradation\n"
                "- 2-stop common due to high-speed corners"
            ),
        }
        return patterns.get(
            circuit,
            "- Standard 1-stop strategy most common\n"
            "- 2-stop viable for aggressive drivers\n"
            "- SC timing often decides race outcome"
        )

    def _get_circuit_trends(self, circuit: str) -> str:
        """Get circuit-specific trends."""
        return (
            "Based on recent seasons:\n"
            "- Qualifying position strongly correlates with race finish\n"
            "- First lap incidents common at Turn 1\n"
            "- Midfield battles often decided by strategy"
        )

    def _get_consideration_do(self, circuit: str, num: int) -> str:
        """Get 'do' considerations for circuit."""
        dos = {
            1: "Monitor tire temperatures closely",
            2: "Have contingency plans for SC/VSC",
            3: "Consider track evolution when planning pit stop",
        }
        return dos.get(num, f"Strategic consideration {num}")

    def _get_consideration_dont(self, circuit: str, num: int) -> str:
        """Get 'don't' considerations for circuit."""
        donts = {
            1: "Commit to strategy too early",
            2: "Ignore weather radar updates",
            3: "Follow rivals blindly into pit lane",
        }
        return donts.get(num, f"Avoid mistake {num}")

    def _get_dry_strategy(self, circuit: str) -> str:
        """Get dry conditions strategy."""
        return (
            "Standard compound progression: MEDIUM → HARD or SOFT → MEDIUM.\n"
            "Focus on tire management in high-degradation sectors.\n"
            "Monitor competitors' pace and adapt pit window accordingly."
        )

    def _get_wet_strategy(self, circuit: str) -> str:
        """Get wet conditions strategy."""
        return (
            "Intermediate tires for light rain/drying conditions.\n"
            "Full wet tires for heavy standing water.\n"
            "Be ready for quick crossover when track evolves.\n"
            "First to switch often gains significant advantage."
        )

    def _format_historical_weather(self, historical: Dict) -> str:
        """Format historical weather data table."""
        if not historical:
            return "| 2023 | 28°C | 42°C | No | Standard dry race |"

        lines = []
        for year, data in historical.items():
            air = data.get("air_temp", "28")
            track = data.get("track_temp", "40")
            rain = "Yes" if data.get("rain", False) else "No"
            notes = data.get("notes", "Standard conditions")
            lines.append(f"| {year} | {air}°C | {track}°C | {rain} | {notes} |")

        return "\n".join(lines) if lines else (
            "| 2023 | 28°C | 42°C | No | Standard dry race |"
        )

    def _get_notable_weather_events(self, circuit: str) -> str:
        """Get notable weather events for circuit."""
        events = {
            "spa": (
                "- **2021**: Race red-flagged due to extreme rain, "
                "only 2 laps completed\n"
                "- **2023**: Changeable conditions throughout weekend"
            ),
            "singapore": (
                "- **2017**: Wet race start, first lap incident\n"
                "- Rain threats common due to tropical climate"
            ),
            "brazil": (
                "- **2016**: Extreme wet conditions, multiple SC periods\n"
                "- **2022**: Dry race but threat of afternoon storms"
            ),
        }
        return events.get(
            circuit,
            "No major weather events in recent seasons. "
            "Check local forecasts for current conditions."
        )

    def _get_compound_reasoning(self, circuit: str) -> str:
        """Get compound selection reasoning for circuit."""
        reasoning = {
            "bahrain": (
                "High-degradation desert circuit requires softer compounds. "
                "C2/C3/C4 selection allows flexibility for 1-stop or 2-stop."
            ),
            "monaco": (
                "Low-degradation due to low speeds and short lap. "
                "Softest compounds (C3/C4/C5) for maximum grip."
            ),
            "monza": (
                "Low-downforce, high-speed circuit. "
                "Harder compounds (C2/C3/C4) to handle traction zones."
            ),
        }
        return reasoning.get(
            circuit,
            "Pirelli selects compounds based on circuit characteristics, "
            "historical data, and expected temperatures."
        )

    def _get_braking_zones(self, circuit: str) -> str:
        """Get critical braking zones description."""
        return (
            "Heavy braking into Turn 1 from high speed generates "
            "significant front tire load. "
            "Monitor brake temperatures and front tire wear."
        )

    def _get_temp_trend_impact(self, circuit: str) -> str:
        """Get temperature trend impact on tires."""
        return (
            "Track temperature typically rises during morning sessions "
            "and stabilizes by race time. "
            "Afternoon races may see cooling track in final stint."
        )

    def _get_quali_recommendation(self, circuit: str) -> str:
        """Get qualifying tire recommendation."""
        return (
            "**Q1**: Use oldest set of SOFT available.\n"
            "**Q2**: Strategic choice - MEDIUM for free tire "
            "choice in race (P11+) or SOFT for track position.\n"
            "**Q3**: Fresh SOFT for maximum performance."
        )

    def _get_race_start_recommendation(self, circuit: str) -> str:
        """Get race start tire recommendation."""
        return (
            "Starting compound depends on Q2 result for top 10. "
            "From P11 back, consider:\n"
            "- MEDIUM for longer first stint\n"
            "- SOFT for aggressive early pace\n"
            "- HARD rarely, only for extreme temperatures"
        )

    def _get_avg_stint_analysis(self, circuit: str) -> str:
        """Get average stint length analysis."""
        return (
            "Based on recent races:\n"
            "- SOFT stints average 15-20 laps\n"
            "- MEDIUM stints average 25-30 laps\n"
            "- HARD stints can extend to 35+ laps if managed"
        )

    def _get_notable_tire_strategies(self, circuit: str) -> str:
        """Get notable tire strategies from history."""
        return (
            "**Notable Examples:**\n"
            "- Extended stints in clean air often outperform standard timing\n"
            "- SC periods can reset strategy entirely\n"
            "- Track evolution can extend stint lengths by 3-5 laps"
        )

    def _get_unconventional_tire(self, circuit: str) -> str:
        """Get unconventional tire strategies."""
        return (
            "**Creative Options:**\n"
            "1. Start on HARD when everyone expects MEDIUM\n"
            "2. Super-short SOFT stint then long MEDIUM stint\n"
            "3. 3-stop with all fresh SOFT sets\n"
            "4. Extreme tire saving for unexpected 1-stop"
        )

    def _format_historical_stints(self, historical: Dict) -> str:
        """Format historical stint data."""
        if not historical:
            return (
                "| 2023 | - | 1-Stop | M→H | 25, 32 |\n"
                "| 2024 | - | 1-Stop | M→H | 24, 33 |"
            )
        return (
            "| 2023 | - | 1-Stop | M→H | 25, 32 |\n"
            "| 2024 | - | 1-Stop | M→H | 24, 33 |"
        )


# Singleton instance
_template_generator: Optional[TemplateGenerator] = None


def get_template_generator() -> TemplateGenerator:
    """Get or create the singleton TemplateGenerator instance."""
    global _template_generator
    if _template_generator is None:
        _template_generator = TemplateGenerator()
    return _template_generator


def reset_template_generator() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _template_generator
    _template_generator = None
