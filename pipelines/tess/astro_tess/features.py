from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.signal import periodogram


FEATURE_COLUMNS = [
    "dominant_period",
    "period_power",
    "amplitude",
    "dispersion",
    "dip_depth",
    "asymmetry",
    "outlier_fraction",
    "change_rate",
]


def extract_features(time: np.ndarray, flux: np.ndarray) -> dict[str, float]:
    amplitude = float(np.nanpercentile(flux, 95) - np.nanpercentile(flux, 5))
    dispersion = float(np.nanstd(flux))
    dip_depth = float(np.nanmedian(flux) - np.nanmin(flux))
    asymmetry = float(stats.skew(flux, bias=False)) if flux.size > 2 else 0.0
    outlier_fraction = float(np.mean(np.abs(flux - np.nanmedian(flux)) > 2.5 * np.nanstd(flux)))
    change_rate = float(np.mean(np.abs(np.diff(flux)))) if flux.size > 1 else 0.0

    if time.size > 4:
        cadence = float(np.median(np.diff(time)))
        frequencies, powers = periodogram(flux, fs=(1.0 / cadence) if cadence else 1.0)
        if frequencies.size > 1:
            peak_index = int(np.argmax(powers[1:]) + 1)
            dominant_frequency = float(frequencies[peak_index])
            dominant_period = 0.0 if dominant_frequency == 0 else 1.0 / dominant_frequency
            period_power = float(powers[peak_index])
        else:
            dominant_period = 0.0
            period_power = 0.0
    else:
        dominant_period = 0.0
        period_power = 0.0

    return {
        "dominant_period": dominant_period,
        "period_power": period_power,
        "amplitude": amplitude,
        "dispersion": dispersion,
        "dip_depth": dip_depth,
        "asymmetry": asymmetry if np.isfinite(asymmetry) else 0.0,
        "outlier_fraction": outlier_fraction if np.isfinite(outlier_fraction) else 0.0,
        "change_rate": change_rate,
    }


def variability_hint(features: dict[str, float]) -> str:
    if features["dip_depth"] > 2.0 and features["period_power"] > 10.0:
        return "transit-like dip"
    if features["amplitude"] > 2.5 and abs(features["asymmetry"]) > 0.5:
        return "high-amplitude variable"
    if features["change_rate"] > 0.7:
        return "step-change anomaly"
    if features["period_power"] > 4.0:
        return "periodic variable"
    return "irregular variable"


def feature_matrix(rows: list[dict[str, float]]) -> np.ndarray:
    return np.asarray([[row[column] for column in FEATURE_COLUMNS] for row in rows], dtype=float)

