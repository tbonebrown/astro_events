from __future__ import annotations

import numpy as np


def sigma_clip_flux(flux: np.ndarray, sigma: float = 5.0) -> np.ndarray:
    center = np.nanmedian(flux)
    spread = np.nanstd(flux)
    if spread == 0 or not np.isfinite(spread):
        return flux
    mask = np.abs(flux - center) <= sigma * spread
    return flux[mask]


def clean_light_curve(time: np.ndarray, flux: np.ndarray, sigma: float = 5.0) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    valid = np.isfinite(time) & np.isfinite(flux)
    time = time[valid]
    flux = flux[valid]
    if time.size == 0:
        return time, flux

    center = np.nanmedian(flux)
    spread = np.nanstd(flux)
    if spread > 0 and np.isfinite(spread):
        mask = np.abs(flux - center) <= sigma * spread
        time = time[mask]
        flux = flux[mask]
    return time, flux


def resample_light_curve(time: np.ndarray, flux: np.ndarray, points: int = 256) -> tuple[np.ndarray, np.ndarray]:
    if time.size == 0:
        target_time = np.linspace(0.0, 1.0, points)
        return target_time, np.zeros(points, dtype=float)

    order = np.argsort(time)
    time = time[order]
    flux = flux[order]
    target_time = np.linspace(float(time[0]), float(time[-1]), points)
    target_flux = np.interp(target_time, time, flux)
    return target_time, target_flux


def normalize_flux(flux: np.ndarray) -> np.ndarray:
    median = float(np.nanmedian(flux))
    centered = flux - median
    scale = float(np.nanstd(centered))
    if scale == 0 or not np.isfinite(scale):
        return centered
    return centered / scale

