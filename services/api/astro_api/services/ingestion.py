from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import shutil

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from astro_api.config import AppSettings
from astro_api.models import (
    Candidate,
    CandidateArtifact,
    NightlyRun,
    TransientArtifact,
    TransientCandidate,
    TransientRun,
)
from astro_api.services.llm import LocalInferenceClient
from astro_api.services.reporting import generate_report, generate_transient_report


def _copy_plot(source: Path, settings: AppSettings, run_date: str, sector: int) -> str:
    artifacts_dir = settings.data_dir / "artifacts" / run_date / f"sector_{sector}"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    target = artifacts_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    relative = target.relative_to(settings.data_dir)
    return f"/artifacts/{relative.as_posix()}"


def ingest_export(export_dir: Path, session: Session, settings: AppSettings | None = None) -> NightlyRun:
    settings = settings or AppSettings()
    export_dir = Path(export_dir)
    metadata = json.loads((export_dir / "run_metadata.json").read_text(encoding="utf-8"))
    candidates_frame = pd.read_parquet(export_dir / "candidates.parquet")
    run_date = str(metadata["run_date"])
    sector = int(metadata["sector"])

    existing = session.scalar(
        select(NightlyRun).where(NightlyRun.run_date == run_date, NightlyRun.sector == sector)
    )
    if existing is not None:
        session.delete(existing)
        session.flush()

    run = NightlyRun(
        run_date=run_date,
        sector=sector,
        status="processing",
        candidate_count=int(metadata["candidate_count"]),
        export_dir=str(export_dir),
        generated_at=datetime.fromisoformat(metadata["generated_at"]),
    )
    session.add(run)
    session.flush()

    llm_client = LocalInferenceClient(settings)
    candidates: list[Candidate] = []
    for row in candidates_frame.to_dict(orient="records"):
        candidate_payload = dict(row)
        explanation, explanation_status = llm_client.candidate_explanation(candidate_payload)
        candidate = Candidate(
            candidate_id=row["candidate_id"],
            run_id=run.id,
            tic_id=row["tic_id"],
            sector=int(row["sector"]),
            run_date=row["run_date"],
            anomaly_score=float(row["anomaly_score"]),
            feature_score=float(row["feature_score"]),
            reconstruction_error=float(row["reconstruction_error"]),
            rank=int(row["rank"]),
            variability_hint=row["variability_hint"],
            top_features=row["top_features"],
            score_breakdown=row["score_breakdown"],
            provenance=row["provenance"],
            explanation=explanation,
            explanation_status=explanation_status,
        )
        plot_path = Path(row["plot_path"])
        if plot_path.exists():
            candidate.artifacts.append(
                CandidateArtifact(
                    artifact_type="light_curve_plot",
                    url=_copy_plot(plot_path, settings, run_date, sector),
                    metadata_json={"source_path": str(plot_path)},
                )
            )
        session.add(candidate)
        candidates.append(candidate)

    session.flush()
    run.candidates = sorted(candidates, key=lambda item: item.rank)
    report = generate_report(run, llm_client)
    run.reports.append(report)
    run.status = "published"
    run.candidate_count = len(run.candidates)
    session.commit()
    session.refresh(run)
    return run


def ingest_transient_export(
    export_dir: Path,
    session: Session,
    settings: AppSettings | None = None,
) -> TransientRun:
    settings = settings or AppSettings()
    export_dir = Path(export_dir)
    metadata = json.loads((export_dir / "run_metadata.json").read_text(encoding="utf-8"))
    candidates_frame = pd.read_parquet(export_dir / "candidates.parquet")
    run_date = str(metadata["run_date"])
    source_name = str(metadata.get("source_name", "gaia"))

    existing = session.scalar(
        select(TransientRun).where(
            TransientRun.run_date == run_date,
            TransientRun.source_name == source_name,
        )
    )
    if existing is not None:
        session.delete(existing)
        session.flush()

    run = TransientRun(
        run_date=run_date,
        source_name=source_name,
        status="processing",
        candidate_count=int(metadata["candidate_count"]),
        export_dir=str(export_dir),
        generated_at=datetime.fromisoformat(metadata["generated_at"]),
    )
    session.add(run)
    session.flush()

    llm_client = LocalInferenceClient(settings)
    candidates: list[TransientCandidate] = []
    for row in candidates_frame.to_dict(orient="records"):
        candidate_payload = dict(row)
        summary = str(row.get("summary") or "").strip()
        if not summary:
            summary, _ = llm_client.transient_summary(candidate_payload)

        candidate = TransientCandidate(
            candidate_id=row["candidate_id"],
            run_id=run.id,
            source_name=row["source_name"],
            external_alert_id=row["external_alert_id"],
            run_date=row["run_date"],
            alert_timestamp=row["alert_timestamp"],
            ra=float(row["ra"]),
            dec=float(row["dec"]),
            score=float(row["score"]),
            rank=int(row["rank"]),
            score_breakdown=row["score_breakdown"],
            classification_hint=row["classification_hint"],
            novelty_flag=bool(row["novelty_flag"]),
            magnitude=float(row["magnitude"]),
            magnitude_change=float(row["magnitude_change"]),
            sky_region=row["sky_region"],
            provenance=row["provenance"],
            summary=summary,
            detail_payload=row["detail_payload"],
        )
        alert_url = candidate.detail_payload.get("alert_url")
        if alert_url:
            candidate.artifacts.append(
                TransientArtifact(
                    artifact_type="external_alert",
                    url=str(alert_url),
                    metadata_json={"source_name": source_name},
                )
            )
        session.add(candidate)
        candidates.append(candidate)

    session.flush()
    run.candidates = sorted(candidates, key=lambda item: item.rank)
    run.reports.append(generate_transient_report(run, llm_client))
    run.status = "published"
    run.candidate_count = len(run.candidates)
    session.commit()
    session.refresh(run)
    return run
