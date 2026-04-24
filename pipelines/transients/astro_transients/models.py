from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class GaiaAlert:
    name: str
    external_alert_id: str
    observed_at: str
    published_at: str
    ra: float
    dec: float
    magnitude: float
    historic_magnitude: float | None = None
    historic_scatter: float | None = None
    classification: str = ""
    comment: str = ""
    tns_name: str = ""
    source_id: str = ""
    alert_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TransientCandidateRecord:
    candidate_id: str
    source_name: str
    external_alert_id: str
    run_date: str
    alert_timestamp: str
    ra: float
    dec: float
    score: float
    rank: int
    score_breakdown: dict[str, float]
    classification_hint: str
    novelty_flag: bool
    magnitude: float
    magnitude_change: float
    sky_region: str
    provenance: dict[str, Any]
    summary: str
    detail_payload: dict[str, Any]


@dataclass(slots=True)
class PipelineRunResult:
    run_date: str
    source_name: str
    export_dir: str
    candidates: list[TransientCandidateRecord]
    generated_at: datetime
