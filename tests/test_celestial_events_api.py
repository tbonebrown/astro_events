from __future__ import annotations

from pathlib import Path
import importlib
import os
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def test_celestial_events_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "celestial.db"
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
        personalized = client.get(
            "/api/events/personalized",
            params={
                "lat": 41.8781,
                "lon": -87.6298,
                "timezone": "America/Chicago",
                "days": 14,
            },
        )

        assert personalized.status_code == 200
        payload = personalized.json()
        assert payload["requested_location"]["timezone"] == "America/Chicago"
        assert len(payload["events"]) >= 5
        event_types = {event["type"] for event in payload["events"]}
        assert len(event_types) >= 5

        event_id = payload["events"][0]["event_id"]

        detail = client.get(
            f"/api/events/{event_id}",
            params={
                "lat": 41.8781,
                "lon": -87.6298,
                "timezone": "America/Chicago",
            },
        )
        explanation = client.get(
            f"/api/events/{event_id}/explain",
            params={
                "lat": 41.8781,
                "lon": -87.6298,
                "timezone": "America/Chicago",
            },
        )

        assert detail.status_code == 200
        assert explanation.status_code == 200
        assert "explanation" in explanation.json()
