from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np

from astro_api.config import AppSettings
from astro_api.exoplanet.models.schemas import ExoplanetAnalyzeRequest


@dataclass(slots=True)
class ExoplanetCache:
    settings: AppSettings

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "lightcurves").mkdir(exist_ok=True)
        (self.base_dir / "results").mkdir(exist_ok=True)
        self._initialize_metadata()

    @property
    def base_dir(self) -> Path:
        return self.settings.exoplanet_cache_dir

    @property
    def metadata_path(self) -> Path:
        return self.base_dir / "metadata.sqlite3"

    def _initialize_metadata(self) -> None:
        with sqlite3.connect(self.metadata_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    @staticmethod
    def _json_hash(payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]

    def analysis_key(self, target: dict[str, Any], request: ExoplanetAnalyzeRequest) -> str:
        return self._json_hash(
            {
                "target_id": target["target_id"],
                "mission": target["mission"],
                "sector_or_quarter": request.sector_or_quarter,
                "period_min_days": request.period_min_days,
                "period_max_days": request.period_max_days,
                "duration_min_hours": request.duration_min_hours,
                "duration_max_hours": request.duration_max_hours,
                "detrend_method": request.detrend_method,
                "max_lightcurves": request.max_lightcurves,
            }
        )

    def lightcurve_key(self, target: dict[str, Any], request: ExoplanetAnalyzeRequest) -> str:
        return self._json_hash(
            {
                "target_id": target["target_id"],
                "mission": target["mission"],
                "sector_or_quarter": request.sector_or_quarter,
                "max_lightcurves": request.max_lightcurves,
            }
        )

    def load_result(self, cache_key: str) -> dict[str, Any] | None:
        path = self.base_dir / "results" / f"{cache_key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_result(self, cache_key: str, target_id: str, payload: dict[str, Any]) -> None:
        path = self.base_dir / "results" / f"{cache_key}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self._record(cache_key, target_id, "analysis", path, {"status": "complete"})

    def load_lightcurve(self, cache_key: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]] | None:
        path = self.base_dir / "lightcurves" / f"{cache_key}.npz"
        if not path.exists():
            return None
        try:
            with np.load(path, allow_pickle=False) as loaded:
                metadata = json.loads(str(loaded["metadata"]))
                return loaded["time"], loaded["flux"], metadata
        except Exception:
            return None

    def save_lightcurve(
        self,
        cache_key: str,
        target_id: str,
        time: np.ndarray,
        flux: np.ndarray,
        metadata: dict[str, Any],
    ) -> None:
        path = self.base_dir / "lightcurves" / f"{cache_key}.npz"
        np.savez_compressed(path, time=time, flux=flux, metadata=json.dumps(metadata, sort_keys=True))
        self._record(cache_key, target_id, "lightcurve", path, metadata)

    def list_entries_for_target(self, target_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.metadata_path) as connection:
            rows = connection.execute(
                """
                SELECT cache_key, target_id, kind, path, created_at, metadata_json
                FROM cache_entries
                WHERE target_id = ?
                ORDER BY created_at DESC
                """,
                (target_id,),
            ).fetchall()
        entries = []
        for cache_key, row_target_id, kind, path, created_at, metadata_json in rows:
            try:
                metadata = json.loads(metadata_json)
            except Exception:
                metadata = {}
            entries.append(
                {
                    "cache_key": cache_key,
                    "target_id": row_target_id,
                    "kind": kind,
                    "path": path,
                    "created_at": created_at,
                    "metadata": metadata,
                }
            )
        return entries

    def _record(
        self,
        cache_key: str,
        target_id: str,
        kind: str,
        path: Path,
        metadata: dict[str, Any],
    ) -> None:
        with sqlite3.connect(self.metadata_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                    (cache_key, target_id, kind, path, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    target_id,
                    kind,
                    str(path),
                    datetime.now(UTC).isoformat(),
                    json.dumps(metadata, sort_keys=True),
                ),
            )
            connection.commit()
