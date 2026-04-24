from __future__ import annotations

from pathlib import Path
import importlib
import os
import sys

pytest = __import__("pytest")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def test_galaxy_map_endpoints_bootstrap_demo_catalog(tmp_path: Path) -> None:
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

    with TestClient(api_main.app) as client:
        galaxy_list = client.get("/api/galaxies?limit=128")
        assert galaxy_list.status_code == 200
        payload = galaxy_list.json()
        assert payload["returned"] > 0
        assert payload["total"] >= payload["returned"]
        assert payload["bounds"]["max_x"] > payload["bounds"]["min_x"]

        image_id = payload["points"][0]["image_id"]

        detail = client.get(f"/api/galaxy/{image_id}")
        explain = client.get(f"/api/explain/{image_id}")
        clusters = client.get("/api/clusters")

        assert detail.status_code == 200
        assert explain.status_code == 200
        assert clusters.status_code == 200
        assert detail.json()["nearest_neighbors"]
        assert "cluster_name" in detail.json()
        assert explain.json()["explanation"]
        assert len(clusters.json()) >= 5
