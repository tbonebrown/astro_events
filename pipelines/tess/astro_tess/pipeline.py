from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from astro_tess.artifacts import save_light_curve_plot
from astro_tess.config import PipelineSettings
from astro_tess.data_sources import LightkurveTessSource, SyntheticTessSource, load_tic_ids
from astro_tess.export import export_run
from astro_tess.features import extract_features, feature_matrix, variability_hint
from astro_tess.models import CandidateRecord, PipelineRunResult
from astro_tess.preprocess import clean_light_curve, normalize_flux, resample_light_curve
from astro_tess.scoring import EnsembleAnomalyScorer
from astro_tess.sync import ArtifactSync


def build_candidate_id(tic_id: str, sector: int, run_date: str) -> str:
    return f"tess:{tic_id}:{sector}:{run_date}"


def run_nightly(
    sector: int,
    limit: int,
    settings: PipelineSettings | None = None,
    synthetic: bool = False,
    tic_target_file: Path | None = None,
) -> PipelineRunResult:
    settings = settings or PipelineSettings()
    generated_at = datetime.now(timezone.utc)
    run_date = generated_at.date().isoformat()
    export_stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    export_dir = settings.export_root / f"sector_{sector}" / export_stamp

    if synthetic:
        source = SyntheticTessSource()
    else:
        if tic_target_file is None:
            raise ValueError("A TIC target file is required for real TESS downloads.")
        source = LightkurveTessSource(load_tic_ids(tic_target_file))

    samples = source.fetch_samples(sector=sector, limit=limit)

    prepared_curves: list[np.ndarray] = []
    feature_rows: list[dict[str, float]] = []
    plot_inputs: list[tuple[str, np.ndarray, np.ndarray, dict[str, str]]] = []

    for sample in samples:
        clean_time, clean_flux = clean_light_curve(sample.time, sample.flux)
        resampled_time, resampled_flux = resample_light_curve(
            clean_time, clean_flux, points=settings.default_points
        )
        normalized_flux = normalize_flux(resampled_flux)
        features = extract_features(resampled_time, normalized_flux)
        prepared_curves.append(normalized_flux)
        feature_rows.append(features)
        plot_inputs.append(
            (
                sample.tic_id,
                resampled_time,
                normalized_flux,
                sample.provenance,
            )
        )

    sequences = np.asarray(prepared_curves, dtype=float)
    features = feature_matrix(feature_rows)
    scorer = EnsembleAnomalyScorer().fit(sequences, features)
    blended, reconstruction_error, feature_score = scorer.score(sequences, features)

    order = np.argsort(blended)[::-1]
    plots_dir = export_dir / "plots"
    candidates: list[CandidateRecord] = []

    for rank, sample_index in enumerate(order, start=1):
        tic_id, resampled_time, normalized_flux, provenance = plot_inputs[sample_index]
        feature_row = feature_rows[sample_index]
        candidate_id = build_candidate_id(tic_id, sector, run_date)
        plot_path = save_light_curve_plot(
            candidate_id=candidate_id,
            time=resampled_time,
            flux=normalized_flux,
            output_dir=plots_dir,
            dpi=settings.plot_dpi,
        )
        candidates.append(
            CandidateRecord(
                candidate_id=candidate_id,
                tic_id=tic_id,
                sector=sector,
                run_date=run_date,
                anomaly_score=float(blended[sample_index]),
                feature_score=float(feature_score[sample_index]),
                reconstruction_error=float(reconstruction_error[sample_index]),
                rank=rank,
                variability_hint=variability_hint(feature_row),
                top_features={key: round(value, 6) for key, value in feature_row.items()},
                score_breakdown={
                    "ensemble": float(blended[sample_index]),
                    "reconstruction_error": float(reconstruction_error[sample_index]),
                    "feature_outlier": float(feature_score[sample_index]),
                },
                provenance={
                    "pipeline_version": "0.1.0",
                    "model_version": "baseline-ensemble-v1",
                    **provenance,
                },
                plot_path=str(plot_path),
                explanation="",
            )
        )

    result = PipelineRunResult(
        run_date=run_date,
        sector=sector,
        export_dir=str(export_dir),
        candidates=candidates,
        generated_at=generated_at,
    )
    export_dir = export_run(result, settings.export_root)
    sync_manager = ArtifactSync(mode=settings.sync_mode, target=settings.sync_target)
    sync_manager.sync(export_dir)
    return replace(result, export_dir=str(export_dir))
