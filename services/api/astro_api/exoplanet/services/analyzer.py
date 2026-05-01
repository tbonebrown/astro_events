from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import traceback
import uuid

import numpy as np

from astro_api.config import AppSettings
from astro_api.exoplanet.models.schemas import ExoplanetAnalyzeRequest
from astro_api.exoplanet.services.archive_lookup import ArchiveLookupService
from astro_api.exoplanet.services.bls_detector import (
    confidence_label,
    fold_light_curve,
    run_bls,
    score_candidate,
)
from astro_api.exoplanet.services.cache import ExoplanetCache
from astro_api.exoplanet.services.kepler_service import KeplerLightCurveService
from astro_api.exoplanet.services.llm_reporter import LLMReporter
from astro_api.exoplanet.services.ml_classifier import FoldedClassifier
from astro_api.exoplanet.services.preprocessing import preprocess_light_curve
from astro_api.exoplanet.services.targets import DEMO_TARGETS, resolve_target
from astro_api.exoplanet.services.tess_service import TESSLightCurveService


PIPELINE_STEPS = [
    ("resolve", "resolving target"),
    ("download", "downloading light curve"),
    ("clean", "cleaning signal"),
    ("search", "searching transit periods"),
    ("fold", "folding light curve"),
    ("archive", "checking archives"),
    ("report", "generating report"),
]


