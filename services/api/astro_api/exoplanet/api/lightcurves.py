from __future__ import annotations

from fastapi import APIRouter


def create_lightcurve_router(manager) -> APIRouter:
    router = APIRouter()

    @router.get("/cache/{target_id}")
    def cache_entries(target_id: str) -> dict:
        return {"target_id": target_id, "entries": manager.cache_entries(target_id)}

    return router
