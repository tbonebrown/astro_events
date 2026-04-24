from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from astro_api.config import AppSettings
from astro_api.database import Base
from astro_api.services.ingestion import ingest_transient_export
from astro_transients.config import PipelineSettings
from astro_transients.pipeline import run_nightly
from services.api.main import create_app


def make_session_provider(session_factory: sessionmaker):
    def get_test_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    return get_test_session


def test_transient_endpoints_return_ranked_results(tmp_path):
    export_settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    export_result = run_nightly(limit=6, settings=export_settings, synthetic=True)

    engine = create_engine(f"sqlite:///{tmp_path / 'astro.db'}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app_settings = AppSettings(
        database_url=f"sqlite:///{tmp_path / 'astro.db'}",
        data_dir=tmp_path / "app-data",
        exports_dir=tmp_path / "exports",
        static_dir=tmp_path / "static",
    )

    with session_factory() as session:
        ingest_transient_export(export_result.export_dir, session=session, settings=app_settings)

    app = create_app(
        settings=app_settings,
        session_provider=make_session_provider(session_factory),
        initialize_database=lambda: Base.metadata.create_all(bind=engine),
    )

    with TestClient(app) as client:
        list_response = client.get("/api/transients")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 6

        candidate_id = payload[0]["candidate_id"]
        detail_response = client.get(f"/api/transients/{candidate_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["external_alert_id"]

        report_response = client.get("/api/transients/reports/latest")
        assert report_response.status_code == 200
        assert report_response.json()["run"]["source_name"] == "gaia"


def test_transient_report_returns_404_when_empty(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'astro.db'}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app_settings = AppSettings(
        database_url=f"sqlite:///{tmp_path / 'astro.db'}",
        data_dir=tmp_path / "app-data",
        exports_dir=tmp_path / "exports",
        static_dir=tmp_path / "static",
    )

    app = create_app(
        settings=app_settings,
        session_provider=make_session_provider(session_factory),
        initialize_database=lambda: Base.metadata.create_all(bind=engine),
    )

    with TestClient(app) as client:
        assert client.get("/api/transients").status_code == 200
        assert client.get("/api/transients").json() == []
        assert client.get("/api/transients/reports/latest").status_code == 404
