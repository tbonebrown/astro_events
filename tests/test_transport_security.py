from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from astro_api.config import AppSettings
from astro_api.database import Base
from services.api.main import create_app


def make_session_provider(session_factory: sessionmaker):
    def get_test_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    return get_test_session


def build_app(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'astro.db'}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    settings = AppSettings(
        database_url=f"sqlite:///{tmp_path / 'astro.db'}",
        data_dir=tmp_path / "app-data",
        exports_dir=tmp_path / "exports",
        static_dir=tmp_path / "static",
        public_hosts=("ohnita.com",),
    )

    return create_app(
        settings=settings,
        session_provider=make_session_provider(session_factory),
        initialize_database=lambda: Base.metadata.create_all(bind=engine),
    )


def test_public_http_requests_redirect_to_https(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    with TestClient(app, base_url="http://ohnita.com", follow_redirects=False) as client:
        response = client.get("/api/health", headers={"x-forwarded-proto": "http"})

    assert response.status_code == 308
    assert response.headers["location"] == "https://ohnita.com/api/health"


def test_public_https_requests_set_hsts_header(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    with TestClient(app, base_url="https://ohnita.com") as client:
        response = client.get("/api/health", headers={"x-forwarded-proto": "https"})

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
