from __future__ import annotations

from pathlib import Path

import numpy as np

from astro_api.config import AppSettings
from astro_api.exoplanet.models.schemas import ExoplanetAnalyzeRequest
from astro_api.exoplanet.services.analyzer import ExoplanetAnalysisManager
from astro_api.exoplanet.services.archive_lookup import ArchiveLookupService
from astro_api.exoplanet.services.bls_detector import fold_light_curve, run_bls, score_candidate
from astro_api.exoplanet.services.llm_reporter import LLMReporter
from astro_api.exoplanet.services.preprocessing import preprocess_light_curve
from astro_api.exoplanet.services.targets import resolve_target
from astro_api.exoplanet.services.tess_service import synthetic_light_curve


def test_target_resolution_handles_demo_and_catalog_ids() -> None:
    demo = resolve_target("Kepler-10", "auto", "auto")
    tic = resolve_target("TIC 123456789", "auto", "auto")
    coords = resolve_target("120.5 -18.2", "auto", "auto")

    assert demo["target_id"] == "kepler-10"
    assert demo["mission"] == "Kepler"
    assert tic["target_id"] == "tic-123456789"
    assert coords["resolver"] == "coordinates"


def test_preprocessing_removes_nans_and_outliers() -> None:
    time = np.linspace(0.0, 4.0, 100)
    flux = np.ones_like(time)
    flux[4] = np.nan
    flux[18] = 12.0

    processed = preprocess_light_curve(time, flux, method="median", outlier_sigma=4.0)

    assert np.all(np.isfinite(processed.cleaned_flux))
    assert processed.removed_points >= 1
    assert len(processed.time) < len(time)


def test_bls_returns_expected_period_for_kepler_10_synthetic_demo() -> None:
    target = resolve_target("Kepler-10", "auto", "Kepler")
    time, flux, _metadata = synthetic_light_curve(target, mission="Kepler")
    processed = preprocess_light_curve(time, flux, method="savgol")

    detection = run_bls(processed.time, processed.cleaned_flux, period_min_days=0.5, period_max_days=2.0)

    assert detection.period_days == pytest_approx(target["known_period_days"], rel=0.01)
    assert detection.snr > 3.0


def test_folded_light_curve_generation() -> None:
    target = resolve_target("HAT-P-7", "auto", "Kepler")
    time, flux, _metadata = synthetic_light_curve(target, mission="Kepler")
    processed = preprocess_light_curve(time, flux, method="savgol")
    detection = run_bls(processed.time, processed.cleaned_flux, period_min_days=1.0, period_max_days=4.0)

    folded = fold_light_curve(processed.time, processed.cleaned_flux, detection)

    assert folded.phase.min() >= -0.5
    assert folded.phase.max() <= 0.5
    assert len(folded.model_phase) == len(folded.model_flux)


def test_candidate_scoring_uses_transits_archive_and_classifier() -> None:
    target = resolve_target("Kepler-10", "auto", "Kepler")
    time, flux, _metadata = synthetic_light_curve(target, mission="Kepler")
    processed = preprocess_light_curve(time, flux, method="savgol")
    detection = run_bls(processed.time, processed.cleaned_flux, period_min_days=0.5, period_max_days=2.0)

    score, breakdown = score_candidate(detection, classifier_score=0.82, archive_is_match=True)

    assert 0 <= score <= 100
    assert breakdown["archive_match"] == 1.0
    assert breakdown["ml_classifier"] == 0.82


def test_archive_lookup_fallback_returns_known_match_and_no_match(tmp_path: Path) -> None:
    settings = AppSettings(exoplanet_cache_dir=tmp_path, nasa_archive_timeout=0.01)
    service = ArchiveLookupService(settings)
    kepler = resolve_target("Kepler-10", "auto", "Kepler")
    unknown = resolve_target("Imaginary Star 123", "name", "TESS")

    assert service.lookup(kepler, 0.83749)["status"] == "match"
    assert service.lookup(unknown, 7.25)["status"] == "no_match"


def test_llm_reporter_guardrail_does_not_preserve_discovery_claim(tmp_path: Path) -> None:
    reporter = LLMReporter(AppSettings(exoplanet_cache_dir=tmp_path))

    guarded = reporter._guardrail("This app discovered a new planet around the target.")

    assert "discovered a new planet" not in guarded
    assert "candidate requiring validation" in guarded


def test_exoplanet_manager_completes_single_target_demo(tmp_path: Path) -> None:
    settings = AppSettings(exoplanet_cache_dir=tmp_path, max_workers=1, llm_base_url="http://127.0.0.1:9/v1")
    manager = ExoplanetAnalysisManager(settings)
    request = ExoplanetAnalyzeRequest(
        target="Kepler-10",
        mission="Kepler",
        period_min_days=0.5,
        period_max_days=2.0,
        force_refresh=True,
        run_synchronously=True,
    )

    job, _cache_hit = manager.submit(request)
    result = manager.result(job.job_id)

    assert job.status == "completed"
    assert result is not None
    assert result["candidates"][0]["archive_match"]["status"] == "match"
    assert "new planet discovered" not in result["report"]["sections"][0]["body"].lower()


def pytest_approx(value: float, rel: float):
    import pytest

    return pytest.approx(value, rel=rel)
