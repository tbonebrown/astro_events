from __future__ import annotations

from fastapi import APIRouter, HTTPException

from astro_api.exoplanet.models.schemas import (
    BatchScanRequest,
    BatchScanResponse,
    ExoplanetAnalysisResult,
    ExoplanetAnalyzeRequest,
    ExoplanetJobResponse,
    ExoplanetStatusResponse,
)
from astro_api.exoplanet.workers.batch_scan import submit_batch_scan


def create_detection_router(manager) -> APIRouter:
    router = APIRouter()

    @router.post("/analyze", response_model=ExoplanetJobResponse)
    def analyze(request: ExoplanetAnalyzeRequest) -> ExoplanetJobResponse:
        if request.period_max_days <= request.period_min_days:
            raise HTTPException(status_code=422, detail="period_max_days must be larger than period_min_days.")
        if request.duration_max_hours <= request.duration_min_hours:
            raise HTTPException(status_code=422, detail="duration_max_hours must be larger than duration_min_hours.")
        job, cache_hit = manager.submit(request)
        return ExoplanetJobResponse(job_id=job.job_id, status=job.status, cache_hit=cache_hit)

    @router.get("/status/{job_id}", response_model=ExoplanetStatusResponse)
    def status(job_id: str) -> ExoplanetStatusResponse:
        payload = manager.status(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Analysis job not found.")
        return ExoplanetStatusResponse.model_validate(payload)

    @router.get("/result/{job_id}", response_model=ExoplanetAnalysisResult)
    def result(job_id: str) -> ExoplanetAnalysisResult:
        payload = manager.result(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Analysis result is not ready.")
        return ExoplanetAnalysisResult.model_validate(payload)

    @router.post("/batch-scan", response_model=BatchScanResponse)
    def batch_scan(request: BatchScanRequest) -> BatchScanResponse:
        if not manager.settings.enable_batch_scan:
            raise HTTPException(status_code=403, detail="Batch scan mode is disabled.")
        jobs = submit_batch_scan(manager, request)
        return BatchScanResponse(submitted=len(jobs), jobs=jobs)

    return router
