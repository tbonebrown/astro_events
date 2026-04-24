from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import selectinload, sessionmaker

from astro_api.config import AppSettings
from astro_api.database import Base
from astro_api.models import Candidate, NightlyReport, NightlyRun
from astro_api.services.ingestion import ingest_export
from astro_tess.config import PipelineSettings
from astro_tess.pipeline import run_nightly


def test_ingestion_loads_candidates_and_report(tmp_path: Path) -> None:
    export_settings = PipelineSettings(export_root=tmp_path / "exports", sync_target="", sync_mode="local")
    pipeline_result = run_nightly(sector=42, limit=10, settings=export_settings, synthetic=True)

    engine = create_engine(f"sqlite:///{tmp_path / 'astro_events.db'}", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = AppSettings(
        database_url=f"sqlite:///{tmp_path / 'astro_events.db'}",
        data_dir=tmp_path / "data",
        exports_dir=tmp_path / "exports",
    )

    with session_factory() as session:
        run = ingest_export(Path(pipeline_result.export_dir), session=session, settings=settings)

    with session_factory() as session:
        stored_run = session.scalar(select(NightlyRun))
        stored_candidate = session.scalar(
            select(Candidate)
            .options(selectinload(Candidate.artifacts))
            .order_by(Candidate.rank.asc())
        )
        stored_report = session.scalar(select(NightlyReport))

        assert run.status == "published"
        assert stored_run is not None
        assert stored_candidate is not None
        assert stored_candidate.explanation
        assert stored_candidate.artifacts[0].url.startswith("/artifacts/")
        assert stored_report is not None
