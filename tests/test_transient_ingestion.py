from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from astro_api.config import AppSettings
from astro_api.database import Base
from astro_api.models import TransientCandidate, TransientRun
from astro_api.services.ingestion import ingest_transient_export
from astro_transients.config import PipelineSettings
from astro_transients.pipeline import run_nightly


def test_transient_ingestion_persists_candidates_and_replaces_existing_run(tmp_path):
    export_settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    export_result = run_nightly(limit=8, settings=export_settings, synthetic=True)

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
        run = ingest_transient_export(export_result.export_dir, session=session, settings=app_settings)
        assert run.candidate_count == 8
        assert run.reports[0].title == "GAIA Transient Nightly Report"

    with Session(engine) as session:
        ingest_transient_export(export_result.export_dir, session=session, settings=app_settings)
        runs = session.scalars(select(TransientRun)).all()
        candidates = session.scalars(select(TransientCandidate)).all()
        assert len(runs) == 1
        assert len(candidates) == 8
