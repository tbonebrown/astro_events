from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from astro_api.config import AppSettings
from astro_api.exoplanet.models.schemas import ExoplanetAnalyzeRequest
from astro_api.exoplanet.services.cache import ExoplanetCache


@dataclass(slots=True)
class TESSLightCurveService:
    settings: AppSettings

    mission: str = "TESS"

    def get_light_curve(
        self,
        target: dict[str, Any],
        request: ExoplanetAnalyzeRequest,
        cache: ExoplanetCache,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        cache_key = cache.lightcurve_key(target, request)
        if not request.force_refresh:
            cached = cache.load_lightcurve(cache_key)
            if cached:
                time, flux, metadata = cached
                metadata["cache_hit"] = True
                return time, flux, metadata

        try:
            time, flux, metadata = self._download_with_lightkurve(target, request)
        except Exception as exc:
            time, flux, metadata = synthetic_light_curve(target, mission=self.mission)
            metadata["download_error"] = str(exc)
            metadata["source"] = "synthetic_fallback"

        cache.save_lightcurve(cache_key, target["target_id"], time, flux, metadata)
        metadata["cache_hit"] = False
        return time, flux, metadata

    def _download_with_lightkurve(
        self,
        target: dict[str, Any],
        request: ExoplanetAnalyzeRequest,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        import lightkurve as lk

        query = target.get("query") or target.get("name")
        search = lk.search_lightcurve(query, mission=self.mission)
        if len(search) == 0:
            raise RuntimeError(f"No {self.mission} light curves found for {query}.")
        if request.sector_or_quarter:
            token = str(request.sector_or_quarter).lower()
            filtered_rows = [
                index
                for index, row in enumerate(search.table)
                if token in " ".join(str(value).lower() for value in row)
            ]
            if filtered_rows:
                search = search[filtered_rows]
        collection = search[: request.max_lightcurves].download_all(
            download_dir=str(self.settings.exoplanet_cache_dir / "mast")
        )
        if collection is None or len(collection) == 0:
            raise RuntimeError(f"Download returned no {self.mission} light curves for {query}.")
        light_curve = collection.stitch().remove_nans().normalize()
        time = np.asarray(light_curve.time.value, dtype=float)
        flux = np.asarray(light_curve.flux.value, dtype=float)
        metadata = {
            "source": "lightkurve",
            "mission": self.mission,
            "query": query,
            "products": len(collection),
            "cadence": "archive",
        }
        return time, flux, metadata


def synthetic_light_curve(target: dict[str, Any], mission: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    period = float(target.get("known_period_days") or 3.25)
    depth = float(target.get("expected_depth_ppm") or 2400.0) / 1_000_000.0
    duration_days = min(max(0.055 * period, 0.06), 0.34)
    baseline = max(72.0, min(1200.0, period * 5.2))
    cadence = 0.020833 if baseline <= 120 else 0.12
    time = np.arange(0.0, baseline, cadence, dtype=float)
    seed = abs(hash((target.get("target_id"), mission))) % (2**32)
    rng = np.random.default_rng(seed)
    stellar = 0.00055 * np.sin(2 * np.pi * time / max(4.5, period * 2.7))
    noise = rng.normal(0.0, max(depth * 0.20, 0.00013), size=len(time))
    flux = 1.0 + stellar + noise
    transit_phase = ((time - 0.18 * period + 0.5 * period) % period) - 0.5 * period
    transit_mask = np.abs(transit_phase) < 0.5 * duration_days
    ingress_width = max(0.01, duration_days * 0.18)
    shape = np.clip((0.5 * duration_days - np.abs(transit_phase[transit_mask])) / ingress_width, 0, 1)
    flux[transit_mask] -= depth * (0.62 + 0.38 * shape)
    metadata = {
        "source": "synthetic_fallback",
        "mission": mission,
        "query": target.get("query") or target.get("name"),
        "products": 0,
        "cadence": cadence,
        "period_days": period,
        "depth": depth,
        "duration_days": duration_days,
        "note": "Deterministic fallback used when live NASA archive access is unavailable.",
    }
    return time, flux, metadata
