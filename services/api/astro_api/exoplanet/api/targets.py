from __future__ import annotations

from fastapi import APIRouter

from astro_api.exoplanet.models.schemas import DemoTargetResponse


def create_target_router(manager) -> APIRouter:
    router = APIRouter()

    @router.get("/demo-targets", response_model=list[DemoTargetResponse])
    def demo_targets() -> list[DemoTargetResponse]:
        return [DemoTargetResponse.model_validate(target) for target in manager.demo_targets()]

    return router
