from __future__ import annotations

from astro_api.models import (
    Candidate,
    NightlyReport,
    NightlyRun,
    TransientCandidate,
    TransientReport,
    TransientRun,
)
from astro_api.services.llm import LocalInferenceClient


def generate_report(run: NightlyRun, llm_client: LocalInferenceClient) -> NightlyReport:
    top_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "anomaly_score": candidate.anomaly_score,
            "variability_hint": candidate.variability_hint,
        }
        for candidate in run.candidates[:10]
    ]
    markdown, status = llm_client.nightly_report(
        {
            "run_date": run.run_date,
            "sector": run.sector,
            "candidate_count": run.candidate_count,
            "top_candidates": top_candidates,
        }
    )
    return NightlyReport(
        title=f"TESS Sector {run.sector} Nightly Report",
        markdown=markdown,
        model_name=llm_client.settings.local_inference_model,
        summary_json={"status": status, "top_candidates": top_candidates},
    )


def generate_transient_report(run: TransientRun, llm_client: LocalInferenceClient) -> TransientReport:
    top_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "external_alert_id": candidate.external_alert_id,
            "score": candidate.score,
            "classification_hint": candidate.classification_hint,
            "summary": candidate.summary,
        }
        for candidate in run.candidates[:10]
    ]
    markdown, status = llm_client.transient_report(
        {
            "run_date": run.run_date,
            "source_name": run.source_name,
            "candidate_count": run.candidate_count,
            "top_candidates": top_candidates,
        }
    )
    return TransientReport(
        title=f"{run.source_name.upper()} Transient Nightly Report",
        markdown=markdown,
        model_name=llm_client.settings.local_inference_model,
        summary_json={"status": status, "top_candidates": top_candidates},
    )
