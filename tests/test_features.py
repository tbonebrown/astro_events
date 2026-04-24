from __future__ import annotations

import numpy as np

from astro_tess.features import FEATURE_COLUMNS, extract_features, variability_hint


def test_extract_features_returns_expected_columns() -> None:
    time = np.linspace(0.0, 12.0, 256)
    flux = np.sin(time) + 0.05 * np.cos(time * 3)

    features = extract_features(time, flux)

    assert set(features) == set(FEATURE_COLUMNS)
    assert features["amplitude"] > 0
    assert features["dispersion"] > 0


def test_variability_hint_classifies_step_changes() -> None:
    hint = variability_hint(
        {
            "dominant_period": 0.0,
            "period_power": 0.2,
            "amplitude": 1.0,
            "dispersion": 0.5,
            "dip_depth": 0.4,
            "asymmetry": 0.0,
            "outlier_fraction": 0.1,
            "change_rate": 1.1,
        }
    )

    assert hint == "step-change anomaly"

