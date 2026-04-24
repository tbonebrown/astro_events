from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


def _minmax(values: np.ndarray) -> np.ndarray:
    lower = float(np.min(values))
    upper = float(np.max(values))
    if np.isclose(lower, upper):
        return np.zeros_like(values)
    return (values - lower) / (upper - lower)


@dataclass(slots=True)
class EnsembleAnomalyScorer:
    hidden_ratio: float = 0.4
    random_state: int = 17
    feature_weight: float = 0.45
    reconstruction_weight: float = 0.55
    sequence_scaler: StandardScaler = field(init=False)
    feature_scaler: StandardScaler = field(init=False)
    feature_model: IsolationForest = field(init=False)
    sequence_model: MLPRegressor | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.sequence_scaler = StandardScaler()
        self.feature_scaler = StandardScaler()
        self.feature_model = IsolationForest(
            n_estimators=200,
            contamination="auto",
            random_state=self.random_state,
        )

    def fit(self, sequences: np.ndarray, features: np.ndarray) -> "EnsembleAnomalyScorer":
        seq_scaled = self.sequence_scaler.fit_transform(sequences)
        feature_scaled = self.feature_scaler.fit_transform(features)
        hidden_size = max(8, int(sequences.shape[1] * self.hidden_ratio))
        self.sequence_model = MLPRegressor(
            hidden_layer_sizes=(hidden_size,),
            activation="tanh",
            max_iter=400,
            random_state=self.random_state,
        )
        self.sequence_model.fit(seq_scaled, seq_scaled)
        self.feature_model.fit(feature_scaled)
        return self

    def score(self, sequences: np.ndarray, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self.sequence_model is None:
            raise RuntimeError("Scorer must be fit before scoring.")

        seq_scaled = self.sequence_scaler.transform(sequences)
        feature_scaled = self.feature_scaler.transform(features)

        reconstructed = self.sequence_model.predict(seq_scaled)
        reconstruction_error = np.mean((seq_scaled - reconstructed) ** 2, axis=1)
        feature_score = -self.feature_model.score_samples(feature_scaled)

        reconstruction_component = _minmax(reconstruction_error)
        feature_component = _minmax(feature_score)
        blended = (
            self.reconstruction_weight * reconstruction_component
            + self.feature_weight * feature_component
        )
        return blended, reconstruction_error, feature_score
