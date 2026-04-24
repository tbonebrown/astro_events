from __future__ import annotations

import numpy as np

from astro_tess.preprocess import clean_light_curve, normalize_flux, resample_light_curve


def test_clean_light_curve_drops_invalid_points() -> None:
    time = np.array([0.0, 1.0, 2.0, 3.0, np.nan])
    flux = np.array([1.0, 1.1, np.nan, 25.0, 1.0])

    cleaned_time, cleaned_flux = clean_light_curve(time, flux, sigma=3.0)

    assert cleaned_time.tolist() == [0.0, 1.0, 3.0]
    assert cleaned_flux.tolist() == [1.0, 1.1, 25.0]


def test_resample_and_normalize_flux() -> None:
    time = np.array([0.0, 1.0, 2.0, 3.0])
    flux = np.array([1.0, 1.5, 0.5, 1.0])

    resampled_time, resampled_flux = resample_light_curve(time, flux, points=8)
    normalized = normalize_flux(resampled_flux)

    assert len(resampled_time) == 8
    assert len(resampled_flux) == 8
    assert np.isclose(np.median(normalized), 0.0, atol=1e-6)
    assert np.isclose(np.std(normalized), 1.0, atol=1e-6)

