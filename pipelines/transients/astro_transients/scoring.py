from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import IsolationForest

from astro_transients.models import GaiaAlert


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _minmax(values: np.ndarray) -> np.ndarray:
    lower = float(np.min(values))
    upper = float(np.max(values))
    if np.isclose(lower, upper):
        return np.zeros_like(values)
    return (values - lower) / (upper - lower)


@dataclass(slots=True)
class AlertScore:
    score: float
    score_breakdown: dict[str, float]
    classification_hint: str
    novelty_flag: bool
    magnitude_change: float
    sky_region: str


@dataclass(slots=True)
class TwoStageTransientScorer:
    random_state: int = 17
    rule_weight: float = 0.7
    ml_weight: float = 0.3

    def score_alerts(self, alerts: list[GaiaAlert]) -> list[AlertScore]:
        if not alerts:
            return []

        features = np.asarray([self._feature_vector(alert) for alert in alerts], dtype=float)
        rule_components = np.asarray([row[:5] for row in features], dtype=float)
        rule_scores = np.mean(rule_components, axis=1)

        if len(alerts) >= 4:
            model = IsolationForest(
                n_estimators=300,
                contamination="auto",
                random_state=self.random_state,
            )
            model.fit(features)
            ml_raw = -model.score_samples(features)
            ml_scores = _minmax(ml_raw)
        else:
            ml_scores = _minmax(features[:, 2])

        combined = self.rule_weight * rule_scores + self.ml_weight * ml_scores
        results: list[AlertScore] = []
        for index, alert in enumerate(alerts):
            magnitude_change = self._magnitude_change(alert)
            classification_hint = self._classification_hint(alert, magnitude_change)
            novelty_flag = (
                "unknown" in classification_hint.lower()
                or magnitude_change >= 1.5
                or ml_scores[index] >= 0.7
            )
            sky_region = self._sky_region(alert.ra, alert.dec)
            results.append(
                AlertScore(
                    score=float(combined[index]),
                    score_breakdown={
                        "freshness": float(features[index][0]),
                        "brightness": float(features[index][1]),
                        "magnitude_change": float(features[index][2]),
                        "classification_priority": float(features[index][3]),
                        "context_richness": float(features[index][4]),
                        "ml_rerank": float(ml_scores[index]),
                    },
                    classification_hint=classification_hint,
                    novelty_flag=novelty_flag,
                    magnitude_change=magnitude_change,
                    sky_region=sky_region,
                )
            )
        return results

    def _feature_vector(self, alert: GaiaAlert) -> list[float]:
        freshness = self._freshness_score(alert)
        brightness = self._brightness_score(alert.magnitude)
        magnitude_change = self._magnitude_change(alert)
        change_score = min(max(abs(magnitude_change) / 3.0, 0.0), 1.0)
        class_priority = self._classification_priority(alert.classification)
        richness = self._context_richness(alert)
        scatter = min(max((alert.historic_scatter or 0.0) / 1.5, 0.0), 1.0)
        return [
            freshness,
            brightness,
            change_score,
            class_priority,
            richness,
            scatter,
            float(alert.ra) / 360.0,
            (float(alert.dec) + 90.0) / 180.0,
        ]

    @staticmethod
    def _brightness_score(magnitude: float) -> float:
        return min(max((20.5 - magnitude) / 7.0, 0.0), 1.0)

    @staticmethod
    def _magnitude_change(alert: GaiaAlert) -> float:
        if alert.historic_magnitude is None:
            return 0.0
        return float(alert.historic_magnitude - alert.magnitude)

    @staticmethod
    def _classification_priority(classification: str) -> float:
        label = classification.lower()
        if "unknown" in label:
            return 1.0
        if "sn" in label or "supernova" in label:
            return 0.95
        if "fast" in label:
            return 0.9
        if "microlens" in label:
            return 0.75
        if "cv" in label or "nova" in label:
            return 0.72
        return 0.5

    @staticmethod
    def _context_richness(alert: GaiaAlert) -> float:
        score = 0.0
        if alert.comment:
            score += 0.3
        if alert.tns_name:
            score += 0.2
        if alert.source_id:
            score += 0.2
        if alert.classification:
            score += 0.2
        if alert.alert_url:
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _classification_hint(alert: GaiaAlert, magnitude_change: float) -> str:
        if alert.classification:
            return alert.classification
        if abs(magnitude_change) >= 2.0:
            return "strong brightness change"
        return "unknown transient"

    @staticmethod
    def _sky_region(ra: float, dec: float) -> str:
        hemisphere = "north" if dec >= 0 else "south"
        quadrant = int(ra // 90) + 1
        return f"{hemisphere}-q{quadrant}"

    @staticmethod
    def _freshness_score(alert: GaiaAlert) -> float:
        observed = _parse_timestamp(alert.observed_at) or _parse_timestamp(alert.published_at)
        if observed is None:
            return 0.4
        age_hours = max((datetime.now(timezone.utc) - observed).total_seconds() / 3600.0, 0.0)
        return min(max(1.0 - (age_hours / 168.0), 0.0), 1.0)