@dataclass
class ExoplanetJob:
    job_id: str
    request: ExoplanetAnalyzeRequest
    status: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    steps: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ExoplanetAnalysisManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.cache = ExoplanetCache(settings)
        self.tess_service = TESSLightCurveService(settings)
        self.kepler_service = KeplerLightCurveService(settings)
        self.archive_lookup = ArchiveLookupService(settings)
        self.classifier = FoldedClassifier(settings)
        self.reporter = LLMReporter(settings)
        self.executor = ThreadPoolExecutor(max_workers=max(1, settings.max_workers))
        self.jobs: dict[str, ExoplanetJob] = {}

    def demo_targets(self) -> list[dict[str, Any]]:
        return [dict(target) for target in DEMO_TARGETS]

    def submit(self, request: ExoplanetAnalyzeRequest) -> tuple[ExoplanetJob, bool]:
        job_id = uuid.uuid4().hex[:16]
        job = ExoplanetJob(job_id=job_id, request=request, steps=self._fresh_steps())
        self.jobs[job_id] = job
        if request.run_synchronously:
            cache_hit = self._run_job(job_id)
        else:
            future = self.executor.submit(self._run_job, job_id)
            future.add_done_callback(lambda completed: completed.exception())
            cache_hit = False
        return job, cache_hit

    def status(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress,
            "steps": job.steps,
            "error": job.error,
        }

    def result(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if not job or job.status != "completed":
            return None
        return job.result

    def report(self, job_id: str) -> dict[str, Any] | None:
        result = self.result(job_id)
        if not result:
            return None
        return result.get("report")

    def cache_entries(self, target_id: str) -> list[dict[str, Any]]:
        return self.cache.list_entries_for_target(target_id)

    def _fresh_steps(self) -> list[dict[str, Any]]:
        return [{"id": step_id, "label": label, "status": "pending"} for step_id, label in PIPELINE_STEPS]

    def _mark_step(self, job: ExoplanetJob, step_id: str, status: str) -> None:
        for step in job.steps:
            if step["id"] == step_id:
                step["status"] = status
                break
        completed = sum(1 for step in job.steps if step["status"] == "complete")
        job.progress = round(completed / len(job.steps), 3)
        active = next((step for step in job.steps if step["status"] == "running"), None)
        job.stage = active["label"] if active else (job.steps[min(completed, len(job.steps) - 1)]["label"])

    def _start_step(self, job: ExoplanetJob, step_id: str) -> None:
        job.status = "running"
        self._mark_step(job, step_id, "running")

    def _complete_step(self, job: ExoplanetJob, step_id: str) -> None:
        self._mark_step(job, step_id, "complete")

    def _run_job(self, job_id: str) -> bool:
        job = self.jobs[job_id]
        cache_hit = False
        try:
            self._start_step(job, "resolve")
            target = resolve_target(job.request.target, job.request.target_type, job.request.mission)
            analysis_key = self.cache.analysis_key(target, job.request)
            self._complete_step(job, "resolve")

            if not job.request.force_refresh:
                cached = self.cache.load_result(analysis_key)
                if cached:
                    cached["job_id"] = job_id
                    job.result = cached
                    job.status = "completed"
                    job.stage = "loaded from cache"
                    job.progress = 1.0
                    for step in job.steps:
                        step["status"] = "complete"
                    return True

            self._start_step(job, "download")
            lightcurve_service = self.kepler_service if target["mission"] == "Kepler" else self.tess_service
            time, flux, provenance = lightcurve_service.get_light_curve(target, job.request, self.cache)
            self._complete_step(job, "download")

            self._start_step(job, "clean")
            processed = preprocess_light_curve(time, flux, method=job.request.detrend_method)
            self._complete_step(job, "clean")

            self._start_step(job, "search")
            detection = run_bls(
                processed.time,
                processed.cleaned_flux,
                period_min_days=job.request.period_min_days,
                period_max_days=job.request.period_max_days,
                duration_min_hours=job.request.duration_min_hours,
                duration_max_hours=job.request.duration_max_hours,
            )
            self._complete_step(job, "search")

            self._start_step(job, "fold")
            folded = fold_light_curve(processed.time, processed.cleaned_flux, detection)
            classifier = self.classifier.classify(folded.phase, folded.flux, detection.snr, detection.depth)
            self._complete_step(job, "fold")

            self._start_step(job, "archive")
            archive_match = self.archive_lookup.lookup(target, detection.period_days)
            self._complete_step(job, "archive")

            classifier_score = classifier["probabilities"].get("likely_transit", 0.0)
            confidence, breakdown = score_candidate(
                detection,
                classifier_score=classifier_score,
                archive_is_match=archive_match["status"] == "match",
            )
            candidate = {
                "candidate_id": f"{target['target_id']}-{detection.period_days:.5f}d",
                "target_id": target["target_id"],
                "period_days": round(detection.period_days, 8),
                "transit_time": round(detection.transit_time, 8),
                "duration_hours": round(detection.duration_days * 24.0, 4),
                "depth_ppm": round(detection.depth * 1_000_000.0, 3),
                "snr": round(detection.snr, 3),
                "power": round(detection.power, 6),
                "observed_transits": detection.observed_transits,
                "radius_ratio": round(detection.radius_ratio, 6),
                "confidence": confidence,
                "confidence_label": confidence_label(confidence),
                "archive_match": archive_match,
                "classifier": classifier,
                "score_breakdown": {key: round(value, 4) for key, value in breakdown.items()},
            }

            self._start_step(job, "report")
            report_payload = {
                "target_id": target["target_id"],
                "target_name": target["name"],
                "mission": target["mission"],
                "period_days": candidate["period_days"],
                "duration_hours": candidate["duration_hours"],
                "depth_ppm": candidate["depth_ppm"],
                "snr": candidate["snr"],
                "power": candidate["power"],
                "observed_transits": candidate["observed_transits"],
                "radius_ratio": candidate["radius_ratio"],
                "confidence": candidate["confidence"],
                "confidence_label": candidate["confidence_label"],
                "archive_match": archive_match,
                "classifier": classifier,
                "point_count": int(len(processed.time)),
                "removed_points": processed.removed_points,
            }
            report = self.reporter.build_report(report_payload)
            self._complete_step(job, "report")

            result = {
                "job_id": job_id,
                "target": target,
                "request": job.request.model_dump(),
                "provenance": {
                    **provenance,
                    "preprocessing": {
                        "method": processed.method,
                        "removed_points": processed.removed_points,
                    },
                    "generated_at": datetime.now(UTC).isoformat(),
                },
                "raw_light_curve": self._series(processed.time, processed.normalized_flux, "Raw normalized flux"),
                "cleaned_light_curve": self._series(processed.time, processed.cleaned_flux, "Cleaned/detrended flux"),
                "periodogram": self._periodogram(detection.period_grid, detection.power_grid, detection.period_days),
                "folded_curve": self._folded(folded),
                "candidates": [candidate],
                "report": report,
            }
            self.cache.save_result(analysis_key, target["target_id"], result)
            job.result = result
            job.status = "completed"
            job.stage = "complete"
            job.progress = 1.0
            return cache_hit
        except Exception as exc:
            job.status = "failed"
            job.stage = "failed"
            job.error = f"{exc}"
            traceback.print_exc()
            for step in job.steps:
                if step["status"] == "running":
                    step["status"] = "failed"
            return False

    @staticmethod
    def _sample(x: np.ndarray, y: np.ndarray, max_points: int = 3500) -> tuple[list[float], list[float]]:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]
        if len(x) > max_points:
            indices = np.linspace(0, len(x) - 1, max_points).astype(int)
            x = x[indices]
            y = y[indices]
        return [round(float(value), 8) for value in x], [round(float(value), 8) for value in y]

    def _series(self, x: np.ndarray, y: np.ndarray, label: str) -> dict[str, Any]:
        xs, ys = self._sample(x, y)
        return {"time": xs, "flux": ys, "label": label}

    def _periodogram(self, periods: np.ndarray, power: np.ndarray, best_period: float) -> dict[str, Any]:
        xs, ys = self._sample(periods, power, max_points=1800)
        return {"period": xs, "power": ys, "best_period": round(float(best_period), 8)}

    def _folded(self, folded) -> dict[str, Any]:
        phase, flux = self._sample(folded.phase, folded.flux, max_points=3500)
        model_phase, model_flux = self._sample(folded.model_phase, folded.model_flux, max_points=240)
        return {
            "phase": phase,
            "flux": flux,
            "model_phase": model_phase,
            "model_flux": model_flux,
        }
