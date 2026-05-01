from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx

from astro_api.config import AppSettings
from astro_api.exoplanet.services.targets import normalize_identifier


KNOWN_OBJECTS = {
    "kepler-10": [
        {"object_name": "Kepler-10 b", "period_days": 0.837491, "disposition": "Confirmed planet"},
        {"object_name": "Kepler-10 c", "period_days": 45.29485, "disposition": "Confirmed planet"},
    ],
    "kepler-22": [
        {"object_name": "Kepler-22 b", "period_days": 289.8623, "disposition": "Confirmed planet"},
    ],
    "kepler-186": [
        {"object_name": "Kepler-186 b", "period_days": 3.88679, "disposition": "Confirmed planet"},
        {"object_name": "Kepler-186 f", "period_days": 129.9441, "disposition": "Confirmed planet"},
    ],
    "wasp-12": [
        {"object_name": "WASP-12 b", "period_days": 1.09142, "disposition": "Confirmed planet"},
    ],
    "hat-p-7": [
        {"object_name": "HAT-P-7 b", "period_days": 2.20473, "disposition": "Confirmed planet"},
    ],
    "toi-700": [
        {"object_name": "TOI-700 b", "period_days": 9.977, "disposition": "Confirmed planet"},
        {"object_name": "TOI-700 d", "period_days": 37.426, "disposition": "Confirmed planet"},
    ],
}


@dataclass(slots=True)
class ArchiveLookupService:
    settings: AppSettings

    def lookup(self, target: dict, period_days: float) -> dict:
        curated = self._curated_match(target, period_days)
        if curated:
            return curated

        remote = self._nasa_archive_match(target, period_days)
        if remote:
            return remote

        return {
            "status": "no_match",
            "catalog": None,
            "object_name": None,
            "disposition": None,
            "period_days": None,
            "period_delta_percent": None,
            "source_url": "https://exoplanetarchive.ipac.caltech.edu/",
            "notes": "No confirmed planet, TOI, or KOI match was found in the local fallback catalog. Remote archive lookup may be unavailable.",
        }

    def _curated_match(self, target: dict, period_days: float) -> dict | None:
        aliases = [target.get("target_id", ""), target.get("name", ""), *target.get("aliases", [])]
        keys = [normalize_identifier(alias) for alias in aliases]
        for key in keys:
            if key not in KNOWN_OBJECTS:
                continue
            best = min(
                KNOWN_OBJECTS[key],
                key=lambda item: abs(item["period_days"] - period_days) / max(item["period_days"], 1e-8),
            )
            delta = abs(best["period_days"] - period_days) / max(best["period_days"], 1e-8) * 100.0
            if delta <= 5.0:
                return {
                    "status": "match",
                    "catalog": "NASA Exoplanet Archive fallback catalog",
                    "object_name": best["object_name"],
                    "disposition": best["disposition"],
                    "period_days": best["period_days"],
                    "period_delta_percent": round(delta, 3),
                    "source_url": "https://exoplanetarchive.ipac.caltech.edu/",
                    "notes": "The detected period is consistent with a known cataloged object.",
                }
        return None

    def _nasa_archive_match(self, target: dict, period_days: float) -> dict | None:
        name = target.get("name") or target.get("query")
        if not name:
            return None
        escaped = name.replace("'", "''")
        query = (
            "select pl_name,hostname,discoverymethod,pl_orbper,sy_pnum "
            "from pscomppars "
            f"where lower(hostname)=lower('{escaped}')"
        )
        url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
        try:
            response = httpx.get(
                url,
                params={"query": query, "format": "json"},
                timeout=self.settings.nasa_archive_timeout,
            )
            response.raise_for_status()
            rows = response.json()
        except Exception:
            return None
        if not isinstance(rows, list) or not rows:
            return None
        candidates = [row for row in rows if row.get("pl_orbper")]
        if not candidates:
            return None
        best = min(
            candidates,
            key=lambda row: abs(float(row["pl_orbper"]) - period_days) / max(float(row["pl_orbper"]), 1e-8),
        )
        archive_period = float(best["pl_orbper"])
        delta = abs(archive_period - period_days) / max(archive_period, 1e-8) * 100.0
        if delta > 5.0:
            return None
        return {
            "status": "match",
            "catalog": "NASA Exoplanet Archive",
            "object_name": str(best.get("pl_name") or best.get("hostname")),
            "disposition": "Confirmed planet",
            "period_days": archive_period,
            "period_delta_percent": round(delta, 3),
            "source_url": f"https://exoplanetarchive.ipac.caltech.edu/overview/{quote(str(best.get('pl_name') or name))}",
            "notes": "Remote NASA Exoplanet Archive lookup found a period-consistent confirmed object.",
        }
