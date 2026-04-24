from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from astro_transients.config import PipelineSettings
from astro_transients.data_sources import GaiaAlertsSource, SyntheticGaiaSource
from astro_transients.export import export_run
from astro_transients.models import GaiaAlert, PipelineRunResult, TransientCandidateRecord
from astro_transients.scoring import AlertScore, TwoStageTransientScorer
from astro_transients.sync import ArtifactSync


def build_candidate_id(source_name: str, external_alert_id: str, run_date: str) -> str:
    safe_identifier = external_alert_id.replace(" ", "_")
    return f"{source_name}:{safe_identifier}:{run_date}"


def _dedupe_alerts(alerts: list[GaiaAlert]) -> list[GaiaAlert]:
    deduped: dict[str, GaiaAlert] = {}
    for alert in alerts:
        key = alert.external_alert_id or alert.source_id or f"{alert.ra:.5f}:{alert.dec:.5f}"
        current = deduped.get(key)
        if current is None or alert.published_at > current.published_at:
            deduped[key] = alert
    return list(deduped.values())


def _summarize(alert: GaiaAlert, score: AlertScore) -> str:
    change_phrase = (
        f"It is {abs(score.magnitude_change):.2f} mag brighter than its historic baseline."
        if score.magnitude_change >= 0
        else f"It is {abs(score.magnitude_change):.2f} mag fainter than its historic baseline."
    )
    novelty_phrase = "This is flagged as a novel follow-up target." if score.novelty_flag else ""
    return " ".join(
        part
        for part in [
            f"{alert.name} is a {score.classification_hint.lower()} candidate from the Gaia alert stream.",
            change_phrase,
            novelty_phrase,
        ]
        if part
    ).strip()


def _detail_payload(alert: GaiaAlert, score: AlertScore) -> dict[str, object]:
    return {
        "gaia_name": alert.name,
        "alert_url": alert.alert_url,
        "tns_name": alert.tns_name,
        "comment": alert.comment,
        "historic_magnitude": alert.historic_magnitude,
        "historic_scatter": alert.historic_scatter,
        "source_id": alert.source_id,
        "published_at": alert.published_at,
        "observed_at": alert.observed_at,
        "classification_hint": score.classification_hint,
        "raw_metadata": alert.metadata or {"source": "gaia"},
    }


def run_nightly(
    limit: int,
    settings: PipelineSettings | None = None,
    synthetic: bool = False,
    source: SyntheticGaiaSource | GaiaAlertsSource | None = None,
) -> PipelineRunResult:
    settings = settings or PipelineSettings()
    generated_at = datetime.now(timezone.utc)
    run_date = generated_at.date().isoformat()

    if source is None:
        source = SyntheticGaiaSource() if synthetic else GaiaAlertsSource(settings.gaia_alerts_url)
    alerts = _dedupe_alerts(source.fetch_alerts(limit=limit))
    scored_alerts = TwoStageTransientScorer().score_alerts(alerts)

    ordered_pairs = sorted(
        zip(alerts, scored_alerts, strict=True),
        key=lambda item: item[1].score,
        reverse=True,
    )

    candidates: list[TransientCandidateRecord] = []
    for rank, (alert, score) in enumerate(ordered_pairs, start=1):
        candidate_id = build_candidate_id(settings.source_name, alert.external_alert_id, run_date)
        candidates.append(
            TransientCandidateRecord(
                candidate_id=candidate_id,
                source_name=settings.source_name,
                external_alert_id=alert.external_alert_id,
                run_date=run_date,
                alert_timestamp=alert.observed_at,
                ra=alert.ra,
                dec=alert.dec,
                score=float(score.score),
                rank=rank,
                score_breakdown={key: round(value, 6) for key, value in score.score_breakdown.items()},
                classification_hint=score.classification_hint,
                novelty_flag=score.novelty_flag,
                magnitude=alert.magnitude,
                magnitude_change=round(score.magnitude_change, 6),
                sky_region=score.sky_region,
                provenance={
                    "pipeline_version": "0.1.0",
                    "model_version": "gaia-two-stage-v1",
                    "source": settings.source_name,
                    "alert_url": alert.alert_url,
                },
                summary=_summarize(alert, score),
                detail_payload=_detail_payload(alert, score),
            )
        )

    result = PipelineRunResult(
        run_date=run_date,
        source_name=settings.source_name,
        export_dir="",
        candidates=candidates,
        generated_at=generated_at,
    )
    export_dir = export_run(result, settings.export_root)
    ArtifactSync(mode=settings.sync_mode, target=settings.sync_target).sync(export_dir)
    return replace(result, export_dir=str(export_dir))
