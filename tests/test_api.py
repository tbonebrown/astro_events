from __future__ import annotations

from pathlib import Path
import importlib
import os
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from astro_tess.config import PipelineSettings
from astro_tess.pipeline import run_nightly


def test_api_endpoints_return_latest_data(tmp_path: Path) -> None:
    db_path = tmp_path / "api.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["EXPORTS_DIR"] = str(tmp_path / "exports")
    os.environ["STATIC_DIR"] = str(tmp_path / "static")
    os.environ["APP_ENV"] = "test"

    for module_name in list(sys.modules):
        if module_name == "main" or module_name.startswith("astro_api"):
            del sys.modules[module_name]

    api_main = importlib.import_module("main")
    database_module = importlib.import_module("astro_api.database")
    ingestion_module = importlib.import_module("astro_api.services.ingestion")
    with TestClient(api_main.app) as client:
        export_settings = PipelineSettings(export_root=tmp_path / "exports", sync_target="", sync_mode="local")
        pipeline_result = run_nightly(sector=7, limit=8, settings=export_settings, synthetic=True)

        with database_module.SessionLocal() as session:
            ingestion_module.ingest_export(
                Path(pipeline_result.export_dir),
                session=session,
                settings=api_main.settings,
            )

        health = client.get("/api/health")
        runs = client.get("/api/runs/latest")
        candidates = client.get("/api/candidates")
        detail = client.get(f"/api/candidates/{candidates.json()[0]['candidate_id']}")
        report = client.get("/api/reports/latest")

        assert health.status_code == 200
        assert runs.status_code == 200
        assert candidates.status_code == 200
        assert detail.status_code == 200
        assert report.status_code == 200
        assert candidates.json()[0]["rank"] == 1
