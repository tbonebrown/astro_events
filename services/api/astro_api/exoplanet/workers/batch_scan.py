from __future__ import annotations

from astro_api.exoplanet.models.schemas import BatchScanRequest, ExoplanetAnalyzeRequest


def submit_batch_scan(manager, request: BatchScanRequest) -> list:
    jobs = []
    for target in request.targets:
        analyze_request = ExoplanetAnalyzeRequest(
            target=target,
            mission=request.mission,
            period_min_days=request.period_min_days,
            period_max_days=request.period_max_days,
        )
        job, cache_hit = manager.submit(analyze_request)
        jobs.append({"job_id": job.job_id, "status": job.status, "cache_hit": cache_hit})
    return jobs
