from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from astropy.timeseries import BoxLeastSquares


@dataclass(slots=True)
class BLSDetection:
    period_days: float
    transit_time: float
    duration_days: float
    depth: float
    snr: float
    power: float
    observed_transits: int
    radius_ratio: float
    period_grid: np.ndarray
    power_grid: np.ndarray


@dataclass(slots=True)
class FoldedCurve:
    phase: np.ndarray
    flux: np.ndarray
    model_phase: np.ndarray
    model_flux: np.ndarray


class GPUBLSAccelerator:
    """Future interface for CuPy/PyTorch BLS kernels without changing API callers."""

    enabled = False

    def run(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("GPU BLS acceleration is a future extension; Astropy BLS is used now.")


def run_bls(
    time: np.ndarray,
    flux: np.ndarray,
    period_min_days: float = 0.5,
    period_max_days: float = 30.0,
    duration_min_hours: float = 1.0,
    duration_max_hours: float = 10.0,
    period_samples: int = 3500,
) -> BLSDetection:
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    mask = np.isfinite(time) & np.isfinite(flux)
    time = time[mask]
    flux = flux[mask]
    if len(time) < 32:
        raise ValueError("At least 32 light curve points are required for BLS.")

    period_max_days = max(period_min_days * 1.1, period_max_days)
    baseline = float(np.nanmax(time) - np.nanmin(time))
    if baseline > 0:
        period_max_days = min(period_max_days, max(period_min_days * 1.1, baseline * 0.8))

    periods = np.linspace(period_min_days, period_max_days, period_samples)
    durations = np.linspace(duration_min_hours / 24.0, duration_max_hours / 24.0, 12)
    durations = durations[durations < periods.max() * 0.25]
    if len(durations) == 0:
        durations = np.array([duration_min_hours / 24.0])

    model = BoxLeastSquares(time, flux)
    result = model.power(periods, durations)
    power = np.asarray(result.power, dtype=float)
    best_index = int(np.nanargmax(power))

    period = float(np.asarray(result.period)[best_index])
    duration = float(np.asarray(result.duration)[best_index])
    transit_time = float(np.asarray(result.transit_time)[best_index])
    depth = max(0.0, float(np.asarray(result.depth)[best_index]))
    depth_snr = np.asarray(getattr(result, "depth_snr", np.zeros_like(power)), dtype=float)
    astropy_snr = max(0.0, float(depth_snr[best_index]))
    phase_days = ((time - transit_time + 0.5 * period) % period) - 0.5 * period
    in_transit = np.abs(phase_days) <= 0.5 * duration
    out_of_transit = ~in_transit
    noise = float(np.nanstd(flux[out_of_transit] - np.nanmedian(flux[out_of_transit]))) if np.any(out_of_transit) else 0.0
    empirical_snr = depth / max(noise, 1e-8) * np.sqrt(max(1, int(np.count_nonzero(in_transit))))
    snr = max(astropy_snr, float(empirical_snr))
    observed_transits = max(1, int(np.floor(baseline / period))) if period > 0 and baseline > 0 else 1
    radius_ratio = float(np.sqrt(max(depth, 0.0)))

    return BLSDetection(
        period_days=period,
        transit_time=transit_time,
        duration_days=duration,
        depth=depth,
        snr=snr,
        power=max(0.0, float(power[best_index])),
        observed_transits=observed_transits,
        radius_ratio=radius_ratio,
        period_grid=np.asarray(result.period, dtype=float),
        power_grid=power,
    )


def fold_light_curve(time: np.ndarray, flux: np.ndarray, detection: BLSDetection) -> FoldedCurve:
    phase = ((time - detection.transit_time + 0.5 * detection.period_days) % detection.period_days) / detection.period_days
    phase -= 0.5
    order = np.argsort(phase)
    phase = phase[order]
    folded_flux = flux[order]

    model_phase = np.linspace(-0.5, 0.5, 240)
    model_flux = np.ones_like(model_phase)
    half_width = max(0.003, 0.5 * detection.duration_days / detection.period_days)
    model_flux[np.abs(model_phase) <= half_width] -= detection.depth

    return FoldedCurve(
        phase=phase,
        flux=folded_flux,
        model_phase=model_phase,
        model_flux=model_flux,
    )


def confidence_label(score: float) -> str:
    if score <= 30:
        return "weak/noisy"
    if score <= 60:
        return "possible"
    if score <= 80:
        return "strong candidate"
    return "known/very strong signal"


def score_candidate(
    detection: BLSDetection,
    classifier_score: float,
    archive_is_match: bool,
    depth_consistency: float = 0.7,
) -> tuple[float, dict[str, float]]:
    power_score = min(1.0, detection.power / 0.25)
    snr_score = min(1.0, detection.snr / 12.0)
    transit_score = min(1.0, detection.observed_transits / 4.0)
    duration_fraction = detection.duration_days / max(detection.period_days, 1e-8)
    duration_score = 1.0 if 0.002 <= duration_fraction <= 0.18 else 0.35
    archive_score = 1.0 if archive_is_match else 0.0
    breakdown = {
        "bls_power": power_score,
        "transit_snr": snr_score,
        "observed_transits": transit_score,
        "depth_consistency": max(0.0, min(1.0, depth_consistency)),
        "duration_plausibility": duration_score,
        "archive_match": archive_score,
        "ml_classifier": max(0.0, min(1.0, classifier_score)),
    }
    weighted = (
        0.18 * breakdown["bls_power"]
        + 0.24 * breakdown["transit_snr"]
        + 0.14 * breakdown["observed_transits"]
        + 0.10 * breakdown["depth_consistency"]
        + 0.10 * breakdown["duration_plausibility"]
        + 0.12 * breakdown["archive_match"]
        + 0.12 * breakdown["ml_classifier"]
    )
    return round(100.0 * weighted, 2), breakdown
