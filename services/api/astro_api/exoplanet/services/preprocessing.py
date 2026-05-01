from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class PreprocessedLightCurve:
    time: np.ndarray
    raw_flux: np.ndarray
    normalized_flux: np.ndarray
    cleaned_flux: np.ndarray
    trend: np.ndarray
    removed_points: int
    method: str


def _odd_window(length: int, fraction: float = 0.08, minimum: int = 31) -> int:
    window = max(minimum, int(length * fraction))
    if window % 2 == 0:
        window += 1
    return min(window, length - 1 if length % 2 == 0 else length)


def _running_median(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) < window:
        return np.full_like(values, np.nanmedian(values))
    padded = np.pad(values, window // 2, mode="edge")
    result = np.empty_like(values, dtype=float)
    for index in range(len(values)):
        result[index] = np.nanmedian(padded[index : index + window])
    return result


def preprocess_light_curve(
    time: np.ndarray,
    flux: np.ndarray,
    method: str = "savgol",
    outlier_sigma: float = 6.0,
) -> PreprocessedLightCurve:
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    finite_mask = np.isfinite(time) & np.isfinite(flux)
    time = time[finite_mask]
    raw_flux = flux[finite_mask]

    if len(time) == 0:
        raise ValueError("No finite light curve points are available.")

    order = np.argsort(time)
    time = time[order]
    raw_flux = raw_flux[order]

    median_flux = float(np.nanmedian(raw_flux))
    if not np.isfinite(median_flux) or median_flux == 0:
        median_flux = 1.0
    normalized_flux = raw_flux / median_flux

    residual = normalized_flux - np.nanmedian(normalized_flux)
    mad = float(np.nanmedian(np.abs(residual - np.nanmedian(residual))))
    robust_sigma = 1.4826 * mad if mad > 0 else float(np.nanstd(residual) or 1.0)
    inlier_mask = np.abs(residual) <= outlier_sigma * robust_sigma

    clean_time = time[inlier_mask]
    clean_raw = raw_flux[inlier_mask]
    clean_norm = normalized_flux[inlier_mask]
    removed_points = int(len(time) - len(clean_time))

    if method == "none" or len(clean_norm) < 9:
        trend = np.ones_like(clean_norm)
    else:
        window = _odd_window(len(clean_norm), fraction=0.06, minimum=21)
        if method == "savgol":
            try:
                from scipy.signal import savgol_filter

                trend = savgol_filter(clean_norm, window_length=max(5, window), polyorder=2, mode="interp")
            except Exception:
                trend = _running_median(clean_norm, window=max(5, window))
        else:
            trend = _running_median(clean_norm, window=max(5, window))
        trend = np.where(np.isfinite(trend) & (np.abs(trend) > 1e-8), trend, 1.0)

    cleaned_flux = clean_norm / trend
    cleaned_flux = cleaned_flux / np.nanmedian(cleaned_flux)

    return PreprocessedLightCurve(
        time=clean_time,
        raw_flux=clean_raw,
        normalized_flux=clean_norm,
        cleaned_flux=cleaned_flux,
        trend=trend,
        removed_points=removed_points,
        method=method,
    )
