from __future__ import annotations

from fastapi import APIRouter

from astro_api.config import AppSettings
from astro_api.exoplanet.api.detection import create_detection_router
from astro_api.exoplanet.api.lightcurves import create_lightcurve_router
from astro_api.exoplanet.api.reports import create_report_router
from astro_api.exoplanet.api.targets import create_target_router
from astro_api.exoplanet.services.analyzer import ExoplanetAnalysisManager


def create_exoplanet_router(settings: AppSettings) -> APIRouter:
    manager = ExoplanetAnalysisManager(settings=settings)
    router = APIRouter(prefix="/api/exoplanet", tags=["exoplanet"])
    router.include_router(create_target_router(manager))
    router.include_router(create_lightcurve_router(manager))
    router.include_router(create_detection_router(manager))
    router.include_router(create_report_router(manager))
    return router
