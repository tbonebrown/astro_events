from __future__ import annotations

from dataclasses import dataclass

from astro_api.config import AppSettings
from astro_api.exoplanet.services.tess_service import TESSLightCurveService


@dataclass(slots=True)
class KeplerLightCurveService(TESSLightCurveService):
    settings: AppSettings

    mission: str = "Kepler"
