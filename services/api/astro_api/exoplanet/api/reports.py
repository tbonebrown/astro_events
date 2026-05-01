from __future__ import annotations

from fastapi import APIRouter, HTTPException

from astro_api.exoplanet.models.schemas import ExoplanetReportResponse


def create_report_router(manager) -> APIRouter:
    router = APIRouter()

    @router.get("/report/{job_id}", response_model=ExoplanetReportResponse)
    def report(job_id: str) -> ExoplanetReportResponse:
        payload = manager.report(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Analysis report is not ready.")
        return ExoplanetReportResponse.model_validate(payload)

    return router
