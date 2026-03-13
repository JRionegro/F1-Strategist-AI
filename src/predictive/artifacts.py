"""Model artifact persistence and loading utilities."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import joblib

from src.predictive.modeling import PitStopBaselineModel, FEATURE_COLUMNS


PREDICTIVE_MODEL_VERSION = "0.1.0"


@dataclass
class ModelMetadata:
    """Metadata stored alongside model artifacts."""

    version: str
    trained_on: str
    feature_columns: list[str]
    n_train: int
    n_test: int
    auc: Optional[float]
    brier: float
    positive_rate: float
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        trained_on: str,
        feature_columns: Iterable[str] = FEATURE_COLUMNS,
        n_train: int,
        n_test: int,
        auc: Optional[float],
        brier: float,
        positive_rate: float,
        version: str = PREDICTIVE_MODEL_VERSION,
    ) -> "ModelMetadata":
        return cls(
            version=version,
            trained_on=trained_on,
            feature_columns=list(feature_columns),
            n_train=n_train,
            n_test=n_test,
            auc=auc,
            brier=brier,
            positive_rate=positive_rate,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


def save_model_artifact(
    model: PitStopBaselineModel,
    metadata: ModelMetadata,
    artifact_path: str | Path,
) -> Path:
    """Persist model and metadata together in a joblib artifact."""

    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"model": model, "metadata": asdict(metadata)}
    joblib.dump(payload, path)

    metadata_path = path.with_suffix(".json")
    with open(metadata_path, "w", encoding="utf-8") as meta_file:
        json.dump(metadata.__dict__, meta_file, indent=2)

    return path


def load_model_artifact(
    artifact_path: str | Path,
    *,
    expected_version: str = PREDICTIVE_MODEL_VERSION,
    expected_features: Iterable[str] = FEATURE_COLUMNS,
) -> tuple[PitStopBaselineModel, ModelMetadata]:
    """Load model and metadata, enforcing version and feature compatibility."""

    path = Path(artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"artifact not found: {path}")

    payload = joblib.load(path)
    model = payload.get("model")
    metadata_dict = payload.get("metadata")

    if model is None or metadata_dict is None:
        raise ValueError("artifact is missing model or metadata")

    metadata = ModelMetadata(**metadata_dict)

    if metadata.version != expected_version:
        raise ValueError(
            f"model version mismatch: {
                metadata.version} != {expected_version}")

    expected_features_list = list(expected_features)
    if metadata.feature_columns != expected_features_list:
        raise ValueError(
            "feature columns mismatch; artifact is stale or incompatible")

    return model, metadata


class PitPredictorService:
    """Prediction service that enforces artifact presence and freshness."""

    def __init__(
        self,
        artifact_path: str | Path,
        *,
        expected_version: str = PREDICTIVE_MODEL_VERSION,
        expected_features: Iterable[str] = FEATURE_COLUMNS,
    ) -> None:
        self.artifact_path = Path(artifact_path)
        self.expected_version = expected_version
        self.expected_features = list(expected_features)
        self._model: Optional[PitStopBaselineModel] = None
        self._metadata: Optional[ModelMetadata] = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._metadata is not None

    @property
    def metadata(self) -> Optional[ModelMetadata]:
        return self._metadata

    def load(self) -> None:
        self._model, self._metadata = load_model_artifact(
            self.artifact_path,
            expected_version=self.expected_version,
            expected_features=self.expected_features,
        )

    def predict_proba(self, df) -> list[float]:
        if not self.is_loaded:
            raise RuntimeError("model not loaded or missing artifact")
        return list(self._model.predict_proba(df))

    def predict(self, df, threshold: float = 0.5) -> list[int]:
        if not self.is_loaded:
            raise RuntimeError("model not loaded or missing artifact")
        return list(self._model.predict(df, threshold=threshold))


__all__ = [
    "PREDICTIVE_MODEL_VERSION",
    "ModelMetadata",
    "save_model_artifact",
    "load_model_artifact",
    "PitPredictorService",
]
